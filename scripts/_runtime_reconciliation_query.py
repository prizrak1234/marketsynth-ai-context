#!/usr/bin/env python3
"""One-off RUNTIME-01G reconciliation DB query — sanitized output."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_session_factory


def mask_uuid(value) -> str | None:
    if value is None:
        return None
    s = str(value)
    return f"{s[:8]}****{s[-4:]}"


def terminal_fields(result_json: dict | None) -> tuple[str | None, str | None]:
    if not isinstance(result_json, dict):
        return None, None
    return result_json.get("result_kind"), result_json.get("research_terminal_state")


async def main() -> None:
    settings = get_settings()
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=36)
    factory = get_session_factory()

    async with factory() as session:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT r.id, r.project_id, r.user_request_id, r.owner_id,
                           r.created_at, r.updated_at, r.finished_at, r.status,
                           r.error_code, r.research_mode, r.result_json, r.progress_json,
                           p.name AS project_name
                    FROM business_idea_validation_runs r
                    LEFT JOIN projects p ON p.id = r.project_id
                    WHERE r.created_at >= :since
                    ORDER BY r.created_at DESC
                    """
                ),
                {"since": since},
            )
        ).mappings().all()

        recent: list[dict] = []
        for row in rows:
            ledger = (
                await session.execute(
                    text(
                        """
                        SELECT provider, outcome_code, COUNT(*) AS cnt
                        FROM biv_fetch_ledger_entries
                        WHERE run_id = :rid
                        GROUP BY provider, outcome_code
                        ORDER BY provider, outcome_code
                        """
                    ),
                    {"rid": row["id"]},
                )
            ).mappings().all()
            rk, rts = terminal_fields(row["result_json"])
            progress = row["progress_json"] if isinstance(row["progress_json"], dict) else {}
            recent.append(
                {
                    "run_id": str(row["id"]),
                    "project_id": str(row["project_id"]),
                    "project_name": row["project_name"],
                    "user_request_id": str(row["user_request_id"]),
                    "owner_id_masked": mask_uuid(row["owner_id"]),
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                    "finished_at": row["finished_at"].isoformat() if row["finished_at"] else None,
                    "status": row["status"],
                    "result_kind": rk,
                    "research_terminal_state": rts,
                    "error_code": row["error_code"],
                    "research_mode": row["research_mode"],
                    "progress_stage": progress.get("stage"),
                    "fetch_ledger_total": sum(x["cnt"] for x in ledger),
                    "fetch_by_provider_outcome": {
                        f"{x['provider']}:{x['outcome_code']}": x["cnt"] for x in ledger
                    },
                }
            )

        orphans = (
            await session.execute(
                text(
                    """
                    SELECT id, status, created_at, updated_at, finished_at,
                           error_code, project_id, user_request_id, owner_id
                    FROM business_idea_validation_runs
                    WHERE status IN ('queued', 'running', 'pending')
                    ORDER BY created_at DESC
                    """
                )
            )
        ).mappings().all()

        interrupted = (
            await session.execute(
                text(
                    """
                    SELECT id, status, error_code, created_at, updated_at, finished_at,
                           project_id, user_request_id, owner_id
                    FROM business_idea_validation_runs
                    WHERE error_code = 'research_execution_interrupted'
                      AND created_at >= :since
                    ORDER BY created_at DESC
                    """
                ),
                {"since": since},
            )
        ).mappings().all()

        fixture_count = (
            await session.execute(text("SELECT COUNT(*) FROM biv_e2e_deterministic_fixtures"))
        ).scalar()

    payload = {
        "feature_flags": {
            "app_env": settings.app_env,
            "biv_e2e_deterministic_enabled": settings.biv_e2e_deterministic_enabled,
            "biv_e2e_deterministic_allowed": settings.biv_e2e_deterministic_allowed,
            "research_source_collection_mock_providers": settings.research_source_collection_mock_providers,
            "business_idea_validation_enabled": settings.business_idea_validation_enabled,
            "biv_run_dispatcher_enabled": settings.biv_run_dispatcher_enabled,
        },
        "recent_runs": recent,
        "orphaned_active": [
            {
                "run_id": str(o["id"]),
                "status": o["status"],
                "project_id": str(o["project_id"]),
                "user_request_id": str(o["user_request_id"]),
                "owner_id_masked": mask_uuid(o["owner_id"]),
                "created_at": o["created_at"].isoformat() if o["created_at"] else None,
                "updated_at": o["updated_at"].isoformat() if o["updated_at"] else None,
                "finished_at": o["finished_at"].isoformat() if o["finished_at"] else None,
                "error_code": o["error_code"],
            }
            for o in orphans
        ],
        "interrupted_runs": [
            {
                "run_id": str(o["id"]),
                "status": o["status"],
                "error_code": o["error_code"],
                "project_id": str(o["project_id"]),
                "user_request_id": str(o["user_request_id"]),
                "owner_id_masked": mask_uuid(o["owner_id"]),
                "created_at": o["created_at"].isoformat() if o["created_at"] else None,
                "finished_at": o["finished_at"].isoformat() if o["finished_at"] else None,
            }
            for o in interrupted
        ],
        "fixture_count": fixture_count,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
