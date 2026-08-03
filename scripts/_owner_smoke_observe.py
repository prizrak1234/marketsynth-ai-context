#!/usr/bin/env python3
"""Observe owner real research smoke run — read-only DB evidence."""

from __future__ import annotations

import asyncio
import json
import sys
from uuid import UUID

from sqlalchemy import text

from app.db.session import get_session_factory


async def observe(user_request_id: str | None = None, run_id: str | None = None) -> None:
    factory = get_session_factory()
    async with factory() as session:
        if run_id:
            where = "r.id = :rid"
            params = {"rid": run_id}
        elif user_request_id:
            where = "r.user_request_id = :ur"
            params = {"ur": user_request_id}
        else:
            row = (
                await session.execute(
                    text(
                        """
                        SELECT id FROM business_idea_validation_runs
                        WHERE created_at > NOW() - INTERVAL '2 hours'
                        ORDER BY created_at DESC LIMIT 1
                        """
                    )
                )
            ).first()
            if not row:
                print(json.dumps({"error": "no_recent_run"}))
                return
            where = "r.id = :rid"
            params = {"rid": row[0]}

        run = (
            await session.execute(
                text(
                    f"""
                    SELECT r.*, p.name AS project_name
                    FROM business_idea_validation_runs r
                    JOIN projects p ON p.id = r.project_id
                    WHERE {where}
                    """
                ),
                params,
            )
        ).mappings().first()

        if not run:
            print(json.dumps({"error": "run_not_found"}))
            return

        rid = run["id"]
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
                {"rid": rid},
            )
        ).mappings().all()

        ledger_total = (
            await session.execute(
                text("SELECT COUNT(*) FROM biv_fetch_ledger_entries WHERE run_id = :rid"),
                {"rid": rid},
            )
        ).scalar()

        post_runs_count = None  # filled from caller context

        rj = run["result_json"] if isinstance(run["result_json"], dict) else {}
        pj = run["progress_json"] if isinstance(run["progress_json"], dict) else {}

        out = {
            "run_id": str(run["id"]),
            "project_id": str(run["project_id"]),
            "project_name": run["project_name"],
            "user_request_id": str(run["user_request_id"]),
            "owner_id_masked": str(run["owner_id"])[:8] + "****",
            "created_at": str(run["created_at"]),
            "updated_at": str(run["updated_at"]),
            "finished_at": str(run["finished_at"]) if run["finished_at"] else None,
            "status": run["status"],
            "error_code": run["error_code"],
            "research_mode": run["research_mode"],
            "result_kind": rj.get("result_kind"),
            "research_terminal_state": rj.get("research_terminal_state"),
            "progress_stage": pj.get("stage"),
            "progress_pct": pj.get("percent"),
            "fetch_ledger_total": ledger_total,
            "fetch_by_provider_outcome": {
                f"{x['provider']}:{x['outcome_code']}": x["cnt"] for x in ledger
            },
            "evidence_count": len(rj.get("evidence_items") or []) if rj else 0,
            "has_customer_report": bool(rj.get("customer_report")) if rj else False,
            "verdict": rj.get("verdict") if rj else None,
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    ur = sys.argv[1] if len(sys.argv) > 1 else None
    rid = sys.argv[2] if len(sys.argv) > 2 else None
    asyncio.run(observe(ur, rid))
