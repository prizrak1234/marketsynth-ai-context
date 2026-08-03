"""Provider readiness + optional live probes — never expose credentials."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.config import Settings, get_settings
from app.db.base import utc_now
from app.schemas.contracts import ResearchProviderReadiness, ResearchProviderState

_SUPPORTED = {
    "xmlriver": ["search"],
    "firecrawl": ["fetch"],
}


def _configured_xmlriver(settings: Settings) -> bool:
    key = settings.xmlriver_api_key
    return bool(
        (settings.xmlriver_user_id or "").strip()
        and key
        and key.get_secret_value().strip()
    )


def _configured_firecrawl(settings: Settings) -> bool:
    key = settings.firecrawl_api_key
    return bool(key and key.get_secret_value().strip())


def _base_provider(
    name: str,
    *,
    configured: bool,
    blocked: bool,
    mock: bool,
) -> ResearchProviderReadiness:
    if blocked:
        state = ResearchProviderState.BLOCKED_BY_POLICY
    elif mock:
        state = ResearchProviderState.PARTIALLY_READY if configured else ResearchProviderState.UNAVAILABLE
    elif configured:
        state = ResearchProviderState.PARTIALLY_READY  # configured but not probed yet
    else:
        state = ResearchProviderState.UNAVAILABLE
    return ResearchProviderReadiness(
        provider=name,
        state=state,
        configured=configured,
        reachable=False,
        authentication_valid=None,
        read_only_capability=True,
        supported_operations=list(_SUPPORTED.get(name, [])),
        rate_limit_state="unknown",
        safe_error_code=None if configured or blocked else "not_configured",
        last_checked_at=utc_now(),
    )


def collection_readiness(settings: Settings | None = None) -> dict[str, Any]:
    """Synchronous credential-presence readiness (no network)."""
    s = settings or get_settings()
    blocked = not s.research_source_collection_enabled
    xml = _base_provider(
        "xmlriver",
        configured=_configured_xmlriver(s),
        blocked=blocked,
        mock=s.research_source_collection_mock_providers,
    )
    fire = _base_provider(
        "firecrawl",
        configured=_configured_firecrawl(s),
        blocked=blocked,
        mock=s.research_source_collection_mock_providers,
    )
    providers = {
        "xmlriver": xml.model_dump(mode="json"),
        "firecrawl": fire.model_dump(mode="json"),
    }
    configured_count = sum(1 for p in (xml, fire) if p.configured)
    if blocked:
        status = ResearchProviderState.BLOCKED_BY_POLICY.value
    elif s.research_source_collection_mock_providers:
        status = ResearchProviderState.PARTIALLY_READY.value
    elif configured_count == 2:
        status = ResearchProviderState.READY.value
    elif configured_count == 1:
        status = ResearchProviderState.PARTIALLY_READY.value
    else:
        status = ResearchProviderState.UNAVAILABLE.value
    return {
        "status": status,
        "mock_providers": s.research_source_collection_mock_providers,
        "enabled": s.research_source_collection_enabled,
        "firecrawl_configured": fire.configured,
        "xmlriver_configured": xml.configured,
        "providers": providers,
        "coverage_disclosure_ru": _coverage_ru(status, s.research_source_collection_mock_providers),
        "last_checked_at": utc_now().isoformat(),
    }


def _coverage_ru(status: str, mock: bool) -> str:
    if mock:
        return (
            "Включён mock-режим провайдеров: результаты демонстрационные, "
            "не подтверждают реальный поиск."
        )
    if status == ResearchProviderState.READY.value:
        return "Доступны оба read-only провайдера: XMLRiver (поиск) и Firecrawl (извлечение)."
    if status == ResearchProviderState.PARTIALLY_READY.value:
        return (
            "Покрытие ограничено: доступен только один из провайдеров. "
            "Полное исследовательское покрытие не заявлено."
        )
    if status == ResearchProviderState.BLOCKED_BY_POLICY.value:
        return "Сбор источников отключён политикой конфигурации."
    return "Реальные провайдеры недоступны: сбор источников невозможен."


async def probe_providers(
    settings: Settings | None = None,
    *,
    live: bool = True,
) -> dict[str, Any]:
    """Optional live read-only probes. Never returns secrets or raw dumps."""
    s = settings or get_settings()
    base = collection_readiness(s)
    if not live or not s.research_source_collection_enabled:
        return base
    if s.research_source_collection_mock_providers:
        base["probe_skipped"] = "mock_providers_enabled"
        return base

    providers: dict[str, Any] = dict(base.get("providers") or {})

    if _configured_xmlriver(s):
        providers["xmlriver"] = (await _probe_xmlriver(s)).model_dump(mode="json")
    if _configured_firecrawl(s):
        providers["firecrawl"] = (await _probe_firecrawl(s)).model_dump(mode="json")

    states = [p.get("state") for p in providers.values()]
    if all(st == ResearchProviderState.READY.value for st in states) and len(states) == 2:
        status = ResearchProviderState.READY.value
    elif any(st == ResearchProviderState.READY.value for st in states):
        status = ResearchProviderState.PARTIALLY_READY.value
    elif any(st == ResearchProviderState.INVALID_CREDENTIALS.value for st in states):
        status = ResearchProviderState.INVALID_CREDENTIALS.value
    else:
        status = ResearchProviderState.UNAVAILABLE.value

    base.update(
        {
            "status": status,
            "providers": providers,
            "coverage_disclosure_ru": _coverage_ru(status, False),
            "probed": True,
            "last_checked_at": utc_now().isoformat(),
        }
    )
    return base


async def _probe_xmlriver(settings: Settings) -> ResearchProviderReadiness:
    from app.business_tools.contracts import BusinessToolError
    from app.business_tools.providers.xmlriver_search import XmlRiverSearchTool

    row = _base_provider("xmlriver", configured=True, blocked=False, mock=False)
    started = utc_now()
    try:
        result = await XmlRiverSearchTool(settings).probe()
        latency = int((utc_now() - started).total_seconds() * 1000)
        row.reachable = True
        row.authentication_valid = True
        row.state = ResearchProviderState.READY
        row.latency_ms = latency
        row.probe_result_count = int(result.get("result_count") or 0)
        row.rate_limit_state = str(result.get("rate_limit_state") or "ok")
        row.safe_error_code = None
        row.last_checked_at = utc_now()
        return row
    except BusinessToolError as exc:
        latency = int((utc_now() - started).total_seconds() * 1000)
        row.latency_ms = latency
        row.last_checked_at = utc_now()
        row.safe_error_code = exc.category
        if exc.category in {"invalid_credentials", "auth_error"}:
            row.state = ResearchProviderState.INVALID_CREDENTIALS
            row.authentication_valid = False
            row.reachable = True
        elif exc.category == "rate_limited":
            row.state = ResearchProviderState.PARTIALLY_READY
            row.reachable = True
            row.rate_limit_state = "limited"
            row.authentication_valid = True
        elif exc.category == "credits_exhausted":
            row.state = ResearchProviderState.PARTIALLY_READY
            row.reachable = True
            row.authentication_valid = True
            row.rate_limit_state = "credits_exhausted"
        else:
            row.state = ResearchProviderState.UNAVAILABLE
            row.reachable = False
        return row


async def _probe_firecrawl(settings: Settings) -> ResearchProviderReadiness:
    from app.business_tools.contracts import BusinessToolError
    from app.business_tools.providers.firecrawl_fetch import FirecrawlFetchTool

    row = _base_provider("firecrawl", configured=True, blocked=False, mock=False)
    started = utc_now()
    try:
        result = await FirecrawlFetchTool(settings).probe()
        latency = int((utc_now() - started).total_seconds() * 1000)
        row.reachable = True
        row.authentication_valid = True
        row.state = ResearchProviderState.READY
        row.latency_ms = latency
        row.probe_result_count = 1 if result.get("ok") else 0
        row.rate_limit_state = str(result.get("rate_limit_state") or "ok")
        row.safe_error_code = None
        row.last_checked_at = utc_now()
        return row
    except BusinessToolError as exc:
        latency = int((utc_now() - started).total_seconds() * 1000)
        row.latency_ms = latency
        row.last_checked_at = utc_now()
        row.safe_error_code = exc.category
        if exc.category in {"invalid_credentials", "auth_error"}:
            row.state = ResearchProviderState.INVALID_CREDENTIALS
            row.authentication_valid = False
            row.reachable = True
        elif exc.category == "rate_limited":
            row.state = ResearchProviderState.PARTIALLY_READY
            row.reachable = True
            row.rate_limit_state = "limited"
            row.authentication_valid = True
        elif exc.category == "credits_exhausted":
            row.state = ResearchProviderState.PARTIALLY_READY
            row.reachable = True
            row.authentication_valid = True
            row.rate_limit_state = "credits_exhausted"
        else:
            row.state = ResearchProviderState.UNAVAILABLE
            row.reachable = False
        return row


def localize_provider_error(safe_error_code: str | None) -> str:
    mapping = {
        "not_configured": "Провайдер не настроен.",
        "provider_unavailable": "Провайдер временно недоступен.",
        "provider_error": "Ошибка ответа провайдера.",
        "invalid_credentials": "Учётные данные провайдера недействительны.",
        "auth_error": "Ошибка аутентификации провайдера.",
        "rate_limited": "Достигнут лимит запросов провайдера.",
        "credits_exhausted": "Кредиты провайдера исчерпаны.",
        "timeout": "Превышено время ожидания ответа провайдера.",
        "zero_results": "Поиск не вернул результатов.",
        "invalid_url": "Некорректный адрес страницы.",
        "invalid_query": "Пустой или недопустимый поисковый запрос.",
    }
    return mapping.get(safe_error_code or "", "Ограничение провайдера. Подробности скрыты из соображений безопасности.")
