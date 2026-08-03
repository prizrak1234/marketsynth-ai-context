"""Approved ContentAsset → PublicationPackage draft (Phase AI.44)."""

from __future__ import annotations

from typing import Any

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_payload, sanitize_text
from app.db.models.marketing import ContentAssetTable
from app.marketing.contracts import ContentAssetStatus, PublicationPackageChannel

_CHANNEL_VALUES = frozenset(ch.value for ch in PublicationPackageChannel)


def assert_asset_eligible_for_publication_package(asset: ContentAssetTable) -> None:
    status = asset.status
    status_value = status.value if hasattr(status, "value") else str(status)
    if status_value != ContentAssetStatus.APPROVED.value:
        raise InvalidStateError(
            "Only approved content assets can create publication packages",
        )


def parse_publication_channel(channel: str) -> PublicationPackageChannel:
    cleaned = sanitize_text(channel).strip().lower()
    if cleaned not in _CHANNEL_VALUES:
        raise InvalidStateError(
            f"Unsupported publication channel: {channel}. "
            f"Allowed: {', '.join(sorted(_CHANNEL_VALUES))}",
        )
    return PublicationPackageChannel(cleaned)


def build_publication_package_fields(
    asset: ContentAssetTable,
    *,
    channel: PublicationPackageChannel,
    title: str | None = None,
    body: str | None = None,
    cta: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    final_title = sanitize_text(title or asset.title).strip()[:512]
    if not final_title:
        raise InvalidStateError("Publication package title cannot be empty")

    final_body = body if body is not None else (asset.body or "")
    final_cta = sanitize_text(cta).strip()[:512] if cta else None
    if final_cta == "":
        final_cta = None

    base_metadata = dict(asset.asset_metadata or {})
    extra = sanitize_payload(metadata or {}) or {}
    merged = {**base_metadata, **extra}
    merged["conversion_source"] = "approved_content_asset"
    merged["source_channel"] = channel.value

    return {
        "title": final_title,
        "body": final_body,
        "cta": final_cta,
        "metadata": merged,
    }
