#!/usr/bin/env python3
"""Read-only diagnosis for owner smoke run cd56d6ff."""

from __future__ import annotations

import asyncio
import json

from uuid import UUID

from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.services.business_idea_validation_service import BusinessIdeaValidationService

RUN_ID = UUID("cd56d6ff-1eaa-47ba-ad07-7a146911028d")
PROJECT_ID = UUID("4ecfb41a-b9ef-4b60-aa04-dfd7b6e01ae8")
USER_REQUEST_ID = UUID("31557e61-8f5a-4f91-937c-a784bc35f99d")
SECOND_RUN_ID = UUID("d1de387f-1f48-4e3d-aaa4-bbbde339a455")


async def main() -> None:
    factory = get_session_factory()
    settings = get_settings()
    async with factory() as session:
        run = (
            await session.execute(
                text(
                    """
                    SELECT id, project_id, user_request_id, investigation_id, status,
                           error_code, safe_error_message, created_at, updated_at, finished_at,
                           result_json, progress_json, observability_json, business_verdict_id,
                           owner_id
                    FROM business_idea_validation_runs WHERE id = :rid
                    """
                ),
                {"rid": RUN_ID},
            )
        ).mappings().first()

        second = (
            await session.execute(
                text(
                    """
                    SELECT id, status, error_code, created_at, finished_at, progress_json
                    FROM business_idea_validation_runs WHERE id = :rid
                    """
                ),
                {"rid": SECOND_RUN_ID},
            )
        ).mappings().first()

        inv = (
            await session.execute(
                text(
                    """
                    SELECT id, status, current_stage, readiness_status, created_at, updated_at
                    FROM investigations WHERE id = :iid
                    """
                ),
                {"iid": run["investigation_id"]},
            )
        ).mappings().first()

        project_runs = (
            await session.execute(
                text(
                    """
                    SELECT id, status, error_code, created_at, finished_at, user_request_id
                    FROM business_idea_validation_runs
                    WHERE project_id = :pid ORDER BY created_at DESC LIMIT 6
                    """
                ),
                {"pid": PROJECT_ID},
            )
        ).mappings().all()

        active = (
            await session.execute(
                text(
                    """
                    SELECT id, status, project_id, user_request_id, created_at
                    FROM business_idea_validation_runs
                    WHERE status IN ('queued', 'running', 'pending')
                    """
                )
            )
        ).mappings().all()

        svc = BusinessIdeaValidationService(session, settings)
        owner_id = run["owner_id"]
        api_run = await svc.get_run_for_owner(owner_id, USER_REQUEST_ID, RUN_ID)
        api_progress = await svc.get_progress_for_run(owner_id, USER_REQUEST_ID, RUN_ID)
        api_latest = await svc.get_project_hydration(owner_id, PROJECT_ID)

    def ser(obj):
        if obj is None:
            return None
        if hasattr(obj, "model_dump"):
            return obj.model_dump(mode="json")
        if isinstance(obj, dict):
            return {k: ser(v) for k, v in obj.items()}
        return str(obj)

    print(
        json.dumps(
            {
                "run": ser(dict(run)),
                "second_run": ser(dict(second)) if second else None,
                "investigation": ser(dict(inv)),
                "project_runs": [ser(dict(r)) for r in project_runs],
                "active_runs": [ser(dict(r)) for r in active],
                "api_get_run": ser(api_run),
                "api_get_progress": ser(api_progress),
                "api_project_latest": ser(api_latest),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
