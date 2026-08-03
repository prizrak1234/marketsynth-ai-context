"""Immutable publication package payload snapshot (Phase AI.62)."""

from __future__ import annotations

from typing import Any

from app.db.models.marketing import PublicationPackageTable


def build_package_payload_snapshot(package: PublicationPackageTable) -> dict[str, Any]:
    return {
        "publication_package_id": str(package.id),
        "content_asset_id": str(package.content_asset_id),
        "channel": package.channel.value,
        "title": package.title,
        "body": package.body,
        "cta": package.cta,
        "metadata": dict(package.package_metadata or {}),
        "package_status_at_snapshot": package.status.value,
    }
