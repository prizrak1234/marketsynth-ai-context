"""DB/API assertions for RUNTIME-01G Playwright E2E (read-only)."""

from __future__ import annotations

import argparse
import asyncio
import json
from uuid import UUID

from app.db.models.business_idea_validation_run import BusinessIdeaValidationRunTable
from app.db.models.investigation import InvestigationTable
from app.db.session import get_session_factory
from app.schemas.contracts import InvestigationStatus
from sqlalchemy import text


async def _active_run_count(project_id: UUID) -> int:
    factory = get_session_factory()
    async with factory() as session:
        count = (
            await session.execute(
                text(
                    """
                    SELECT COUNT(*)::int
                    FROM business_idea_validation_runs
                    WHERE project_id = :project_id
                      AND status IN ('queued', 'running')
                    """
                ),
                {"project_id": str(project_id)},
            )
        ).scalar_one()
        return int(count)


async def _investigation_for_run(run_id: UUID) -> dict | None:
    factory = get_session_factory()
    async with factory() as session:
        row = await session.get(BusinessIdeaValidationRunTable, run_id)
        if row is None or row.investigation_id is None:
            return None
        inv = await session.get(InvestigationTable, row.investigation_id)
        if inv is None:
            return None
        return {
            "investigation_id": str(inv.id),
            "status": inv.status.value if hasattr(inv.status, "value") else str(inv.status),
            "superseded": inv.status == InvestigationStatus.SUPERSEDED,
        }


async def _run_snapshot(run_id: UUID) -> dict | None:
    factory = get_session_factory()
    async with factory() as session:
        row = await session.get(BusinessIdeaValidationRunTable, run_id)
        if row is None:
            return None
        progress_state = None
        if isinstance(row.progress_json, dict):
            progress_state = row.progress_json.get("state")
        return {
            "run_id": str(row.id),
            "project_id": str(row.project_id),
            "status": row.status.value if hasattr(row.status, "value") else str(row.status),
            "error_code": row.error_code,
            "has_output": row.result_json is not None,
            "progress_state": progress_state,
            "investigation_id": str(row.investigation_id) if row.investigation_id else None,
        }


async def _constraint_violations() -> list[dict]:
    factory = get_session_factory()
    async with factory() as session:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT project_id, COUNT(*) AS active_count
                    FROM business_idea_validation_runs
                    WHERE status IN ('queued', 'running')
                    GROUP BY project_id
                    HAVING COUNT(*) > 1
                    """
                )
            )
        ).all()
        return [{"project_id": str(r[0]), "active_count": int(r[1])} for r in rows]


def main() -> int:
    parser = argparse.ArgumentParser(description="RUNTIME-01G E2E DB assertions")
    parser.add_argument(
        "command",
        choices=["active-run-count", "investigation", "run-snapshot", "constraint-violations"],
    )
    parser.add_argument("--project-id")
    parser.add_argument("--run-id")
    args = parser.parse_args()

    if args.command == "active-run-count":
        if not args.project_id:
            parser.error("--project-id required")
        count = asyncio.run(_active_run_count(UUID(args.project_id)))
        print(json.dumps({"active_run_count": count}))
        return 0

    if args.command == "investigation":
        if not args.run_id:
            parser.error("--run-id required")
        payload = asyncio.run(_investigation_for_run(UUID(args.run_id)))
        print(json.dumps(payload or {}))
        return 0

    if args.command == "run-snapshot":
        if not args.run_id:
            parser.error("--run-id required")
        payload = asyncio.run(_run_snapshot(UUID(args.run_id)))
        print(json.dumps(payload or {}))
        return 0

    violations = asyncio.run(_constraint_violations())
    print(json.dumps({"violations": violations, "ok": len(violations) == 0}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
