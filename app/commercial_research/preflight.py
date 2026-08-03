"""Preflight checks — no paid provider calls (Phase 1B.1)."""

from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.research_source_collection.readiness import collection_readiness
from app.schemas.contracts import (
    CommercialResearchEstimatedScope,
    CommercialResearchPreflightCommercial,
)


def _llm_configured(settings: Settings) -> bool:
    if settings.default_llm_provider == "mock":
        return True
    for attr in (
        "openai_api_key",
        "anthropic_api_key",
        "google_api_key",
        "yandex_ai_studio_api_key",
    ):
        secret = getattr(settings, attr, None)
        if secret is not None and secret.get_secret_value().strip():
            return True
    return False


def _estimate_scope(*, query_len: int, settings: Settings) -> CommercialResearchEstimatedScope:
    base_queries = max(3, min(12, query_len // 120 + 3))
    pages = base_queries * 2
    llm_calls = base_queries + 2
    note = (
        "Оценка основана на объёме запроса и лимитах конфигурации; "
        "точный объём уточняется после сбора источников."
    )
    if settings.research_source_collection_mock_providers:
        note = "Mock-режим: объём демонстрационный, без реального биллинга."
    return CommercialResearchEstimatedScope(
        estimated_search_queries=base_queries,
        estimated_fetched_pages=pages,
        estimated_llm_calls=llm_calls,
        scope_note_ru=note,
    )


def build_preflight_result(
    *,
    settings: Settings,
    query_text: str,
) -> tuple[CommercialResearchPreflightCommercial, dict[str, Any]]:
    readiness = collection_readiness(settings)
    blocking: list[str] = []
    scope = _estimate_scope(query_len=len(query_text), settings=settings)

    if not settings.research_source_collection_enabled:
        blocking.append("research_disabled_by_policy")
    elif not readiness.get("enabled"):
        blocking.append("research_not_enabled")

    mock_providers = settings.research_source_collection_mock_providers
    if not readiness.get("xmlriver_configured") and not mock_providers:
        blocking.append("search_provider_not_configured")
    if not readiness.get("firecrawl_configured") and not mock_providers:
        blocking.append("fetch_provider_not_configured")

    if not _llm_configured(settings):
        blocking.append("llm_not_configured")

    ready = len(blocking) == 0
    commercial = CommercialResearchPreflightCommercial(
        ready=ready,
        paid_execution_required=True,
        blocking_reasons=blocking,
        estimated_scope=scope,
        research_not_executed=True,
    )
    developer: dict[str, Any] = {
        "readiness_status": readiness.get("status"),
        "mock_providers": readiness.get("mock_providers"),
        "feature_flags": {
            "research_source_collection_enabled": settings.research_source_collection_enabled,
            "research_source_collection_mock_providers": (
                settings.research_source_collection_mock_providers
            ),
        },
        "providers": readiness.get("providers") or {},
        "llm_configured": _llm_configured(settings),
        "timeout_seconds": settings.llm_timeout_seconds,
        "max_retries": settings.llm_max_retries,
        "secrets_exposed": False,
    }
    return commercial, developer
