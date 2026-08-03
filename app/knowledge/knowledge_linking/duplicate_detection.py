"""Duplicate candidate detection for Knowledge Linking."""

from __future__ import annotations

from typing import Any

from app.knowledge.knowledge_linking.contracts import DUPLICATE_TYPES


def _normalize_title(title: str) -> str:
    return " ".join(title.lower().split())


def detect_duplicate_candidates(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen_hashes: dict[str, list[str]] = {}
    seen_identity: dict[tuple[str, str, str], list[str]] = {}

    for artifact in artifacts:
        artifact_id = artifact["artifact_id"]
        content_hash = artifact.get("content_hash")
        if content_hash:
            seen_hashes.setdefault(content_hash, []).append(artifact_id)

        identity_key = (
            artifact.get("artifact_type", ""),
            artifact.get("title", ""),
            artifact.get("version", ""),
        )
        if identity_key[0] and identity_key[1] and identity_key[2]:
            seen_identity.setdefault(identity_key, []).append(artifact_id)

    for content_hash, artifact_ids in seen_hashes.items():
        if len(artifact_ids) < 2:
            continue
        candidates.append(
            {
                "duplicate_candidate_id": f"dup-hash-{content_hash[:8]}",
                "artifact_ids": artifact_ids,
                "duplicate_type": "exact_content",
                "evidence": [{"type": "identical_content_hash", "hash": content_hash}],
                "differences": [],
                "confidence": "high",
                "merge_recommended": False,
                "human_review_required": True,
                "provenance": {"detector": "exact_hash"},
            }
        )

    for identity_key, artifact_ids in seen_identity.items():
        if len(artifact_ids) < 2:
            continue
        hashes = {
            aid: next(a["content_hash"] for a in artifacts if a["artifact_id"] == aid)
            for aid in artifact_ids
        }
        unique_hashes = set(hashes.values())
        duplicate_type = "identity_conflict" if len(unique_hashes) > 1 else "version_conflict"
        candidates.append(
            {
                "duplicate_candidate_id": f"dup-id-{'-'.join(artifact_ids[:2])[:24]}",
                "artifact_ids": artifact_ids,
                "duplicate_type": duplicate_type,
                "evidence": [{"type": "shared_logical_identity", "identity": identity_key}],
                "differences": [
                    {"artifact_id": aid, "content_hash": hashes[aid]} for aid in artifact_ids
                ],
                "confidence": "high" if duplicate_type == "identity_conflict" else "medium",
                "merge_recommended": False,
                "human_review_required": True,
                "provenance": {"detector": "identity_version"},
            }
        )

    title_groups: dict[tuple[str, str], list[str]] = {}
    for artifact in artifacts:
        key = (artifact.get("artifact_type", ""), _normalize_title(artifact.get("title", "")))
        if key[0] and key[1]:
            title_groups.setdefault(key, []).append(artifact["artifact_id"])

    for (artifact_type, title), artifact_ids in title_groups.items():
        if len(artifact_ids) < 2:
            continue
        versions = {
            aid: next(a.get("version") for a in artifacts if a["artifact_id"] == aid)
            for aid in artifact_ids
        }
        if len(set(versions.values())) == len(versions):
            continue
        if any(c["artifact_ids"] == artifact_ids for c in candidates):
            continue
        candidates.append(
            {
                "duplicate_candidate_id": f"dup-title-{artifact_type}-{title[:12]}",
                "artifact_ids": artifact_ids,
                "duplicate_type": "normalized_title",
                "evidence": [{"type": "normalized_title_match", "title": title}],
                "differences": [],
                "confidence": "medium",
                "merge_recommended": False,
                "human_review_required": True,
                "provenance": {"detector": "normalized_title"},
            }
        )

    for candidate in candidates:
        if candidate["duplicate_type"] not in DUPLICATE_TYPES:
            candidate["duplicate_type"] = "unknown"
    return candidates


def classify_provider_variants(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    variants: list[dict[str, Any]] = []
    topology_groups: dict[str, list[str]] = {}
    for artifact in artifacts:
        topology = artifact.get("provider_neutral_topology_id")
        if topology:
            topology_groups.setdefault(topology, []).append(artifact["artifact_id"])
    for topology, artifact_ids in topology_groups.items():
        if len(artifact_ids) < 2:
            continue
        variants.append(
            {
                "link_id": f"variant-{topology[:12]}",
                "source_artifact_id": artifact_ids[0],
                "target_artifact_id": artifact_ids[1],
                "relation_type": "variant_of",
                "direction": "bidirectional",
                "reason": "Provider-neutral topology equivalence",
                "supporting_evidence": [
                    {"type": "structurally_equivalent_pattern", "topology": topology}
                ],
                "confidence": "medium",
                "human_review_required": True,
                "conflict_status": "none",
                "provenance": {"detector": "provider_variant"},
            }
        )
    return variants
