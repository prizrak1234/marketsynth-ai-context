"""Resolve classic vs langgraph execution engine (Phase 3.13)."""

from __future__ import annotations

from typing import Literal, Protocol

from app.core.config import Settings
from app.core.logging import get_logger

ExecutionEngine = Literal["classic", "langgraph"]

log = get_logger(__name__)


class ProjectEngineConfig(Protocol):
    config: dict


def normalize_execution_engine(value: object | None) -> ExecutionEngine | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in ("classic", "langgraph"):
        return normalized
    return None


def _apply_langgraph_gate(engine: ExecutionEngine, settings: Settings) -> ExecutionEngine:
    if engine == "langgraph" and not settings.agent_execution_langgraph_enabled:
        return "classic"
    return engine


def resolve_execution_engine(
    settings: Settings,
    *,
    project: ProjectEngineConfig | None = None,
    request_override: str | None = None,
) -> ExecutionEngine:
    """Priority: force classic > request override > project.config > settings > classic."""
    if settings.agent_execution_force_classic:
        return "classic"

    if request_override is not None:
        override = normalize_execution_engine(request_override)
        if override is None:
            log.warning(
                "execution_engine_unknown_override",
                request_override=str(request_override),
            )
        elif settings.agent_execution_engine_request_override_enabled:
            return _apply_langgraph_gate(override, settings)

    if project is not None:
        project_config = getattr(project, "config", None)
        if isinstance(project_config, dict):
            project_engine = normalize_execution_engine(
                project_config.get("execution_engine"),
            )
            if project_engine is not None:
                return _apply_langgraph_gate(project_engine, settings)
            if project_config.get("execution_engine") is not None:
                log.warning(
                    "execution_engine_unknown_project_config",
                    project_execution_engine=str(project_config.get("execution_engine")),
                )

    settings_engine = normalize_execution_engine(settings.agent_execution_engine)
    if settings_engine is None:
        log.warning(
            "execution_engine_unknown_settings",
            agent_execution_engine=str(settings.agent_execution_engine),
        )
        return "classic"
    return _apply_langgraph_gate(settings_engine, settings)
