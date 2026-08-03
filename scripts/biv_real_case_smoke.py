#!/usr/bin/env python3
"""Run real BIV acceptance cases via API (requires live server + real providers)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx

from app.business_idea_validation.direct_http_fetch import probe_direct_http_fetch
from app.business_idea_validation.real_research_readiness import (
    RealResearchValidationResult,
    format_control_summary,
    provider_smoke_passed,
    validate_run_output,
)
from app.core.config import get_settings
from app.research_source_collection.readiness import probe_providers
from app.schemas.contracts import (
    AnalysisContextConfirmRequest,
    AnalysisContextCreateDraftRequest,
    BusinessIdeaValidationOutput,
)
from app.services.business_idea_validation_service import build_research_idempotency_key

MARKETSYNTH_CASE = {
    "name": "marketsynth_saas",
    "project_name": "REAL-RESEARCH Marketsynth",
    "idea": (
        "SaaS — AI-маркетинговое агентство, которое сначала проверяет жизнеспособность идеи, "
        "затем формирует стратегию, создаёт контент и помогает запускать рекламную кампанию."
    ),
    "product_or_service": "SaaS AI-маркетинговое агентство",
    "target_customer": "маркетологи, блогеры, малый и средний бизнес",
    "geography": "Россия",
    "pricing_or_revenue_model": "подписка, ориентир 200–900 долларов в месяц",
    "current_stage": "в разработке",
    "analysis_goal": "проверить коммерческую жизнеспособность",
    "expect_verdicts": {"GO", "CONDITIONAL_GO", "PILOT_ONLY", "HOLD"},
}

CASES = [
    MARKETSYNTH_CASE,
    {
        "name": "weak_brief",
        "project_name": "REAL-RESEARCH weak brief",
        "idea": "что-то с едой",
        "product_or_service": None,
        "target_customer": None,
        "geography": "Россия",
        "pricing_or_revenue_model": None,
        "current_stage": None,
        "analysis_goal": "понять есть ли смысл",
        "expect_verdicts": {"HOLD", "PILOT_ONLY", "NO_GO"},
    },
    {
        "name": "weak_commercial",
        "project_name": "REAL-RESEARCH weak commercial",
        "idea": "Бесплатное приложение без монетизации для всех желающих",
        "product_or_service": "мобильное приложение",
        "target_customer": "все",
        "geography": "Россия",
        "pricing_or_revenue_model": "бесплатно",
        "current_stage": "идея",
        "analysis_goal": "проверить коммерческую жизнеспособность",
        "expect_verdicts": {"NO_GO", "HOLD", "PILOT_ONLY"},
    },
]


async def _login(client: httpx.AsyncClient, email: str, password: str) -> None:
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    resp.raise_for_status()


async def _run_case(
    client: httpx.AsyncClient,
    case: dict,
    *,
    poll_seconds: float,
    timeout_seconds: float,
) -> dict:
    started = time.perf_counter()
    project = await client.post("/projects", json={"name": case["project_name"]})
    project.raise_for_status()
    project_id = project.json()["id"]

    draft_body = AnalysisContextCreateDraftRequest(
        idea_description=case["idea"],
        product_or_service=case.get("product_or_service"),
        target_customer=case.get("target_customer"),
        geography=case.get("geography"),
        pricing_or_revenue_model=case.get("pricing_or_revenue_model"),
        current_stage=case.get("current_stage"),
        analysis_goal=case.get("analysis_goal"),
    )
    draft = await client.post(
        f"/projects/{project_id}/analysis-contexts",
        json=draft_body.model_dump(mode="json", exclude_none=True),
    )
    draft.raise_for_status()
    context = draft.json()
    context_id = context["context_id"]
    snapshot_hash = context["input_snapshot_hash"]

    confirmed = await client.post(
        f"/projects/{project_id}/analysis-contexts/{context_id}/confirm",
        json=AnalysisContextConfirmRequest(input_snapshot_hash=snapshot_hash).model_dump(
            mode="json"
        ),
    )
    confirmed.raise_for_status()

    user_request = await client.post(
        "/user-requests",
        json={
            "text": case["idea"],
            "selected_scenario": "idea_validation",
            "skill_inputs": {"home_agency_flow": "v2"},
        },
    )
    user_request.raise_for_status()
    request_id = user_request.json()["id"]

    idem_key = build_research_idempotency_key(context_id, snapshot_hash)
    run_body = {
        "idempotency_key": idem_key,
        "research_intent": True,
        "analysis_context_id": context_id,
        "input_snapshot_hash": snapshot_hash,
        "idea": case["idea"],
        "location": case.get("geography"),
        "target_audience": case.get("target_customer"),
    }
    run = await client.post(
        f"/user-requests/{request_id}/business-idea-validation/run",
        json=run_body,
    )
    run.raise_for_status()
    run_json = run.json()
    run_id = run_json["run_id"]

    deadline = time.perf_counter() + timeout_seconds
    output_payload = run_json.get("output")
    while time.perf_counter() < deadline:
        if output_payload and run_json.get("status") == "succeeded":
            break
        await asyncio.sleep(poll_seconds)
        latest = await client.get(f"/user-requests/{request_id}/business-idea-validation")
        if latest.status_code == 200:
            run_json = latest.json()
            output_payload = run_json.get("output")
            if run_json.get("status") in {"succeeded", "failed"}:
                break

    export_resp = await client.get(f"/user-requests/{request_id}/business-idea-validation/export")
    export_ok = export_resp.status_code == 200
    export_text = export_resp.json().get("content", "") if export_ok else ""

    output = None
    if output_payload:
        output = BusinessIdeaValidationOutput.model_validate(output_payload)

    settings = get_settings()
    if output is None:
        validation = RealResearchValidationResult(
            passed=False,
            blockers=["research_output_missing"],
            metrics={"verdict": None, "confidence": None, "coverage": None},
        )
    else:
        validation = validate_run_output(output, settings=settings)

    elapsed = round(time.perf_counter() - started, 1)
    verdict = validation.metrics.get("verdict")
    verdict_ok = verdict in case.get("expect_verdicts", set()) if verdict else False

    return {
        "case": case["name"],
        "project_id": project_id,
        "user_request_id": request_id,
        "run_id": run_id,
        "status": run_json.get("status"),
        "elapsed_seconds": elapsed,
        "export_pass": export_ok,
        "export_length": len(export_text),
        "verdict_in_expected_set": verdict_ok,
        "validation": {
            "passed": validation.passed,
            "blockers": validation.blockers,
            "warnings": validation.warnings,
            "metrics": validation.metrics,
        },
        "export_preview": export_text[:400],
    }


async def _main_async(args: argparse.Namespace) -> int:
    settings = get_settings()
    if settings.research_source_collection_mock_providers:
        print("FAIL: RESEARCH_SOURCE_COLLECTION_MOCK_PROVIDERS=true — disable for real research")
        return 1

    probe = await probe_providers(settings, live=True)
    smoke_ok, blocker = provider_smoke_passed(probe)
    direct_http_probe = await probe_direct_http_fetch()
    fc_row = (probe.get("providers") or {}).get("firecrawl") or {}
    xr_row = (probe.get("providers") or {}).get("xmlriver") or {}
    fetch_contour_ok = xr_row.get("state") == "ready" and (
        fc_row.get("state") == "ready" or bool(direct_http_probe.get("ok"))
    )
    if not fetch_contour_ok and not args.skip_provider_smoke:
        print(f"FAIL fetch contour: xmlriver={xr_row.get('state')} firecrawl={fc_row.get('state')} direct_http={direct_http_probe.get('ok')}")
        print(json.dumps(probe, ensure_ascii=False, indent=2, default=str))
        return 1
    if not smoke_ok and not args.skip_provider_smoke and not fetch_contour_ok:
        print(f"FAIL provider smoke: {blocker}")
        print(json.dumps(probe, ensure_ascii=False, indent=2, default=str))
        return 1

    selected = [c for c in CASES if args.case in ("all", c["name"])]
    if not selected:
        print(f"Unknown case: {args.case}")
        return 1

    headers = {"Authorization": f"Bearer {args.api_key}"} if args.api_key else {}
    headers.setdefault("Origin", "http://localhost:3000")
    async with httpx.AsyncClient(
        base_url=args.base_url.rstrip("/"),
        headers=headers,
        timeout=httpx.Timeout(args.timeout_seconds, connect=30.0),
    ) as client:
        if not args.api_key:
            await _login(client, args.email, args.password)

        results = []
        for case in selected:
            print(f"Running case: {case['name']} ...")
            results.append(
                await _run_case(
                    client,
                    case,
                    poll_seconds=args.poll_seconds,
                    timeout_seconds=args.timeout_seconds,
                )
            )

    artifact_dir = Path(args.artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / f"real-research-{int(time.time())}.json"
    artifact_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    marketsynth = next((r for r in results if r["case"] == "marketsynth_saas"), results[0])
    validation = RealResearchValidationResult(
        passed=marketsynth["validation"]["passed"],
        blockers=marketsynth["validation"]["blockers"],
        warnings=marketsynth["validation"]["warnings"],
        metrics=marketsynth["validation"]["metrics"],
    )
    summary = format_control_summary(
        provider_status="PASS" if smoke_ok else "FAIL",
        case_status=marketsynth.get("status", "unknown"),
        validation=validation,
        export_pass=marketsynth["export_pass"],
    )
    print("\n" + summary)
    print(f"\nArtifact: {artifact_path}")

    all_ok = smoke_ok and all(
        r["status"] == "succeeded"
        and r["export_pass"]
        and r["validation"]["passed"]
        for r in results
    )
    return 0 if all_ok else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="BIV real-case smoke against live API")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--email", default="biv-real-research@marketsynth.test")
    parser.add_argument("--password", default="BivRealResearch2026!")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--case", default="marketsynth_saas", help="marketsynth_saas|weak_brief|weak_commercial|all")
    parser.add_argument("--skip-provider-smoke", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=3.0)
    parser.add_argument("--timeout-seconds", type=float, default=540.0)
    parser.add_argument("--artifact-dir", default="artifacts/real-research-readiness")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_main_async(args)))


if __name__ == "__main__":
    main()
