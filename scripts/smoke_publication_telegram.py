#!/usr/bin/env python3
"""Phase 7.0 — smoke: approve asset → queue telegram job → process (+ optional replay).

Safe skip without BOTFAZER_API_KEY/SMOKE_API_KEY or TELEGRAM_PUBLICATION_BOT_TOKEN.
"""

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

    token = os.environ.get("TELEGRAM_PUBLICATION_BOT_TOKEN", "").strip()
    if not token:
        return skip("TELEGRAM_PUBLICATION_BOT_TOKEN not set")

    chat_id = os.environ.get("TELEGRAM_PUBLICATION_CHAT_ID", "").strip()
    if not chat_id:
        return skip(
            "TELEGRAM_PUBLICATION_CHAT_ID not set (telegram channel config requires chat_id)",
        )

    mode = os.environ.get("TELEGRAM_PUBLICATION_SMOKE_MODE", "text").strip().lower()
    image_url = os.environ.get("TELEGRAM_PUBLICATION_SMOKE_IMAGE_URL", "").strip()
    if mode not in ("text", "photo"):
        return skip(
            f"TELEGRAM_PUBLICATION_SMOKE_MODE={mode!r} is not supported "
            "(expected text|photo)",
        )
    if mode == "photo" and not image_url:
        return skip(
            "TELEGRAM_PUBLICATION_SMOKE_MODE=photo but "
            "TELEGRAM_PUBLICATION_SMOKE_IMAGE_URL not set",
        )

    status, health = request_json("GET", f"{base}/health", api_key=api_key)
    if status != 200:
        return fail(f"health check returned {status}: {health}")

    status, project = request_json(
        "POST",
        f"{base}/projects",
        api_key=api_key,
        body={"name": "smoke-publication-telegram"},
    )
    if status != 201 or not isinstance(project, dict):
        return fail(f"create project failed: {status} {project}")
    project_id = project["id"]

    if mode == "photo":
        body = {
            "type": "email",
            "title": "Smoke TG photo publish",
            "body": "Hello from BotFazer (photo smoke)",
            "metadata": {"media_url": image_url},
        }
    else:
        body = {
            "type": "email",
            "title": "Smoke TG publish",
            "body": "Hello from BotFazer (smoke)",
        }

    status, asset = request_json(
        "POST",
        f"{base}/projects/{project_id}/content-assets",
        api_key=api_key,
        body=body,
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

    status, channel = request_json(
        "POST",
        f"{base}/projects/{project_id}/publishing-channels",
        api_key=api_key,
        body={
            "name": "Smoke Telegram",
            "type": "telegram",
            "config": {
                "chat_id": chat_id,
                "parse_mode": None,
                "disable_web_page_preview": True,
            },
        },
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
        body=None,
    )
    delivery_status = "none"
    if status == 200 and isinstance(deliveries, list) and deliveries:
        delivery_status = deliveries[0].get("status", "unknown")

    print(
        f"mode={mode} "
        f"job_status={job_final.get('status')} "
        f"attempts={job_final.get('attempts')} "
        f"delivery_status={delivery_status} "
        f"processed={processed.get('processed_count', processed)}",
    )

    if job_final.get("status") in ("failed", "cancelled"):
        status, replay = request_json(
            "POST",
            f"{base}/projects/{project_id}/publication-jobs/{job_id}/replay",
            api_key=api_key,
        )
        if status == 200:
            print("replay: queued (no auto-dispatch)")

    return ok("telegram publication smoke completed (no agent execution)")


if __name__ == "__main__":
    raise SystemExit(main())

