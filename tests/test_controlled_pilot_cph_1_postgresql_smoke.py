"""Optional PostgreSQL smoke — set CPH1_POSTGRES_URL to disposable migrated DB.

Does not replace SQLite suite. Never targets the local `botfazer` data DB name.
Avoids TestClient+asyncio.run create_all (asyncpg loop binding); uses one asyncio.run.
"""

from __future__ import annotations

import asyncio
import os
import random
from urllib.parse import urlparse

import pytest

COMMERCIAL_TABLES = [
    "projects",
    "project_briefs",
    "investigations",
    "sources",
    "investigation_source_links",
    "investigation_evidence",
    "evidence_source_links",
    "business_verdicts",
    "business_verdict_evidence_snapshots",
    "business_verdict_evidence_links",
    "marketing_strategies",
    "implementation_plans",
    "implementation_marketing_plan_handoffs",
    "marketing_plans",
]


def _pg_url() -> str | None:
    return os.environ.get("CPH1_POSTGRES_URL")


def _assert_disposable(url: str) -> None:
    name = (urlparse(url.replace("+asyncpg", "").replace("+psycopg", "")).path or "").lstrip(
        "/"
    )
    if name in {"botfazer", "postgres", "template0", "template1"}:
        raise AssertionError(f"refusing non-disposable database name={name}")


def _to_dsn(url: str) -> str:
    for p in (
        "postgresql+asyncpg://",
        "postgresql+psycopg://",
        "postgresql+psycopg2://",
    ):
        if url.startswith(p):
            return "postgresql://" + url[len(p) :]
    return url


@pytest.fixture
def pg_url(monkeypatch: pytest.MonkeyPatch) -> str:
    url = _pg_url()
    if not url:
        pytest.skip("CPH1_POSTGRES_URL not set")
    _assert_disposable(url)
    monkeypatch.setenv("DATABASE_URL", url)
    from app.core.config import get_settings

    get_settings.cache_clear()
    return url


@pytest.mark.skipif(not _pg_url(), reason="CPH1_POSTGRES_URL not set")
def test_cph1_postgres_revision_current(pg_url: str) -> None:
    import asyncpg

    from app.domain.alembic_revision_guard import (
        DatabaseRevisionState,
        classify_revision,
    )

    async def _run() -> None:
        conn = await asyncpg.connect(_to_dsn(pg_url))
        try:
            revs = [
                r["version_num"]
                for r in await conn.fetch("select version_num from alembic_version")
            ]
        finally:
            await conn.close()
        diag = classify_revision(database_revisions=revs)
        assert diag.state == DatabaseRevisionState.CURRENT
        assert "20260614_0036" in diag.database_revisions

    asyncio.run(_run())


@pytest.mark.skipif(not _pg_url(), reason="CPH1_POSTGRES_URL not set")
def test_cph1_postgres_commercial_tables_present(pg_url: str) -> None:
    import asyncpg

    async def _run() -> None:
        conn = await asyncpg.connect(_to_dsn(pg_url))
        try:
            missing = []
            for t in COMMERCIAL_TABLES:
                ok = await conn.fetchval(
                    "select exists(select 1 from information_schema.tables "
                    "where table_schema='public' and table_name=$1)",
                    t,
                )
                if not ok:
                    missing.append(t)
            assert missing == [], missing
            fks = await conn.fetch(
                "select count(*) as c from information_schema.table_constraints "
                "where constraint_type='FOREIGN KEY' and table_schema='public' "
                "and table_name = any($1::text[])",
                COMMERCIAL_TABLES,
            )
            assert fks[0]["c"] >= 5
        finally:
            await conn.close()

    asyncio.run(_run())


@pytest.mark.skipif(not _pg_url(), reason="CPH1_POSTGRES_URL not set")
def test_cph1_postgres_orm_project_brief_smoke(pg_url: str) -> None:
    """Migrated PG schema accepts ORM Project + ProjectBrief create (no create_all)."""

    async def _run() -> None:
        from app.core.config import get_settings
        from app.db.session import close_db, get_session_factory, init_db, reset_db_state
        from app.schemas.contracts import ProjectBriefCreateRequest
        from app.schemas.crud import ProjectCreate, UserCreate
        from app.services.auth import AuthService
        from app.services.project_brief_service import ProjectBriefService
        from app.services.projects_service import ProjectService
        from app.services.users_service import UserService

        get_settings.cache_clear()
        reset_db_state()
        await init_db(get_settings())
        factory = get_session_factory()
        try:
            async with factory() as session:
                user = await UserService(session).create(
                    UserCreate(
                        telegram_id=random.randint(1_000_000, 9_999_999),
                        display_name="CPH1 PG",
                        is_active=True,
                    ),
                )
                await AuthService(session).create_api_key(user.id, "cph1-pg-key")
                project = await ProjectService(session).create(
                    ProjectCreate(name="CPH1 PG Project", owner_id=user.id),
                )
                body = {
                    "language": "ru",
                    "project_basics": {
                        "project_name": "CPH1",
                        "idea_description": "x",
                        "business_type": "local_business",
                        "project_stage": "preparing_launch",
                        "geography": "Moscow",
                        "preferred_language": "ru",
                    },
                    "product": {
                        "product_or_service": "S",
                        "customer_problem": "P",
                        "value_proposition": "V",
                        "price": {"mode": "unknown"},
                        "delivery_model": "clinic",
                        "differentiators": "d",
                        "limitations": "l",
                    },
                    "market": {
                        "target_market": "A",
                        "geography": "Moscow",
                        "known_competitors": "",
                        "competitor_urls": "",
                        "market_assumptions": "a",
                        "demand_evidence": "d",
                        "seasonality": "",
                        "restrictions": "",
                    },
                    "audience": {
                        "business_model": "b2c",
                        "segments": [],
                        "decision_maker": "D",
                        "buyer_user_distinction": "same",
                        "geography": "Moscow",
                        "pains": "p",
                        "objections": "o",
                        "current_research": "r",
                    },
                    "economics": {
                        "launch_budget": {"mode": "unknown"},
                        "monthly_marketing_budget": {"mode": "unknown"},
                        "target_revenue": {"mode": "unknown"},
                        "payback_period": "",
                        "average_order_value": {"mode": "unknown"},
                        "gross_margin": "",
                        "team_size": "",
                        "internal_resources": "",
                        "launch_deadline": "",
                        "critical_constraints": "",
                    },
                    "materials_summary": {
                        "website_url": "",
                        "social_profiles": "",
                        "items": [],
                    },
                    "assumptions": ["a"],
                    "missing_data": [],
                    "readiness_status": "conditionally_ready",
                    "readiness_reasons": ["pending"],
                }
                payload = ProjectBriefCreateRequest.model_validate(body)
                brief = await ProjectBriefService(session).create_draft(
                    user.id, project.id, payload
                )
                assert brief is not None
                assert brief.version == 1
                assert getattr(brief.status, "value", str(brief.status)) == "draft"
        finally:
            await close_db()
            get_settings.cache_clear()
            reset_db_state()

    asyncio.run(_run())
