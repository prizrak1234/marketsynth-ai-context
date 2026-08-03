#!/usr/bin/env python3
"""Read-only owner smoke diagnostic queries — PRODUCT-01.3B-OWNER-SMOKE-DIAG-01."""

from __future__ import annotations

import asyncio
import json
import sys
from uuid import UUID

from sqlalchemy import text

from app.db.session import get_session_factory


async def diagnose(project_id: str | None = None, run_id: str | None = None) -> None:
    factory = get_session_factory()
    async with factory() as session:
        if run_id:
            run_filter = "r.id = :run_id"
            params: dict = {"run_id": UUID(run_id)}
        elif project_id:
            run_filter = "r.project_id = :project_id"
            params = {"project_id": UUID(project_id)}
        else:
            run_filter = """
                r.created_at > NOW() - INTERVAL '24 hours'
                AND p.name NOT LIKE 'E2E-%'
                AND p.name NOT LIKE 'E2E_%'
            """
            params = {}

        runs = (
            await session.execute(
                text(
                    f"""
                    SELECT r.id, r.project_id, p.name AS project_name, r.user_request_id,
                           r.investigation_id, r.owner_id, r.status, r.error_code,
                           r.safe_error_message, r.created_at, r.updated_at, r.finished_at,
                           r.research_mode, r.progress_json, r.result_json, r.observability_json
                    FROM business_idea_validation_runs r
                    JOIN projects p ON p.id = r.project_id
                    WHERE {run_filter if run_id or project_id else run_filter}
                    ORDER BY r.created_at DESC
                    LIMIT 5
                    """
                ),
                params,
            )
        ).mappings().all()

        active_global = (
            await session.execute(
                text(
                    """
                    SELECT COUNT(*) FROM business_idea_validation_runs
                    WHERE status IN ('queued', 'running')
                    """
                )
            )
        ).scalar()

        owner_projects = (
            await session.execute(
                text(
                    """
                    SELECT id, name, created_at, updated_at
                    FROM projects
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                      AND name NOT LIKE 'E2E-%'
                      AND name NOT LIKE 'E2E_%'
                    ORDER BY created_at DESC
                    LIMIT 20
                    """
                )
            )
        ).mappings().all()

        out_runs = []
        for run in runs:
            rid = run["id"]
            ledger = (
                await session.execute(
                    text(
                        """
                        SELECT provider, outcome_code, COUNT(*) AS cnt,
                               MIN(created_at) AS first_at, MAX(created_at) AS last_at
                        FROM biv_fetch_ledger_entries
                        WHERE run_id = :rid
                        GROUP BY provider, outcome_code
                        ORDER BY provider, outcome_code
                        """
                    ),
                    {"rid": rid},
                )
            ).mappings().all()
            first_evidence = (
                await session.execute(
                    text(
                        """
                        SELECT MIN(created_at) FROM biv_fetch_ledger_entries
                        WHERE run_id = :rid AND outcome_code = 'success'
                        """
                    ),
                    {"rid": rid},
                )
            ).scalar()
            inv = None
            if run["investigation_id"]:
                inv = (
                    await session.execute(
                        text(
                            """
                            SELECT id, status, current_stage, readiness_status,
                                   created_at, updated_at, superseded_at
                            FROM investigations WHERE id = :iid
                            """
                        ),
                        {"iid": run["investigation_id"]},
                    )
                ).mappings().first()
            rj = run["result_json"] if isinstance(run["result_json"], dict) else {}
            pj = run["progress_json"] if isinstance(run["progress_json"], dict) else {}
            oj = run["observability_json"] if isinstance(run["observability_json"], dict) else {}
            out_runs.append(
                {
                    "run_id": str(rid),
                    "project_id": str(run["project_id"]),
                    "project_name": run["project_name"],
                    "user_request_id": str(run["user_request_id"]),
                    "investigation_id": str(run["investigation_id"]) if run["investigation_id"] else None,
                    "status": run["status"],
                    "error_code": run["error_code"],
                    "safe_error_message": run["safe_error_message"],
                    "created_at": str(run["created_at"]),
                    "updated_at": str(run["updated_at"]),
                    "finished_at": str(run["finished_at"]) if run["finished_at"] else None,
                    "research_started_at": pj.get("started_at") or str(run["created_at"]),
                    "first_evidence_at": str(first_evidence) if first_evidence else None,
                    "terminal_state_reached_at": str(run["finished_at"]) if run["finished_at"] else None,
                    "progress": pj,
                    "result_kind": rj.get("result_kind"),
                    "research_terminal_state": rj.get("research_terminal_state"),
                    "evidence_count": len(rj.get("evidence_items") or []),
                    "has_customer_report": bool(rj.get("customer_report")),
                    "has_verdict": bool(rj.get("verdict")),
                    "citations_count": len(rj.get("citations") or []),
                    "observability": oj,
                    "fetch_ledger": [dict(x) for x in ledger],
                    "investigation": dict(inv) if inv else None,
                }
            )

    print(
        json.dumps(
            {
                "active_runs_global": int(active_global or 0),
                "owner_projects_24h": [dict(p) for p in owner_projects],
                "runs": out_runs,
            },
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )


if __name__ == "__main__":
    pid = sys.argv[1] if len(sys.argv) > 1 else None
    rid = sys.argv[2] if len(sys.argv) > 2 else None
    asyncio.run(diagnose(pid, rid))
