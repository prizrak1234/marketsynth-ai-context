"""Source fingerprint and snapshot helpers (Commercial MVP P0.3).

Source answers: where did information come from?
Never includes analysis, summary, evidence, or conclusions.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from app.schemas.contracts import (
    SourceCapability,
    SourceCreateRequest,
    SourceFreshnessStatus,
    SourceProvenanceType,
    SourceSnapshot,
    SourceStatus,
    SourceType,
)

_FORBIDDEN_META_KEYS = frozenset(
    {
        "conclusion",
        "proof",
        "reasoning",
        "verdict",
        "analysis",
        "recommendation",
        "summary",
        "evidence",
        "content",
        "body",
        "raw_html",
        "document_text",
    }
)


def normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    raw = url.strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    scheme = (parsed.scheme or "https").lower()
    netloc = (parsed.netloc or "").lower()
    path = parsed.path.rstrip("/") or ""
    query = parsed.query
    if query:
        return f"{scheme}://{netloc}{path}?{query}"
    return f"{scheme}://{netloc}{path}"


def derive_domain(url: str | None, domain: str | None) -> str | None:
    if domain and domain.strip():
        return domain.strip().lower()
    normalized = normalize_url(url)
    if not normalized:
        return None
    return urlparse(normalized).netloc or None


def derive_freshness(
    *,
    published_at: datetime | None,
    accessed_at: datetime | None,
    captured_at: datetime | None,
    explicit: SourceFreshnessStatus | None,
    now: datetime | None = None,
) -> SourceFreshnessStatus:
    if explicit is not None:
        return explicit
    ref = published_at or accessed_at or captured_at
    if ref is None:
        return SourceFreshnessStatus.UNKNOWN
    anchor = now or datetime.utcnow()
    # naive comparison only when both naive/aware aligned
    try:
        age_days = (anchor - ref).days
    except TypeError:
        return SourceFreshnessStatus.UNKNOWN
    if age_days < 0:
        return SourceFreshnessStatus.UNKNOWN
    if age_days <= 90:
        return SourceFreshnessStatus.CURRENT
    if age_days <= 365:
        return SourceFreshnessStatus.ACCEPTABLE
    return SourceFreshnessStatus.OUTDATED


def fingerprint_payload(
    *,
    project_id: UUID,
    source_type: SourceType,
    title: str,
    url: str | None,
    publisher: str | None,
    published_at: datetime | None,
    content_hash: str | None,
) -> dict[str, Any]:
    return {
        "project_id": str(project_id),
        "source_type": source_type.value,
        "url": normalize_url(url),
        "publisher": (publisher or "").strip().lower() or None,
        "published_at": published_at.isoformat() if published_at else None,
        "content_hash": (content_hash or "").strip().lower() or None,
        "title": re.sub(r"\s+", " ", title.strip().lower()),
    }


def compute_source_fingerprint(
    *,
    project_id: UUID,
    source_type: SourceType,
    title: str,
    url: str | None,
    publisher: str | None,
    published_at: datetime | None,
    content_hash: str | None,
) -> str:
    payload = fingerprint_payload(
        project_id=project_id,
        source_type=source_type,
        title=title,
        url=url,
        publisher=publisher,
        published_at=published_at,
        content_hash=content_hash,
    )
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def sanitize_source_metadata(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not raw:
        return {}
    out: dict[str, Any] = {}
    for i, (key, value) in enumerate(raw.items()):
        if i >= 32:
            break
        k = str(key).strip()[:64]
        if not k or k.lower() in _FORBIDDEN_META_KEYS:
            continue
        if isinstance(value, str):
            out[k] = value.strip()[:500]
        elif isinstance(value, (int, float, bool)) or value is None:
            out[k] = value
        else:
            out[k] = str(value)[:500]
    return out


def validate_capabilities(capabilities: list[SourceCapability]) -> list[SourceCapability]:
    seen: list[SourceCapability] = []
    for cap in capabilities:
        if cap not in seen:
            seen.append(cap)
    if len(seen) > 16:
        from app.core.exceptions import InvalidStateError

        raise InvalidStateError("invalid_capability")
    return seen


def to_source_snapshot(
    *,
    source_id: UUID,
    project_id: UUID,
    version: int,
    fingerprint: str,
    content_hash: str | None,
    captured_at: datetime | None,
    accessed_at: datetime | None,
    supersedes_source_id: UUID | None,
    status: SourceStatus,
) -> SourceSnapshot:
    return SourceSnapshot(
        source_id=source_id,
        project_id=project_id,
        version=version,
        fingerprint=fingerprint,
        content_hash=content_hash,
        captured_at=captured_at,
        accessed_at=accessed_at,
        supersedes_source_id=supersedes_source_id,
        status=status,
    )


def material_to_source_candidate(
    *,
    title: str,
    material_type: str | None,
    url: str | None,
    local_reference_label: str | None,
) -> dict[str, Any]:
    """Explicit P0.1 materials → Source registration candidate (never auto-applied)."""
    mapped_type = SourceType.UPLOADED_DOCUMENT
    if material_type:
        mt = material_type.lower()
        if "website" in mt or "url" in mt:
            mapped_type = SourceType.WEBSITE
        elif "spreadsheet" in mt or "sheet" in mt or "csv" in mt:
            mapped_type = SourceType.SPREADSHEET
        elif "presentation" in mt or "deck" in mt:
            mapped_type = SourceType.PRESENTATION
        elif "analytics" in mt:
            mapped_type = SourceType.ANALYTICS_EXPORT
    return {
        "source_type": mapped_type.value,
        "provenance_type": SourceProvenanceType.USER_PROVIDED.value,
        "title": title,
        "origin": "project_brief_materials",
        "url": url,
        "capabilities": [],
        "reliability_level": "unverified",
        "material_reference": local_reference_label,
        "auto_migrate": False,
        "requires_user_confirmation": True,
        "no_binary_content": True,
        "no_url_fetch": True,
    }


def create_request_identity_fields(request: SourceCreateRequest) -> dict[str, Any]:
    return {
        "source_type": request.source_type,
        "title": request.title,
        "url": request.url,
        "publisher": request.publisher,
        "published_at": request.published_at,
        "content_hash": request.content_hash,
    }
