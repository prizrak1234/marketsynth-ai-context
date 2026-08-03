#!/usr/bin/env python3
"""Phase 6.4 — smoke: approve asset → queue publication job → process (no agent runs)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._smoke_util import fail, ok, request_json, skip, smoke_env


def main() -> int:
    api_key, base = smoke_env()
    if not api_key:
        return skip("BOTFAZER_API_KEY or SMOKE_API_KEY not set")

    webhook_url = os.environ.get("WEBHOOK_TEST_URL", "").strip()
    use_real_webhook = bool(webhook_url)

    status, health = request_json("GET", f"{base}/health", api_key=api_key)
    if status != 200:
        return fail(f"health check returned {status}: {health}")

    status, ops = request_json("GET", f"{base}/health/operations", api_key=api_key)
    if status not in (200, 503) or not isinstance(ops, dict):
        return fail(f"health/operations failed: {status} {ops}")

    status, project = request_json(
        "POST",
        f"{base}/projects",
        api_key=api_key,
        body={"name": "smoke-publication-webhook"},
    )
    if status != 201 or not isinstance(project, dict):
        return fail(f"create project failed: {status} {project}")
    project_id = project["id"]

    status, asset = request_json(
        "POST",
        f"{base}/projects/{project_id}/content-assets",
        api_key=api_key,
        body={"type": "email", "title": "Smoke publish", "body": "Smoke body"},
    )
    if status != 201 or not isinstance(asset, dict):
        return fail(f"create asset failed: {status} {asset}")
    asset_id = asset["id"]

    status, approved = request_json(
        "POST",
        f"{base}/projects/{project_id}/content-assets/{asset_id}/approve",
        api_key=api_key,
    )
    if status != 200:
        return fail(f"approve asset failed: {status} {approved}")

    if use_real_webhook:
        channel_body = {
            "name": "Smoke webhook",
            "type": "webhook",
            "config": {"url": webhook_url},
        }
        channel_note = f"webhook → {webhook_url}"
    else:
        channel_body = {"name": "Smoke custom noop", "type": "custom", "config": {}}
        channel_note = "custom noop (WEBHOOK_TEST_URL not set — skip real webhook)"

    status, channel = request_json(
        "POST",
        f"{base}/projects/{project_id}/publishing-channels",
        api_key=api_key,
        body=channel_body,
    )
    if status != 201 or not isinstance(channel, dict):
        return fail(f"create channel failed: {status} {channel}")
    channel_id = channel["id"]

    status, job = request_json(
        "POST",
        f"{base}/projects/{project_id}/publication-jobs",
        api_key=api_key,
        body={"asset_id": asset_id, "channel_id": channel_id},
    )
    if status != 201 or not isinstance(job, dict):
        return fail(f"queue job failed: {status} {job}")
    job_id = job["id"]

    status, processed = request_json(
        "POST",
        f"{base}/projects/{project_id}/publication-jobs/process",
        api_key=api_key,
    )
    if status != 200 or not isinstance(processed, dict):
        return fail(f"process jobs failed: {status} {processed}")

    status, job_final = request_json(
        "GET",
        f"{base}/projects/{project_id}/publication-jobs/{job_id}",
        api_key=api_key,
    )
    if status != 200 or not isinstance(job_final, dict):
        return fail(f"get job failed: {status} {job_final}")

    status, deliveries = request_json(
        "GET",
        f"{base}/projects/{project_id}/publication-deliveries",
        api_key=api_key,
    )
    delivery_status = "none"
    if status == 200 and isinstance(deliveries, list) and deliveries:
        delivery_status = deliveries[0].get("status", "unknown")

    print(
        f"channel: {channel_note}\n"
        f"job_status={job_final.get('status')} "
        f"attempts={job_final.get('attempts')} "
        f"delivery_status={delivery_status} "
        f"processed={processed.get('processed', processed)}",
    )

    if not use_real_webhook:
        print("skip: real webhook (set WEBHOOK_TEST_URL to exercise outbound HTTP)")

    return ok("publication smoke completed (no agent execution)")


if __name__ == "__main__":
    raise SystemExit(main())
