#!/usr/bin/env python3
"""Smoke: orchestrator → content planner → critic review (no approve unless --approve-draft)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.marketing.workflow_smoke import (
    create_critic_run_payload,
    create_orchestrator_run_payload,
)

from scripts._smoke_util import fail, ok, request_json, skip, smoke_env

_PROCESS_HANDOFF = "/agent-runs/process-handoff-children"


def _patch_agent_config(
    base_url: str,
    api_key: str,
    agent_id: str,
    config: dict,
) -> tuple[int, dict | None]:
    return request_json(
        "PATCH",
        f"{base_url}/agents/{agent_id}",
        api_key=api_key,
        body={"config": config},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Marketing workflow smoke")
    parser.add_argument(
        "--approve-draft",
        action="store_true",
        help="Approve the content plan draft via API (default: skip approve)",
    )
    args = parser.parse_args()

    api_key, base = smoke_env()
    if not api_key:
        return skip("BOTFAZER_API_KEY or SMOKE_API_KEY not set")

    status, health = request_json("GET", f"{base}/health", api_key=api_key)
    if status != 200:
        return fail(f"health check returned {status}: {health}")

    status, project = request_json(
        "POST",
        f"{base}/projects",
        api_key=api_key,
        body={"name": "smoke-marketing-workflow"},
    )
    if status != 201 or not isinstance(project, dict):
        return fail(f"create project failed: {status} {project}")
    project_id = project["id"]

    status, brief = request_json(
        "POST",
        f"{base}/projects/{project_id}/marketing-briefs",
        api_key=api_key,
        body={"title": "Smoke workflow brief", "offer": "Smoke offer"},
    )
    if status != 201 or not isinstance(brief, dict):
        return fail(f"create brief failed: {status} {brief}")

    status, funnel = request_json(
        "POST",
        f"{base}/projects/{project_id}/funnels",
        api_key=api_key,
        body={"title": "Smoke workflow funnel", "brief_id": brief["id"]},
    )
    if status != 201 or not isinstance(funnel, dict):
        return fail(f"create funnel failed: {status} {funnel}")

    status, _step = request_json(
        "POST",
        f"{base}/projects/{project_id}/funnels/{funnel['id']}/steps",
        api_key=api_key,
        body={"step_type": "awareness", "title": "Awareness"},
    )
    if status != 201:
        return fail(f"create funnel step failed: {status} {_step}")

    status, orchestrator = request_json(
        "POST",
        f"{base}/agents",
        api_key=api_key,
        body={"project_id": project_id, "type": "orchestrator"},
    )
    if status != 201 or not isinstance(orchestrator, dict):
        return fail(f"create orchestrator failed: {status} {orchestrator}")

    status, planner = request_json(
        "POST",
        f"{base}/agents",
        api_key=api_key,
        body={"project_id": project_id, "type": "content_planner"},
    )
    if status != 201 or not isinstance(planner, dict):
        return fail(f"create content_planner failed: {status} {planner}")

    status, critic = request_json(
        "POST",
        f"{base}/agents",
        api_key=api_key,
        body={"project_id": project_id, "type": "critic"},
    )
    if status != 201 or not isinstance(critic, dict):
        return fail(f"create critic failed: {status} {critic}")

    orch_cfg = dict(orchestrator.get("config") or {})
    orch_cfg["mock_orchestrator_flow"] = True
    _patch_agent_config(base, api_key, orchestrator["id"], orch_cfg)

    planner_cfg = dict(planner.get("config") or {})
    planner_cfg["mock_content_planner_flow"] = True
    _patch_agent_config(base, api_key, planner["id"], planner_cfg)

    critic_cfg = dict(critic.get("config") or {})
    critic_cfg["mock_critic_flow"] = True
    _patch_agent_config(base, api_key, critic["id"], critic_cfg)

    status, parent_run = request_json(
        "POST",
        f"{base}/agent-runs",
        api_key=api_key,
        body={
            "agent_id": orchestrator["id"],
            "input_payload": create_orchestrator_run_payload(
                brief_id=brief["id"],
                funnel_id=funnel["id"],
            ),
        },
    )
    if status != 201 or not isinstance(parent_run, dict):
        return fail(f"create orchestrator run failed: {status} {parent_run}")

    parent_id = parent_run["id"]
    status, executed = request_json(
        "POST",
        f"{base}/agent-runs/{parent_id}/execute-graph-dry-run",
        api_key=api_key,
    )
    if status != 200:
        return fail(f"orchestrator graph execute failed: {status} {executed}")

    status, worker = request_json(
        "POST",
        f"{base}{_PROCESS_HANDOFF}?limit=5",
        api_key=api_key,
    )
    if status != 200:
        return fail(f"process handoff children failed: {status} {worker}")

    status, parent_body = request_json(
        "GET",
        f"{base}/agent-runs/{parent_id}",
        api_key=api_key,
    )
    if status != 200 or not isinstance(parent_body, dict):
        return fail(f"get parent run failed: {status} {parent_body}")

    handoff = (parent_body.get("output_payload") or {}).get("handoff") or {}
    child_id = handoff.get("child_run_id")
    if not child_id:
        return fail("parent handoff missing child_run_id")

    status, assets = request_json(
        "GET",
        f"{base}/projects/{project_id}/content-assets",
        api_key=api_key,
    )
    if status != 200 or not isinstance(assets, list):
        return fail(f"list assets failed: {status} {assets}")

    plan_asset = None
    for asset in assets:
        if asset.get("agent_run_id") == child_id:
            plan_asset = asset
            break
    if plan_asset is None:
        return fail("content plan draft not found for child run")

    status, critic_run = request_json(
        "POST",
        f"{base}/agent-runs",
        api_key=api_key,
        body={
            "agent_id": critic["id"],
            "input_payload": create_critic_run_payload(
                source_asset_id=plan_asset["id"],
                brief_id=brief["id"],
                funnel_id=funnel["id"],
            ),
        },
    )
    if status != 201 or not isinstance(critic_run, dict):
        return fail(f"create critic run failed: {status} {critic_run}")

    status, critic_exec = request_json(
        "POST",
        f"{base}/agent-runs/{critic_run['id']}/execute-graph-dry-run",
        api_key=api_key,
    )
    if status != 200:
        return fail(f"critic graph execute failed: {status} {critic_exec}")

    status, assets_after = request_json(
        "GET",
        f"{base}/projects/{project_id}/content-assets",
        api_key=api_key,
    )
    review_assets = []
    if isinstance(assets_after, list):
        plan_id = plan_asset["id"]
        for asset in assets_after:
            meta = asset.get("metadata") or {}
            if meta.get("source_asset_id") == plan_id or meta.get("purpose") == "content_review":
                review_assets.append(asset)

    print(f"project_id={project_id}")
    print(f"parent_run_id={parent_id}")
    print(f"child_run_id={child_id}")
    print(f"plan_asset_id={plan_asset['id']}")
    plan_quality = (plan_asset.get("metadata") or {}).get("quality") or {}
    print(f"plan_quality_score={plan_quality.get('score')}")
    if review_assets:
        review = review_assets[0]
        print(f"review_asset_id={review['id']}")
        review_quality = (review.get("metadata") or {}).get("quality") or {}
        print(f"review_quality_score={review_quality.get('score')}")

    if args.approve_draft:
        status, approved = request_json(
            "POST",
            f"{base}/projects/{project_id}/content-assets/{plan_asset['id']}/approve",
            api_key=api_key,
        )
        if status != 200:
            return fail(f"approve failed: {status} {approved}")
        print(f"approved_version_number={approved.get('approved_version_number')}")

    return ok("marketing workflow smoke completed")


if __name__ == "__main__":
    raise SystemExit(main())
