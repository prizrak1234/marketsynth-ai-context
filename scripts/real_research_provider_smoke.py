#!/usr/bin/env python3
"""Provider readiness smoke — gate before full real BIV research."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from app.business_idea_validation.real_research_readiness import provider_smoke_passed
from app.core.config import get_settings
from app.research_source_collection.readiness import collection_readiness, probe_providers


async def _run(*, live: bool, json_out: bool) -> int:
    settings = get_settings()
    if settings.research_source_collection_mock_providers:
        payload = collection_readiness(settings)
        payload["probe_skipped"] = "mock_providers_enabled"
    else:
        payload = await probe_providers(settings, live=live)

    ok, blocker = provider_smoke_passed(payload)
    result = {
        "pass": ok,
        "blocker": blocker,
        "status": payload.get("status"),
        "mock_providers": payload.get("mock_providers"),
        "providers": {
            name: {
                "state": row.get("state"),
                "configured": row.get("configured"),
                "reachable": row.get("reachable"),
                "authentication_valid": row.get("authentication_valid"),
                "safe_error_code": row.get("safe_error_code"),
                "latency_ms": row.get("latency_ms"),
            }
            for name, row in (payload.get("providers") or {}).items()
        },
    }
    if json_out:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Real providers: {'PASS' if ok else 'FAIL'}")
        if blocker:
            print(f"Blocker: {blocker}")
        for name, row in result["providers"].items():
            print(
                f"  {name}: state={row['state']} "
                f"auth={row['authentication_valid']} "
                f"error={row['safe_error_code']}"
            )
    return 0 if ok else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Research provider readiness smoke")
    parser.add_argument("--no-live", action="store_true", help="Credential check only")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    code = asyncio.run(_run(live=not args.no_live, json_out=args.json))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
