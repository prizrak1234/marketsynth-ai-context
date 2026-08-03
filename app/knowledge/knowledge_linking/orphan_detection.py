"""Orphan artifact detection for Knowledge Linking."""

from __future__ import annotations

from typing import Any

from app.knowledge.knowledge_linking.contracts import STANDALONE_EXEMPTION_FLAGS


def is_standalone_exempt(artifact: dict[str, Any]) -> bool:
    exemptions = artifact.get("standalone_exemptions") or []
    if any(flag in STANDALONE_EXEMPTION_FLAGS for flag in exemptions):
        return True
    if artifact.get("artifact_type") == "source_archive" and artifact.get("standalone"):
        return True
    if artifact.get("artifact_type") == "schema_bundle" and artifact.get("frozen_root_index"):
        return True
    return (
        artifact.get("lifecycle_status") == "rejected"
        and artifact.get("intentionally_isolated") is True
    )


def detect_orphan_artifacts(
    artifacts: list[dict[str, Any]],
    linked_ids: set[str],
) -> list[dict[str, Any]]:
    orphans: list[dict[str, Any]] = []
    for artifact in artifacts:
        artifact_id = artifact["artifact_id"]
        if is_standalone_exempt(artifact):
            continue
        if artifact_id in linked_ids:
            continue
        orphans.append(
            {
                "artifact_id": artifact_id,
                "artifact_type": artifact.get("artifact_type", "other"),
                "orphan_reason": "no_inbound_or_outbound_links_in_scope",
                "expected_link_types": artifact.get("expected_link_types", ["related_to"]),
                "possible_targets": artifact.get("possible_targets", []),
                "confidence": "medium",
                "human_review_required": True,
                "provenance": {"detector": "orphan_after_visibility"},
            }
        )
    return orphans


def collect_linked_artifact_ids(
    existing_links: list[dict[str, Any]],
    proposed_links: list[dict[str, Any]],
) -> set[str]:
    linked: set[str] = set()
    for link in [*existing_links, *proposed_links]:
        source = link.get("source_artifact_id")
        target = link.get("target_artifact_id")
        if source:
            linked.add(source)
        if target:
            linked.add(target)
    return linked
