#!/usr/bin/env python3
"""Safe smoke: handoff graph dry-run + outbox listing (no outbound webhook by default)."""

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
        body={"name": "smoke-handoff-outbox"},
    )
    if status != 201 or not isinstance(project, dict):
        return fail(f"create project failed: {status} {project}")

    project_id = project["id"]

    status, orch = request_json(
        "POST",
        f"{base}/agents",
        api_key=api_key,
        body={"project_id": project_id, "type": "orchestrator", "name": "O"},
    )
    status, researcher = request_json(
        "POST",
        f"{base}/agents",
        api_key=api_key,
        body={"project_id": project_id, "type": "researcher", "name": "R"},
    )
    if status != 201 or not isinstance(orch, dict) or not isinstance(researcher, dict):
        return fail("create agents failed")

    status, run = request_json(
        "POST",
        f"{base}/agent-runs",
        api_key=api_key,
        body={
            "agent_id": orch["id"],
            "input_payload": {
                "prompt": "smoke handoff",
                "handoff_to_agent_id": researcher["id"],
                "handoff_enqueue_child": True,
                "handoff_execute_child": False,
            },
        },
    )
    if status != 201 or not isinstance(run, dict):
        return fail(f"create run failed: {status} {run}")

    status, graph_run = request_json(
        "POST",
        f"{base}/agent-runs/{run['id']}/execute-graph-dry-run",
        api_key=api_key,
    )
    if status != 200:
        return fail(f"graph dry-run failed: {status} {graph_run}")

    status, events = request_json(
        "GET",
        f"{base}/projects/{project_id}/events",
        api_key=api_key,
    )
    if status != 200:
        return fail(f"list events failed: {status} {events}")

    status, metrics = request_json(
        "GET",
        f"{base}/projects/{project_id}/operational-metrics",
        api_key=api_key,
    )
    if status != 200 or not isinstance(metrics, dict):
        return fail(f"operational metrics failed: {status} {metrics}")

    return ok(
        f"handoff graph dry-run ok; events listed; metrics window={metrics.get('window')}",
    )


if __name__ == "__main__":
    raise SystemExit(main())
