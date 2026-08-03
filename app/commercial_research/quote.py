"""Reproducible quote — no provider billing (Phase 1B.1)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

from app.core.config import Settings
from app.db.base import utc_now
from app.research_source_collection.readiness import collection_readiness
from app.schemas.contracts import (
    CommercialResearchEstimatedScope,
    CommercialResearchQuote,
    CommercialResearchQuoteCommercial,
)


def _cost_range(
    *,
    scope: CommercialResearchEstimatedScope,
    settings: Settings,
) -> tuple[str, str, list[str]]:
    assumptions: list[str] = []
    if settings.research_source_collection_mock_providers:
        return "0", "0", ["Mock-режим: стоимость нулевая, без реального биллинга."]

    search_unit_min, search_unit_max = 3, 8
    page_unit_min, page_unit_max = 5, 15
    llm_unit_min, llm_unit_max = 2, 6

    min_cost = (
        scope.estimated_search_queries * search_unit_min
        + scope.estimated_fetched_pages * page_unit_min
        + scope.estimated_llm_calls * llm_unit_min
    )
    max_cost = (
        scope.estimated_search_queries * search_unit_max
        + scope.estimated_fetched_pages * page_unit_max
        + scope.estimated_llm_calls * llm_unit_max
    )
    assumptions.append(
        "Диапазон рассчитан по ориентировочным единицам провайдеров; "
        "точная цена зависит от фактического числа запросов и страниц."
    )
    if not settings.research_source_collection_enabled:
        assumptions.append("Сбор источников отключён политикой — quote носит справочный характер.")
    return str(min_cost), str(max_cost), assumptions


def build_quote(
    *,
    tenant_id: UUID,
    request_hash: str,
    scope: CommercialResearchEstimatedScope,
    settings: Settings,
    quote_ttl_hours: int = 24,
) -> tuple[CommercialResearchQuote, CommercialResearchQuoteCommercial, dict[str, Any]]:
    now = utc_now()
    expires = now + timedelta(hours=quote_ttl_hours)
    cost_min, cost_max, assumptions = _cost_range(scope=scope, settings=settings)
    readiness = collection_readiness(settings)
    quote = CommercialResearchQuote(
        quote_id=uuid4(),
        request_hash=request_hash,
        tenant_id=tenant_id,
        estimated_search_queries=scope.estimated_search_queries,
        estimated_fetched_pages=scope.estimated_fetched_pages,
        estimated_llm_calls=scope.estimated_llm_calls,
        estimated_llm_tokens=scope.estimated_llm_calls * 1500,
        estimated_cost_min=cost_min,
        estimated_cost_max=cost_max,
        currency="RUB",
        assumptions=assumptions,
        provider_capabilities={
            "search": bool(readiness.get("xmlriver_configured")),
            "fetch": bool(readiness.get("firecrawl_configured")),
            "mock_mode": bool(settings.research_source_collection_mock_providers),
        },
        created_at=now,
        expires_at=expires,
    )
    if cost_min == cost_max:
        label = f"≈ {cost_min} {quote.currency}"
    else:
        label = f"≈ {cost_min}–{cost_max} {quote.currency}"
    commercial = CommercialResearchQuoteCommercial(
        cost_range_label=label,
        currency=quote.currency,
        expires_at=expires,
        assumptions=assumptions,
        research_not_executed=True,
    )
    developer = {
        "quote_id": str(quote.quote_id),
        "request_hash": request_hash,
        "readiness_status": readiness.get("status"),
        "estimated_llm_tokens": quote.estimated_llm_tokens,
    }
    return quote, commercial, developer
