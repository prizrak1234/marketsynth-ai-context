#!/usr/bin/env python3
"""Phase 5.8 — smoke: tool matrix, specialist mock flows, orchestrator workflow summary."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.marketing.workflow_smoke import (
    agent_config_with_mock_flow,
    create_orchestrator_run_payload,
)

from scripts._smoke_util import fail, ok, request_json, skip, smoke_env

_PROCESS_HANDOFF = "/agent-runs/process-handoff-children"

_SPECIALIST_FLOWS: tuple[tuple[str, str], ...] = (
    ("strategist", "mock_strategy_flow"),
    ("researcher", "mock_researcher_flow"),
    ("content_planner", "mock_content_planner_flow"),
    ("copywriter", "mock_copywriter_flow"),
    ("critic", "mock_critic_flow"),
)


def main() -> int:
    api_key, base = smoke_env()
    if not api_key:
        return skip("BOTFAZER_API_KEY or SMOKE_API_KEY not set")

    status, health = request_json("GET", f"{base}/health", api_key=api_key)
    if status != 200:
        return fail(f"health check returned {status}: {health}")

    status, matrix = request_json("GET", f"{base}/agents/tool-matrix", api_key=api_key)
    if status != 200 or not isinstance(matrix, dict):
        return fail(f"tool-matrix failed: {status} {matrix}")
    if "agents" not in matrix or len(matrix["agents"]) < 7:
        return fail("tool-matrix missing agent rows")

    status, project = request_json(
        "POST",
        f"{base}/projects",
        api_key=api_key,
        body={"name": "smoke-phase-5-agents"},
    )
    if status != 201 or not isinstance(project, dict):
        return fail(f"create project failed: {status} {project}")
    project_id = project["id"]

    status, brief = request_json(
        "POST",
        f"{base}/projects/{project_id}/marketing-briefs",
        api_key=api_key,
        body={"title": "Phase 5 smoke brief", "offer": "Offer"},
    )
    if status != 201 or not isinstance(brief, dict):
        return fail(f"create brief failed: {status} {brief}")

    status, funnel = request_json(
        "POST",
        f"{base}/projects/{project_id}/funnels",
        api_key=api_key,
        body={"title": "Phase 5 smoke funnel", "brief_id": brief["id"]},
    )
    if status != 201 or not isinstance(funnel, dict):
        return fail(f"create funnel failed: {status} {funnel}")

    request_json(
        "POST",
        f"{base}/projects/{project_id}/funnels/{funnel['id']}/steps",
        api_key=api_key,
        body={"step_type": "awareness", "title": "Awareness"},
    )

    for agent_type, flow_key in _SPECIALIST_FLOWS:
        status, agent = request_json(
            "POST",
            f"{base}/agents",
            api_key=api_key,
            body={"project_id": project_id, "type": agent_type},
        )
        if status != 201 or not isinstance(agent, dict):
            return fail(f"create {agent_type} failed: {status} {agent}")
        config = agent_config_with_mock_flow(agent.get("config"), flow_key)
        status, patched = request_json(
            "PATCH",
            f"{base}/agents/{agent['id']}",
            api_key=api_key,
            body={"config": config},
        )
        if status != 200:
            return fail(f"patch {agent_type} config failed: {status} {patched}")
        status, run = request_json(
            "POST",
            f"{base}/agent-runs",
            api_key=api_key,
            body={
                "agent_id": agent["id"],
                "input_payload": {
                    "goal": f"smoke {agent_type}",
                    "funnel_id": funnel["id"],
                    "brief_id": brief["id"],
                },
            },
        )
        if status != 201:
            return fail(f"create {agent_type} run failed: {status} {run}")
        status, executed = request_json(
            "POST",
            f"{base}/agent-runs/{run['id']}/execute-dry-run",
            api_key=api_key,
        )
        if status != 200 or not isinstance(executed, dict):
            return fail(f"execute {agent_type} failed: {status} {executed}")
        if executed.get("status") != "succeeded":
            return fail(f"{agent_type} run expected succeeded, got {executed.get('status')}")
        print(f"ok: {agent_type} mock flow succeeded")

    status, orchestrator = request_json(
        "POST",
        f"{base}/agents",
        api_key=api_key,
        body={"project_id": project_id, "type": "orchestrator"},
    )
    if status != 201 or not isinstance(orchestrator, dict):
        return fail(f"create orchestrator failed: {status} {orchestrator}")
    orch_config = agent_config_with_mock_flow(
        orchestrator.get("config"),
        "mock_orchestrator_flow",
    )
    request_json(
        "PATCH",
        f"{base}/agents/{orchestrator['id']}",
        api_key=api_key,
        body={"config": orch_config},
    )
    request_json(
        "POST",
        f"{base}/agents",
        api_key=api_key,
        body={"project_id": project_id, "type": "content_planner"},
    )

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
    if status != 201:
        return fail(f"orchestrator run failed: {status} {parent_run}")
    parent_id = parent_run["id"] if isinstance(parent_run, dict) else ""
    request_json(
        "POST",
        f"{base}/agent-runs/{parent_id}/execute-graph-dry-run",
        api_key=api_key,
    )
    request_json("POST", f"{base}{_PROCESS_HANDOFF}?limit=5", api_key=api_key)

    status, summary = request_json(
        "GET",
        f"{base}/agent-runs/{parent_id}/workflow-summary",
        api_key=api_key,
    )
    if status != 200 or not isinstance(summary, dict):
        return fail(f"workflow-summary failed: {status} {summary}")
    if not summary.get("child_runs"):
        return fail("workflow-summary expected at least one child run")

    print(f"project_id={project_id}")
    print(f"parent_run_id={parent_id}")
    print(f"child_runs={len(summary.get('child_runs', []))}")
    return ok("phase 5 agents smoke completed (no auto-approve)")


if __name__ == "__main__":
    raise SystemExit(main())
