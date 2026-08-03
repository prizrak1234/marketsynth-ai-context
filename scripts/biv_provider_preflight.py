#!/usr/bin/env python3

"""HARDENING-01 provider preflight — credential presence + live smoke without secrets."""



from __future__ import annotations



import argparse

import asyncio

import json

import sys

from pathlib import Path

from typing import Any



from app.business_idea_validation.direct_http_fetch import probe_direct_http_fetch

from app.business_idea_validation.fetch_contour_readiness import assess_fetch_contour

from app.business_idea_validation.real_research_readiness import provider_smoke_passed

from app.core.config import get_settings

from app.research_source_collection.readiness import collection_readiness, probe_providers





def _credential_status(settings) -> dict[str, Any]:

    firecrawl = bool(settings.firecrawl_api_key and settings.firecrawl_api_key.get_secret_value().strip())

    xmlriver = bool(

        settings.xmlriver_user_id

        and settings.xmlriver_api_key

        and settings.xmlriver_api_key.get_secret_value().strip()

    )

    llm = bool(

        (settings.openai_api_key and settings.openai_api_key.get_secret_value().strip())

        or (settings.anthropic_api_key and settings.anthropic_api_key.get_secret_value().strip())

        or (settings.routellm_api_key and settings.routellm_api_key.get_secret_value().strip())

    )

    return {

        "firecrawl": {"present": firecrawl, "env": "FIRECRAWL_API_KEY"},

        "xmlriver": {

            "present": xmlriver,

            "env": "XMLRIVER_USER_ID + XMLRIVER_API_KEY",

        },

        "llm": {

            "present": llm,

            "env": "OPENAI_API_KEY or ANTHROPIC_API_KEY or ROUTELLM_API_KEY",

        },

    }





def _missing_credentials(creds: dict[str, Any]) -> list[dict[str, str]]:

    missing: list[dict[str, str]] = []

    for provider, row in creds.items():

        if not row["present"]:

            missing.append({"provider": provider, "required_env": row["env"]})

    return missing





def _firecrawl_detail(probe_payload: dict[str, Any]) -> dict[str, Any]:

    fc = (probe_payload.get("providers") or {}).get("firecrawl") or {}

    error_class = fc.get("safe_error_code") or "unknown"

    reachable = fc.get("reachable")

    auth_ok = fc.get("authentication_valid")

    if error_class == "credits_exhausted":

        status = "FAIL"

        http_status = 402

        retryable = False

    elif fc.get("state") == "ready":

        status = "PASS"

        http_status = 200

        retryable = False

        error_class = None

    elif not reachable and error_class == "provider_error":

        status = "FAIL"

        http_status = None

        retryable = False

    elif error_class in {"invalid_credentials", "auth_error"}:

        status = "FAIL"

        http_status = 401

        retryable = False

    elif error_class == "rate_limited":

        status = "FAIL"

        http_status = 429

        retryable = True

    else:

        status = "FAIL"

        http_status = None

        retryable = error_class in {"provider_unavailable", "timeout"}

    return {

        "provider": "firecrawl",

        "status": status,

        "http_status": http_status,

        "error_class": error_class,

        "retryable": retryable,

        "quota_remaining": None,

        "correlation_id": None,

        "reachable": reachable,

        "authentication_valid": auth_ok,

        "latency_ms": fc.get("latency_ms"),

        "adapter_version": "firecrawl_fetch/v1/scrape",

    }





def _fetch_contour_pass(
    *,
    xmlriver_status: str,
    firecrawl_detail: dict[str, Any],
    direct_http: dict[str, Any],
    fetch_contour: dict[str, Any] | None = None,
) -> tuple[bool, str, str]:
    """Return (pass, decision_code, rationale)."""
    if fetch_contour and fetch_contour.get("pass"):
        state = fetch_contour.get("state", "")
        ops = fetch_contour.get("operational_providers") or []
        if state == "ready":
            return True, "A_fetch_contour_ready", f"Fetch contour ready: {','.join(ops)}."
        return (
            True,
            "B_fetch_contour_degraded",
            f"Degraded fetch contour operational: {','.join(ops)}.",
        )
    if xmlriver_status != "PASS":
        return False, "search_unavailable", "XMLRiver search probe failed."

    if firecrawl_detail["status"] == "PASS":

        return True, "A_firecrawl_restored", "Firecrawl fetch probe succeeded."

    if direct_http.get("status") == "PASS":

        if firecrawl_detail.get("error_class") == "credits_exhausted":

            return (

                True,

                "B_firecrawl_credits_exhausted_direct_http_fallback",

                "Firecrawl credits exhausted; direct HTTP fallback verified.",

            )

        return (

            True,

            "B_firecrawl_unavailable_direct_http_fallback",

            "Firecrawl unavailable; direct HTTP fallback verified.",

        )

    if firecrawl_detail.get("error_class") == "credits_exhausted":

        return False, "D_owner_credits_action", "Firecrawl credits exhausted and direct HTTP fallback failed."

    return False, "fetch_contour_blocked", "Neither Firecrawl nor direct HTTP fetch contour is viable."





async def run_preflight(*, live: bool) -> dict[str, Any]:

    settings = get_settings()

    creds = _credential_status(settings)

    missing = _missing_credentials(creds)



    if settings.research_source_collection_mock_providers:

        probe_payload = collection_readiness(settings)

        probe_payload["probe_skipped"] = "mock_providers_enabled"

        research_ok, blocker = False, "mock_providers_enabled"

    elif missing and any(m["provider"] in {"firecrawl", "xmlriver"} for m in missing):

        probe_payload = {"status": "blocked", "providers": {}, "mock_providers": False}

        research_ok, blocker = False, "missing_research_credentials"

    else:

        probe_payload = await probe_providers(settings, live=live)
        fetch_contour = await assess_fetch_contour(settings, live=live)
        probe_payload["fetch_contour"] = fetch_contour
        research_ok, blocker = provider_smoke_passed(probe_payload)



    direct_http_probe: dict[str, Any] = {"status": "SKIPPED", "reason": "live_probe_disabled"}

    if live and not settings.research_source_collection_mock_providers:

        try:

            dh = await probe_direct_http_fetch()

            direct_http_probe = {

                "provider": "direct_http",

                "status": "PASS" if dh.get("ok") else "FAIL",

                "http_status": dh.get("http_status"),

                "error_class": None if dh.get("ok") else "extraction_rejected",

                "retryable": True,

                "extraction_status": dh.get("extraction_status"),

                "extracted_len": dh.get("extracted_len"),

                "latency_ms": dh.get("latency_ms"),

            }

        except Exception as exc:  # noqa: BLE001

            direct_http_probe = {

                "provider": "direct_http",

                "status": "FAIL",

                "http_status": None,

                "error_class": type(exc).__name__,

                "retryable": True,

            }



    llm_status = "PASS" if creds["llm"]["present"] else "FAIL"

    providers_summary: dict[str, str] = {}

    external_blockers: list[dict[str, str]] = [

        {

            "provider": m["provider"],

            "issue": "missing_credential",

            "required_env": m["required_env"],

            "owner_action": f"Set {m['required_env']} in .env and restart the API.",

        }

        for m in missing

    ]



    for name, row in (probe_payload.get("providers") or {}).items():

        state = str(row.get("state") or "unknown")

        if state in {"ready", "partially_ready"} and name == "firecrawl" and row.get("reachable") is False:

            providers_summary[name] = "FAIL"

        elif state == "ready":

            providers_summary[name] = "PASS"

        elif state == "partially_ready" and name == "firecrawl" and row.get("safe_error_code") == "credits_exhausted":

            providers_summary[name] = "FAIL"

        elif state == "partially_ready":

            providers_summary[name] = "FAIL"

        elif not creds.get(name, {}).get("present", True):

            providers_summary[name] = "BLOCKED"

        else:

            providers_summary[name] = "FAIL"



    if not creds["firecrawl"]["present"]:

        providers_summary.setdefault("firecrawl", "BLOCKED")

    else:

        providers_summary.setdefault("firecrawl", providers_summary.get("firecrawl", "FAIL"))

    if not creds["xmlriver"]["present"]:

        providers_summary.setdefault("xmlriver", "BLOCKED")

    else:

        providers_summary.setdefault("xmlriver", providers_summary.get("xmlriver", "PASS"))



    firecrawl_detail = _firecrawl_detail(probe_payload)

    fetch_contour_ok, provider_decision, fetch_rationale = _fetch_contour_pass(
        xmlriver_status=providers_summary.get("xmlriver", "FAIL"),
        firecrawl_detail=firecrawl_detail,
        direct_http=direct_http_probe,
        fetch_contour=probe_payload.get("fetch_contour"),
    )



    if firecrawl_detail["status"] == "FAIL" and firecrawl_detail.get("error_class") == "credits_exhausted":

        external_blockers.append(

            {

                "provider": "firecrawl",

                "issue": "credits_exhausted",

                "required_env": "FIRECRAWL_API_KEY",

                "owner_action": (

                    "Top up Firecrawl credits at https://firecrawl.dev/pricing "

                    "or continue with direct HTTP fallback for this run."

                ),

            }

        )

    elif providers_summary.get("firecrawl") == "FAIL":

        fc = (probe_payload.get("providers") or {}).get("firecrawl") or {}

        external_blockers.append(

            {

                "provider": "firecrawl",

                "issue": fc.get("safe_error_code") or "provider_unavailable",

                "required_env": "FIRECRAWL_API_KEY",

                "owner_action": "Verify Firecrawl API key, quota, and rate limits.",

            }

        )



    overall = "PASS" if fetch_contour_ok and llm_status == "PASS" and not missing else ("BLOCKED" if missing else "FAIL")



    return {

        "overall": overall,

        "research_providers_pass": research_ok,

        "fetch_contour_pass": fetch_contour_ok,

        "provider_decision": provider_decision,

        "fetch_contour_rationale": fetch_rationale,

        "provider_preflight": providers_summary,

        "llm": llm_status,

        "credentials": {k: {"present": v["present"], "env": v["env"]} for k, v in creds.items()},

        "external_blockers": external_blockers,

        "firecrawl": firecrawl_detail,

        "direct_http": direct_http_probe,

        "probe": {

            "status": probe_payload.get("status"),

            "mock_providers": probe_payload.get("mock_providers"),

            "providers": probe_payload.get("providers"),

        },

    }





def main() -> None:

    parser = argparse.ArgumentParser(description="BIV provider preflight for HARDENING-01")

    parser.add_argument("--no-live", action="store_true")

    parser.add_argument("--json", action="store_true")

    parser.add_argument(

        "--out",

        default="artifacts/real-research-readiness/hardening-01/provider-preflight.json",

    )

    args = parser.parse_args()

    result = asyncio.run(run_preflight(live=not args.no_live))

    out_path = Path(args.out)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:

        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:

        print(f"Overall: {result['overall']}")

        print(f"Fetch contour: {'PASS' if result['fetch_contour_pass'] else 'FAIL'} ({result['provider_decision']})")

        fc = result["firecrawl"]

        print(

            f"Firecrawl: {fc['status']} http={fc.get('http_status')} "

            f"error={fc.get('error_class')} retryable={fc.get('retryable')}"

        )

        dh = result["direct_http"]

        print(f"Direct HTTP: {dh.get('status')} http={dh.get('http_status')} extracted={dh.get('extracted_len')}")

        print(f"XMLRiver: {result['provider_preflight'].get('xmlriver', '—')}")

        print(f"LLM: {result['llm']}")

        if result["external_blockers"]:

            print("External blockers:")

            for b in result["external_blockers"]:

                print(f"  - {b['provider']}: {b['issue']}")

    raise SystemExit(0 if result["overall"] == "PASS" else 1)





if __name__ == "__main__":

    main()

