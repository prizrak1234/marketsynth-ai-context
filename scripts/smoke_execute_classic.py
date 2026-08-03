#!/usr/bin/env python3
"""Safe smoke: create queued run and execute via classic (no real webhooks)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._smoke_util import fail, ok, request_json, skip, smoke_env


def main() -> int:
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
        body={"name": "smoke-classic"},
    )
    if status != 201 or not isinstance(project, dict):
        return fail(f"create project failed: {status} {project}")

    status, agent = request_json(
        "POST",
        f"{base}/agents",
        api_key=api_key,
        body={"project_id": project["id"], "type": "researcher", "name": "Smoke"},
    )
    if status != 201 or not isinstance(agent, dict):
        return fail(f"create agent failed: {status} {agent}")

    status, run = request_json(
        "POST",
        f"{base}/agent-runs",
        api_key=api_key,
        body={"agent_id": agent["id"], "input_payload": {"prompt": "smoke classic"}},
    )
    if status != 201 or not isinstance(run, dict):
        return fail(f"create run failed: {status} {run}")

    status, executed = request_json(
        "POST",
        f"{base}/agent-runs/{run['id']}/execute?engine=classic",
        api_key=api_key,
    )
    if status != 200 or not isinstance(executed, dict):
        return fail(f"execute failed: {status} {executed}")

    if executed.get("status") != "succeeded":
        return fail(f"expected succeeded, got {executed.get('status')}")

    execution = (executed.get("output_payload") or {}).get("execution") or {}
    if execution.get("engine") != "classic":
        return fail(f"expected execution.engine=classic, got {execution}")

    return ok(f"classic execute succeeded for run {run['id']}")


if __name__ == "__main__":
    raise SystemExit(main())
