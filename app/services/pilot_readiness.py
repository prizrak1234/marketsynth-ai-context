"""CPH.5 — readiness aggregation (no provider/LLM calls)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.core.config import Settings, get_settings
from app.core.redis import check_redis_connection
from app.db.session import check_database_connection, get_engine
from app.domain.alembic_revision_guard import DatabaseRevisionState
from app.domain.pilot_config_validation import validate_pilot_configuration
from app.services.alembic_revision_startup import diagnose_database_revision


@dataclass
class ComponentStatus:
    name: str
    status: str  # ok | error | warn | skipped
    detail: str = ""


@dataclass
class ReadinessReport:
    ready: bool
    status: str
    components: list[ComponentStatus] = field(default_factory=list)
    expected_revision: str | None = None
    actual_revisions: list[str] = field(default_factory=list)
    database_name: str | None = None
    backup_age_hours: float | None = None
    duration_ms: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "status": self.status,
            "expected_revision": self.expected_revision,
            "actual_revisions": self.actual_revisions,
            "database_name": self.database_name,
            "backup_age_hours": self.backup_age_hours,
            "duration_ms": self.duration_ms,
            "components": [
                {"name": c.name, "status": c.status, "detail": c.detail} for c in self.components
            ],
        }


def _safe_db_name(database_url: str) -> str | None:
    try:
        u = urlparse(database_url.replace("postgresql+asyncpg://", "postgresql://", 1))
        return (u.path or "").lstrip("/") or None
    except Exception:  # noqa: BLE001
        return None


def _backup_age_hours(settings: Settings) -> tuple[float | None, ComponentStatus]:
    root = Path.home() / "botfazer_backups" / "cph4"
    policy_hours = float(getattr(settings, "pilot_backup_max_age_hours", 48) or 48)
    if not root.is_dir():
        return None, ComponentStatus("backup_freshness", "warn", "backup_dir_missing")
    dumps = sorted(root.glob("cph4_*.dump"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not dumps:
        return None, ComponentStatus("backup_freshness", "warn", "no_backup_files")
    age_h = (time.time() - dumps[0].stat().st_mtime) / 3600.0
    if age_h > policy_hours:
        return age_h, ComponentStatus(
            "backup_freshness",
            "warn",
            f"backup_age_hours={age_h:.1f} exceeds policy={policy_hours}",
        )
    return age_h, ComponentStatus("backup_freshness", "ok", f"age_hours={age_h:.1f}")


async def gather_readiness_report(settings: Settings | None = None) -> ReadinessReport:
    settings = settings or get_settings()
    t0 = time.perf_counter()
    components: list[ComponentStatus] = []

    cfg = validate_pilot_configuration(settings)
    if cfg.errors:
        components.append(
            ComponentStatus("configuration", "error", ",".join(i.code for i in cfg.errors))
        )
    elif cfg.warnings:
        components.append(
            ComponentStatus("configuration", "warn", ",".join(i.code for i in cfg.warnings))
        )
    else:
        components.append(ComponentStatus("configuration", "ok"))

    db_ok = await check_database_connection()
    components.append(
        ComponentStatus("database", "ok" if db_ok else "error", "" if db_ok else "unreachable")
    )

    expected: str | None = None
    actual: list[str] = []
    if db_ok:
        try:
            diag = await diagnose_database_revision(get_engine(), settings)
            actual = list(diag.database_revisions)
            expected = diag.code_heads[0] if len(diag.code_heads) == 1 else None
            if diag.state == DatabaseRevisionState.CURRENT:
                components.append(ComponentStatus("alembic_revision", "ok", diag.state.value))
            elif diag.state in {
                DatabaseRevisionState.EMPTY,
                DatabaseRevisionState.NO_VERSION_TABLE,
            } and settings.app_env in {"development", "test"}:
                # SQLite create_all tests have no alembic_version — do not block readiness.
                components.append(
                    ComponentStatus("alembic_revision", "warn", diag.state.value)
                )
            elif diag.state == DatabaseRevisionState.BEHIND:
                severity = (
                    "error"
                    if settings.app_env in {"pilot", "staging", "production"}
                    else "warn"
                )
                components.append(
                    ComponentStatus(
                        "alembic_revision",
                        severity,
                        "behind_required_migrate_offline",
                    )
                )
            else:
                severity = (
                    "error"
                    if settings.app_env in {"pilot", "staging", "production"}
                    else "warn"
                )
                components.append(
                    ComponentStatus("alembic_revision", severity, diag.state.value)
                )
        except Exception as exc:  # noqa: BLE001
            severity = (
                "error"
                if settings.app_env in {"pilot", "staging", "production"}
                else "warn"
            )
            components.append(ComponentStatus("alembic_revision", severity, type(exc).__name__))

    redis_ok = await check_redis_connection()
    components.append(
        ComponentStatus("redis", "ok" if redis_ok else "warn", "" if redis_ok else "unreachable")
    )

    if settings.browser_session_cookie_name and settings.browser_session_ttl_hours > 0:
        components.append(ComponentStatus("browser_sessions", "ok"))
    else:
        components.append(ComponentStatus("browser_sessions", "error", "misconfigured"))

    if settings.app_env in {"pilot", "production"}:
        bad = []
        if settings.tools_provider_enabled:
            bad.append("tools_provider")
        if settings.publication_worker_enabled:
            bad.append("publication_worker")
        if settings.graph_handoff_execute_child:
            bad.append("handoff_execute_child")
        if bad:
            components.append(ComponentStatus("execution_firewall", "error", ",".join(bad)))
        else:
            components.append(ComponentStatus("execution_firewall", "ok", "disabled"))
    else:
        components.append(ComponentStatus("execution_firewall", "ok", "not_enforced"))

    age, backup_comp = _backup_age_hours(settings)
    components.append(backup_comp)

    if db_ok:
        try:
            from app.services.analysis_context_subsystem_readiness import (
                inspect_analysis_context_subsystem,
            )

            ac_status = await inspect_analysis_context_subsystem(get_engine())
            severity = "error" if not ac_status.ready else "ok"
            if settings.app_env in {"development", "test"} and not ac_status.ready:
                severity = "warn"
            components.append(
                ComponentStatus(
                    "analysis_context_subsystem",
                    severity,
                    ac_status.detail,
                )
            )
        except Exception as exc:  # noqa: BLE001
            components.append(
                ComponentStatus(
                    "analysis_context_subsystem",
                    "warn" if settings.app_env in {"development", "test"} else "error",
                    type(exc).__name__,
                )
            )

    blocking = [c for c in components if c.status == "error"]
    ready = len(blocking) == 0 and db_ok
    return ReadinessReport(
        ready=ready,
        status="ready" if ready else "not_ready",
        components=components,
        expected_revision=expected,
        actual_revisions=actual,
        database_name=_safe_db_name(settings.database_url),
        backup_age_hours=age,
        duration_ms=round((time.perf_counter() - t0) * 1000, 2),
    )
