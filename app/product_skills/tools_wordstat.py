"""Audited Wordstat tools — XMLRiver credentials via Settings binding (not package .env)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import get_settings
from app.core.exceptions import InvalidStateError
from app.product_skills.permissions import assert_host_allowed, assert_tool_allowed
from app.product_skills.secret_binding import resolve_secret_alias
from app.schemas.contracts import ProductSkillManifest


def _credentials() -> tuple[str, str]:
    user = resolve_secret_alias("XML_RIVER_USER_ID")
    key = resolve_secret_alias("XML_RIVER_KEY")
    if not user.configured or not key.configured:
        raise InvalidStateError("xmlriver_unconfigured")
    assert user.value and key.value
    return user.value, key.value


def _get_json(url: str, *, timeout: float = 65.0) -> dict[str, Any]:
    req = Request(url, headers={"User-Agent": "Marketsynth-ProductSkill/1.0"})
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — host allowlisted by caller
        raw = resp.read().decode("utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise InvalidStateError("xmlriver_malformed_response")
    if "code" in data and data.get("code") not in (None, 0, "0"):
        code = data.get("code")
        if code in (401, 403, "401", "403"):
            raise InvalidStateError("xmlriver_auth_error")
        if code in (429, "429"):
            raise InvalidStateError("xmlriver_rate_limited")
        if code in (402, "402"):
            raise InvalidStateError("xmlriver_balance_error")
        raise InvalidStateError("xmlriver_provider_error")
    return data


def wordstat_frequency(
    manifest: ProductSkillManifest,
    query: str,
    *,
    regions: str = "",
) -> dict[str, Any]:
    assert_tool_allowed(manifest, "wordstat.frequency")
    assert_host_allowed(manifest, "xmlriver.com")
    user, key = _credentials()
    settings = get_settings()
    # Prefer HTTPS when available; XMLRiver docs historically used http — still host-bound.
    use_https = bool(getattr(settings, "xmlriver_wordstat_https", True))
    scheme = "https" if use_https else "http"
    params = {
        "user": user,
        "key": key,
        "query": query.replace("&", "%26"),
        "pagetype": "history",
        "period": "month",
    }
    if regions:
        params["regions"] = regions
    url = f"{scheme}://xmlriver.com/wordstat/new/json?{urlencode(params)}"
    # Redact secrets from evidence URL
    safe_url = f"{scheme}://xmlriver.com/wordstat/new/json?pagetype=history&period=month"
    try:
        data = _get_json(url)
    except InvalidStateError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise InvalidStateError(f"xmlriver_timeout_or_network:{type(exc).__name__}") from exc
    total = data.get("totalValue")
    return {
        "query": query,
        "frequency": total,
        "source": "XMLRiver",
        "collected_at": datetime.now(UTC).isoformat(),
        "request_metadata": {"endpoint": safe_url, "api": "wordstat_new", "pagetype": "history"},
        "limitations": ["Single-phrase frequency; no bulk crawl in MVP"],
        "raw_keys": sorted(list(data.keys()))[:20],
    }


def wordstat_expand(
    manifest: ProductSkillManifest,
    query: str,
    *,
    regions: str = "",
) -> dict[str, Any]:
    assert_tool_allowed(manifest, "wordstat.expand")
    assert_host_allowed(manifest, "xmlriver.com")
    user, key = _credentials()
    settings = get_settings()
    use_https = bool(getattr(settings, "xmlriver_wordstat_https", True))
    scheme = "https" if use_https else "http"
    params = {
        "user": user,
        "key": key,
        "query": query.replace("&", "%26"),
        "pagetype": "words",
    }
    if regions:
        params["regions"] = regions
    url = f"{scheme}://xmlriver.com/wordstat/new/json?{urlencode(params)}"
    safe_url = f"{scheme}://xmlriver.com/wordstat/new/json?pagetype=words"
    try:
        data = _get_json(url)
    except InvalidStateError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise InvalidStateError(f"xmlriver_timeout_or_network:{type(exc).__name__}") from exc
    popular = data.get("popular") or []
    associations = data.get("associations") or []
    phrases: list[dict[str, Any]] = []
    seen: set[str] = set()
    for bucket in (popular, associations):
        if not isinstance(bucket, list):
            continue
        for item in bucket:
            if not isinstance(item, dict):
                continue
            phrase = str(item.get("text") or item.get("phrase") or "").strip()
            if not phrase or phrase.lower() in seen:
                continue
            seen.add(phrase.lower())
            phrases.append(
                {
                    "phrase": phrase,
                    "value": item.get("value") or item.get("number"),
                }
            )
    return {
        "query": query,
        "phrases": phrases[:100],
        "source": "XMLRiver",
        "collected_at": datetime.now(UTC).isoformat(),
        "request_metadata": {"endpoint": safe_url, "api": "wordstat_new", "pagetype": "words"},
        "limitations": ["First page only; no multi-page bulk in MVP"],
    }


def wordstat_related(
    manifest: ProductSkillManifest,
    query: str,
) -> dict[str, Any]:
    assert_tool_allowed(manifest, "wordstat.related")
    expanded = wordstat_expand(manifest, query)
    return {
        **expanded,
        "related": expanded.get("phrases") or [],
    }
