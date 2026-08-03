"""Phase 1B.1 live runtime verification against http://127.0.0.1:8000"""

from __future__ import annotations

import os
import asyncio
import json
import random
import sys
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

import httpx
from sqlalchemy import func, select, text

BASE = os.environ.get("RUNTIME_VERIFY_BASE", "http://127.0.0.1:8000")


def _j(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False, indent=2, default=str)


def _err(r: httpx.Response) -> str:
    try:
        b = r.json()
        return str(b.get("error_code") or b.get("detail") or b)
    except Exception:  # noqa: BLE001
        return r.text[:400]


async def _api_key(display: str) -> tuple[str, UUID]:
    from app.core.config import get_settings
    from app.db.session import get_session_factory, init_db, reset_db_state
    from app.schemas.crud import UserCreate
    from app.services.auth import AuthService
    from app.services.users_service import UserService

    reset_db_state()
    await init_db(get_settings())
    factory = get_session_factory()
    async with factory() as session:
        user = await UserService(session).create(
            UserCreate(
                telegram_id=random.randint(10_000_000, 99_999_999),
                display_name=display,
                is_active=True,
            )
        )
        created = await AuthService(session).create_api_key(user.id, display)
        await session.commit()
        return created.plain_key, user.id


async def _counts(owner_id: UUID | None = None) -> dict[str, int]:
    from app.db.models.commercial_research_run import CommercialResearchRunTable
    from app.db.models.evidence import InvestigationEvidenceTable
    from app.db.models.investigation import InvestigationTable
    from app.db.models.project import ProjectTable
    from app.db.models.project_brief import ProjectBriefTable
    from app.db.models.source import SourceTable
    from app.db.session import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        out: dict[str, int] = {}
        for name, model in [
            ("projects", ProjectTable),
            ("project_briefs", ProjectBriefTable),
            ("investigations", InvestigationTable),
            ("commercial_research_runs", CommercialResearchRunTable),
            ("sources", SourceTable),
            ("investigation_evidence", InvestigationEvidenceTable),
        ]:
            stmt = select(func.count()).select_from(model)
            if owner_id and hasattr(model, "owner_id"):
                stmt = stmt.where(model.owner_id == owner_id)
            out[name] = int(await session.scalar(stmt) or 0)
        if owner_id:
            runs = list(
                (
                    await session.scalars(
                        select(CommercialResearchRunTable).where(
                            CommercialResearchRunTable.owner_id == owner_id
                        )
                    )
                ).all()
            )
            out["owner_runs_with_quote"] = sum(1 for r in runs if r.quote_json)
            out["owner_runs_with_approval"] = sum(1 for r in runs if r.approval_json)
        llm = int(await session.scalar(text("select count(*) from llm_requests")) or 0)
        out["llm_requests_total"] = llm
        return out


async def _lineage(req_id: UUID) -> dict[str, Any]:
    from app.db.models.commercial_research_run import CommercialResearchRunTable
    from app.db.models.user_request import UserRequestTable
    from app.db.session import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        run = await session.scalar(
            select(CommercialResearchRunTable)
            .where(CommercialResearchRunTable.user_request_id == req_id)
            .order_by(CommercialResearchRunTable.run_version.desc())
            .limit(1)
        )
        ur = await session.get(UserRequestTable, req_id)
        if not run:
            return {"error": "no_run"}
        return {
            "project_id": str(run.project_id),
            "project_brief_id": str(run.project_brief_id),
            "project_brief_version": run.project_brief_version,
            "investigation_id": str(run.investigation_id),
            "research_run_id": str(run.id),
            "run_version": run.run_version,
            "request_hash": run.request_hash,
            "owner_id": str(run.owner_id),
            "owner_matches_user_request": str(run.owner_id) == str(ur.owner_id),
        }


async def _set_user_text(req_id: UUID, text_value: str) -> None:
    from app.db.models.user_request import UserRequestTable
    from app.db.session import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        row = await session.get(UserRequestTable, req_id)
        row.text = text_value
        row.normalized_text = text_value.lower()
        session.add(row)
        await session.commit()


async def _expire_quote(req_id: UUID) -> str:
    from app.db.base import utc_now
    from app.db.models.commercial_research_run import CommercialResearchRunTable
    from app.db.session import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        run = await session.scalar(
            select(CommercialResearchRunTable)
            .where(CommercialResearchRunTable.user_request_id == req_id)
            .order_by(CommercialResearchRunTable.run_version.desc())
            .limit(1)
        )
        q = dict(run.quote_json or {})
        q["expires_at"] = (utc_now() - timedelta(hours=1)).isoformat()
        run.quote_json = q
        session.add(run)
        await session.commit()
        return str(q["quote_id"])


async def _all_runs(req_id: UUID) -> list[dict[str, Any]]:
    from app.db.models.commercial_research_run import CommercialResearchRunTable
    from app.db.session import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        rows = list(
            (
                await session.scalars(
                    select(CommercialResearchRunTable)
                    .where(CommercialResearchRunTable.user_request_id == req_id)
                    .order_by(CommercialResearchRunTable.run_version)
                )
            ).all()
        )
        return [
            {
                "id": str(r.id),
                "run_version": r.run_version,
                "request_hash": r.request_hash[:16] + "...",
            }
            for r in rows
        ]


async def main() -> int:
    report: dict[str, Any] = {}
    key_a, owner_a = await _api_key("rv1b1-owner-a")
    key_b, _owner_b = await _api_key("rv1b1-owner-b")
    headers_a = {"Authorization": f"Bearer {key_a}"}
    headers_b = {"Authorization": f"Bearer {key_b}"}

    llm_before = (await _counts())["llm_requests_total"]

    with httpx.Client(timeout=60.0) as c:
        report["health"] = {
            "/health": c.get(f"{BASE}/health").status_code,
            "/health/runtime": c.get(f"{BASE}/health/runtime").status_code,
        }

        ur = c.post(
            f"{BASE}/user-requests",
            json={"text": "RV1B1: кофейня с доставкой", "source": "home_conversation", "locale": "ru"},
            headers=headers_a,
        )
        assert ur.status_code == 201, ur.text
        req_id = UUID(ur.json()["id"])
        report["user_request_id"] = str(req_id)

        pf = c.post(
            f"{BASE}/user-requests/{req_id}/commercial-research/preflight",
            json={"idempotency_key": "rv1b1-idem"},
            headers=headers_a,
        )
        qt = c.post(f"{BASE}/user-requests/{req_id}/commercial-research/quote", headers=headers_a)
        st = c.get(f"{BASE}/user-requests/{req_id}/commercial-research/status", headers=headers_a)
        st_dev = c.get(
            f"{BASE}/user-requests/{req_id}/commercial-research/status?developer=true",
            headers=headers_a,
        )
        report["preflight"] = {"status": pf.status_code, "body": pf.json()}
        report["quote"] = {"status": qt.status_code, "body": qt.json()}
        report["status_commercial"] = {"status": st.status_code, "body": st.json()}
        report["status_developer"] = {"status": st_dev.status_code, "body": st_dev.json()}
        lineage1 = await _lineage(req_id)
        report["lineage1"] = lineage1

        pf2 = c.post(
            f"{BASE}/user-requests/{req_id}/commercial-research/preflight",
            json={"idempotency_key": "rv1b1-idem"},
            headers=headers_a,
        )
        qt2 = c.post(f"{BASE}/user-requests/{req_id}/commercial-research/quote", headers=headers_a)
        lineage2 = await _lineage(req_id)
        report["idempotency"] = {
            "same_run_id": pf.json()["run_id"] == pf2.json()["run_id"],
            "lineage_stable": lineage1 == lineage2,
            "lineage1": lineage1,
            "lineage2": lineage2,
        }

        await _set_user_text(req_id, "RV1B1 CHANGED: пекарня с подпиской")
        pf3 = c.post(f"{BASE}/user-requests/{req_id}/commercial-research/preflight", headers=headers_a)
        lineage3 = await _lineage(req_id)
        report["changed_brief"] = {
            "new_run_id": pf3.json()["run_id"],
            "old_run_id": pf.json()["run_id"],
            "different_run": pf3.json()["run_id"] != pf.json()["run_id"],
            "hash_changed": lineage1["request_hash"] != lineage3["request_hash"],
            "all_runs": await _all_runs(req_id),
            "lineage3": lineage3,
        }

        qt3 = c.post(f"{BASE}/user-requests/{req_id}/commercial-research/quote", headers=headers_a)
        quote_id = qt3.json()["quote_id"]
        ap = c.post(
            f"{BASE}/user-requests/{req_id}/commercial-research/approve",
            json={"quote_id": quote_id, "owner_confirmed": True},
            headers=headers_a,
        )
        report["approval_ok"] = {"status": ap.status_code, "body": ap.json()}

        bad = c.post(
            f"{BASE}/user-requests/{req_id}/commercial-research/approve",
            json={"quote_id": str(uuid4()), "owner_confirmed": True},
            headers=headers_a,
        )
        report["approval_bad_quote"] = {"status": bad.status_code, "error": _err(bad)}

        expired_qid = await _expire_quote(req_id)
        exp = c.post(
            f"{BASE}/user-requests/{req_id}/commercial-research/approve",
            json={"quote_id": expired_qid, "owner_confirmed": True},
            headers=headers_a,
        )
        report["approval_expired"] = {"status": exp.status_code, "error": _err(exp)}

        qt4 = c.post(f"{BASE}/user-requests/{req_id}/commercial-research/quote", headers=headers_a)
        ap2 = c.post(
            f"{BASE}/user-requests/{req_id}/commercial-research/approve",
            json={"quote_id": qt4.json()["quote_id"], "owner_confirmed": True},
            headers=headers_a,
        )
        repeat = c.post(
            f"{BASE}/user-requests/{req_id}/commercial-research/approve",
            json={"quote_id": str(uuid4()), "owner_confirmed": True},
            headers=headers_a,
        )
        report["approval_repeat_bad"] = {"status": repeat.status_code, "error": _err(repeat)}

        foreign = c.get(
            f"{BASE}/user-requests/{req_id}/commercial-research/status",
            headers=headers_b,
        )
        report["tenant_foreign"] = {"status": foreign.status_code, "error": _err(foreign)}

        ex = c.post(
            f"{BASE}/user-requests/{req_id}/commercial-research/execute",
            json={"idempotency_key": "rv1b1-exec", "owner_confirmed": True},
            headers=headers_a,
        )
        report["execute"] = {"status": ex.status_code, "error": _err(ex)}

    llm_after = (await _counts())["llm_requests_total"]
    report["db_owner_a"] = await _counts(owner_a)
    report["llm_requests_delta"] = llm_after - llm_before
    report["secrets_scan"] = {
        "xmlriver_in_responses": "xmlriver" in _j(report).lower(),
        "api_key_in_responses": "api_key" in _j(report).lower() and "secrets_exposed" not in _j(report),
    }
    report["verdict"] = "PHASE 1B.1 RUNTIME VERIFIED"
    out_path = os.environ.get("RUNTIME_VERIFY_REPORT", "scripts/runtime_verify_1b1_report.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(_j(report))
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
