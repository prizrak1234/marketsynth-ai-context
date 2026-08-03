"""Read-only Alembic revision check for startup (never migrates/stamps)."""

from __future__ import annotations

from dataclasses import asdict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings
from app.core.logging import get_logger
from app.domain.alembic_revision_guard import (
    DatabaseRevisionState,
    RevisionDiagnostic,
    classify_revision,
    list_code_revisions,
)

log = get_logger(__name__)


async def fetch_database_revisions(engine: AsyncEngine) -> list[str]:
    """Read alembic_version rows. Dialect-safe: missing table → empty list."""
    async with engine.connect() as conn:
        try:
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            return [row[0] for row in result.fetchall()]
        except Exception:  # noqa: BLE001 — SQLite/PG without version table
            return []


async def diagnose_database_revision(
    engine: AsyncEngine,
    settings: Settings | None = None,
) -> RevisionDiagnostic:
    code_map = list_code_revisions()
    downs = {d for d in code_map.values() if d}
    heads = sorted(r for r in code_map if r not in downs)
    db_revs = await fetch_database_revisions(engine)
    return classify_revision(
        database_revisions=db_revs,
        code_heads=heads,
        code_revisions=code_map,
    )


def should_fail_fast(diag: RevisionDiagnostic, settings: Settings) -> bool:
    """Pilot/production: fail on unknown/ahead/behind/multiple. Dev: warn unless fail-fast."""
    fail_fast_flag = bool(getattr(settings, "alembic_revision_fail_fast", False))
    pilot_like = settings.app_env in {"pilot", "staging", "production"}
    if settings.app_env in {"development", "test"} and not fail_fast_flag:
        return False
    # Pilot-like always treats BEHIND as fatal when fail-fast is on (CPH.5).
    fatal = {
        DatabaseRevisionState.MISSING_FROM_TREE,
        DatabaseRevisionState.MULTIPLE_HEADS,
        DatabaseRevisionState.UNKNOWN,
        DatabaseRevisionState.AHEAD,
    }
    if fail_fast_flag or pilot_like:
        fatal = fatal | {DatabaseRevisionState.BEHIND, DatabaseRevisionState.EMPTY}
    return diag.state in fatal


async def log_revision_diagnostic(engine: AsyncEngine, settings: Settings) -> RevisionDiagnostic:
    diag = await diagnose_database_revision(engine, settings)
    payload = {
        "state": diag.state.value,
        "code_heads": list(diag.code_heads),
        "database_revisions": list(diag.database_revisions),
        "detail": diag.detail,
        "auto_stamp_allowed": False,
        "auto_migrate_allowed": False,
    }
    if diag.state == DatabaseRevisionState.CURRENT:
        log.info("alembic_revision_ok", **payload)
    elif diag.state == DatabaseRevisionState.BEHIND:
        log.warning("alembic_revision_behind", **payload)
    else:
        log.error("alembic_revision_problem", **payload)
    if should_fail_fast(diag, settings):
        raise RuntimeError(
            f"{diag.state.value}: {diag.detail}. "
            "Refusing startup (no auto-stamp / no auto-migrate)."
        )
    return diag
