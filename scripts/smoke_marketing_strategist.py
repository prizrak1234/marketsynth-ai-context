#!/usr/bin/env python3
"""Smoke: strategist brief + funnel → run → strategy draft quality (no approve)."""

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
        body={"name": "smoke-strategist"},
    )
    if status != 201 or not isinstance(project, dict):
        return fail(f"create project failed: {status} {project}")

    project_id = project["id"]

    status, brief = request_json(
        "POST",
        f"{base}/projects/{project_id}/marketing-briefs",
        api_key=api_key,
        body={"title": "Smoke brief", "offer": "Smoke offer"},
    )
    if status != 201 or not isinstance(brief, dict):
        return fail(f"create brief failed: {status} {brief}")

    status, funnel = request_json(
        "POST",
        f"{base}/projects/{project_id}/funnels",
        api_key=api_key,
        body={"title": "Smoke funnel", "brief_id": brief["id"]},
    )
    if status != 201 or not isinstance(funnel, dict):
        return fail(f"create funnel failed: {status} {funnel}")

    status, agent = request_json(
        "POST",
        f"{base}/agents",
        api_key=api_key,
        body={"project_id": project_id, "type": "strategist"},
    )
    if status != 201 or not isinstance(agent, dict):
        return fail(f"create strategist failed: {status} {agent}")

    agent_id = agent["id"]
    config = dict(agent.get("config") or {})
    config["mock_strategy_flow"] = True
    status, patched = request_json(
        "PATCH",
        f"{base}/agents/{agent_id}",
        api_key=api_key,
        body={"config": config},
    )
    if status != 200 or not isinstance(patched, dict):
        return fail(f"patch strategist config failed: {status} {patched}")

    status, run = request_json(
        "POST",
        f"{base}/agent-runs",
        api_key=api_key,
        body={
            "agent_id": agent_id,
            "input_payload": {
                "brief_id": brief["id"],
                "funnel_id": funnel["id"],
                "goal": "analyze funnel and create strategy draft",
            },
        },
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

    status, assets = request_json(
        "GET",
        f"{base}/projects/{project_id}/content-assets",
        api_key=api_key,
    )
    if status != 200 or not isinstance(assets, list):
        return fail(f"list assets failed: {status} {assets}")

    draft = next(
        (item for item in assets if item.get("title") == "Marketing Strategy Draft"),
        None,
    )
    if draft is None:
        print(
            "warn: no strategy draft asset created "
            "(enable AGENT_WRITE_TOOLS_ENABLED and "
            "AGENT_WRITE_TOOL_CONTENT_ASSET_CREATE_DRAFT_ENABLED on the server)",
        )
        return ok(f"strategist run {run['id']} succeeded without draft asset")

    status, quality = request_json(
        "GET",
        f"{base}/projects/{project_id}/content-assets/{draft['id']}/quality",
        api_key=api_key,
    )
    if status != 200 or not isinstance(quality, dict):
        return fail(f"quality endpoint failed: {status} {quality}")

    print(f"draft_asset_id={draft['id']}")
    print(f"quality_score={quality.get('score')}")
    print(f"missing_sections={quality.get('missing_sections')}")
    return ok(
        f"strategist smoke completed — draft {draft['id']} score={quality.get('score')}",
    )


if __name__ == "__main__":
    raise SystemExit(main())
