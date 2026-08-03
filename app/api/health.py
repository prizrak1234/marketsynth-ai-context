"""Health, readiness, and version endpoints (CPH.5 semantics)."""

from __future__ import annotations

import importlib.util
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.config import Settings, get_settings
from app.schemas.operational_metrics import OperationsHealthResponse
from app.services.health_checks import gather_health_report
from app.services.operations_health import gather_operations_health
from app.services.pilot_readiness import gather_readiness_report

router = APIRouter(tags=["system"])

_PROCESS_STARTED_AT = datetime.now(UTC).isoformat()
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _openapi_has_analysis_context_paths(openapi_schema: dict) -> bool:
    paths = openapi_schema.get("paths", {})
    required = {
        "/projects/{project_id}/analysis-contexts",
        "/projects/{project_id}/analysis-contexts/current",
    }
    return required.issubset(paths.keys())


def _git_commit() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=_REPO_ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
        )
        return out.strip()
    except Exception:
        return "unknown"


def _database_name(database_url: str) -> str:
    try:
        return (urlparse(database_url).path or "/").lstrip("/") or "unknown"
    except Exception:
        return "unknown"


@router.get("/health/live")
async def health_live() -> dict[str, str]:
    """Liveness: process is up. No DB / Redis / provider fan-out."""
    return {"status": "alive", "service": "marketsynth-api"}


@router.get("/health/ready")
async def health_ready(response: Response) -> dict:
    """Readiness: safe to receive pilot traffic."""
    report = await gather_readiness_report()
    if not report.ready:
        response.status_code = 503
    return report.as_dict()


@router.get("/health")
async def health(response: Response) -> dict[str, str]:
    """Legacy combined probe (compat). Prefer /health/live and /health/ready."""
    report = await gather_health_report()
    if not report.is_healthy:
        response.status_code = 503
    return {
        "status": report.status,
        "app": report.app,
        "database": report.database,
        "redis": report.redis,
    }


@router.get("/health/operations", response_model=OperationsHealthResponse)
async def health_operations(
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> OperationsHealthResponse:
    report = await gather_operations_health(session)
    if report.status != "ok":
        response.status_code = 503
    return report


@router.get("/version")
async def version(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
    }


@router.get("/health/runtime")
async def health_runtime(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Owner diagnostics: prove which backend build/process is live (no secrets)."""
    commit = _git_commit()
    alembic_revision = "unknown"
    try:
        result = await session.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
        row = result.first()
        if row and row[0]:
            alembic_revision = str(row[0])
    except Exception:
        alembic_revision = "unavailable"

    litellm_installed = importlib.util.find_spec("litellm") is not None
    from app.media_generation.video_aggregator_status import content_factory_integrations_status
    from app.db.session import get_engine
    from app.services.analysis_context_subsystem_readiness import inspect_analysis_context_subsystem

    analysis_context = (
        await inspect_analysis_context_subsystem(get_engine())
    ).as_dict()
    openapi_has_analysis_context = False
    try:
        from app.main import app as fastapi_app

        openapi_has_analysis_context = bool(
            _openapi_has_analysis_context_paths(fastapi_app.openapi())
        )
    except Exception:  # noqa: BLE001
        openapi_has_analysis_context = False
    analysis_context["openapi_paths_present"] = openapi_has_analysis_context

    env_file = _REPO_ROOT / ".env"
    return {
        "backend_build_id": f"be-{commit[:12]}-{_PROCESS_STARTED_AT[:19]}",
        "git_commit": commit,
        "process_started_at": _PROCESS_STARTED_AT,
        "database_name": _database_name(settings.database_url),
        "alembic_revision": alembic_revision,
        "expected_alembic_head": "20260724_0060",
        "analysis_context_subsystem": analysis_context,
        "content_draft_execution_enabled": bool(settings.content_draft_execution_enabled),
        "content_draft_llm_provider": settings.content_draft_llm_provider,
        "content_draft_llm_model": settings.content_draft_llm_model,
        "litellm_installed": litellm_installed,
        "repository_path": str(_REPO_ROOT),
        "env_file_path": str(env_file.resolve()),
        "env_file_exists": env_file.is_file(),
        "cwd": str(Path.cwd().resolve()),
        "content_factory_integrations": content_factory_integrations_status(settings),
    }


@router.get("/health/research-providers")
async def health_research_providers(
    live: bool = True,
    settings: Settings = Depends(get_settings),
) -> dict:
    """Read-only research provider contour — no secrets, optional live probes."""
    from app.research_source_collection.readiness import probe_providers

    payload = await probe_providers(settings, live=live)
    return {
        "status": payload.get("status"),
        "mock_providers": payload.get("mock_providers"),
        "enabled": payload.get("enabled"),
        "probed": payload.get("probed", False),
        "probe_skipped": payload.get("probe_skipped"),
        "coverage_disclosure_ru": payload.get("coverage_disclosure_ru"),
        "providers": payload.get("providers"),
        "contour": {
            "search_provider": "xmlriver",
            "fetch_provider": "firecrawl",
            "llm_provider": "none_in_biv_pipeline",
            "timeout_seconds": settings.mcp_tool_call_timeout_seconds,
            "max_retries": settings.mcp_max_retries,
            "max_search_calls": settings.biv_research_max_search_calls,
            "max_fetch_calls": settings.biv_research_max_fetch_calls,
            "max_latency_seconds": settings.biv_research_max_latency_seconds,
            "max_estimated_cost_usd": settings.biv_research_max_estimated_cost_usd,
        },
        "last_checked_at": payload.get("last_checked_at"),
    }
