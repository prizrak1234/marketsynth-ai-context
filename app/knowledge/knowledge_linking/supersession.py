"""Supersession candidate detection for Knowledge Linking."""

from __future__ import annotations

from typing import Any

from app.knowledge.knowledge_linking.contracts import SUPERSESSION_COMPATIBILITY


def _parse_semver(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for piece in version.replace("-", ".").split("."):
        if piece.isdigit():
            parts.append(int(piece))
    return tuple(parts) if parts else (0,)


def detect_supersession_candidates(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    by_logical: dict[str, list[dict[str, Any]]] = {}
    for artifact in artifacts:
        logical_id = artifact.get("logical_artifact_id") or artifact.get("artifact_id")
        by_logical.setdefault(logical_id, []).append(artifact)

    for logical_id, group in by_logical.items():
        if len(group) < 2:
            continue
        ordered = sorted(group, key=lambda a: _parse_semver(a.get("version", "0")))
        for older, newer in zip(ordered, ordered[1:], strict=False):
            explicit = newer.get("supersedes") or []
            evidence = []
            if older["artifact_id"] in explicit or logical_id:
                evidence.append(
                    {"type": "explicit_supersedes_field", "newer": newer["artifact_id"]}
                )
            if _parse_semver(newer.get("version", "0")) > _parse_semver(older.get("version", "0")):
                evidence.append({"type": "higher_semantic_version"})
            if not evidence:
                continue
            compatibility = newer.get("compatibility_status", "unknown")
            if compatibility not in SUPERSESSION_COMPATIBILITY:
                compatibility = "unknown"
            candidates.append(
                {
                    "candidate_id": f"sup-{older['artifact_id']}-{newer['artifact_id']}",
                    "older_artifact_id": older["artifact_id"],
                    "newer_artifact_id": newer["artifact_id"],
                    "evidence": evidence,
                    "compatibility_status": compatibility,
                    "historical_resolution_required": True,
                    "retirement_recommendation": newer.get(
                        "retirement_recommendation", "review_only"
                    ),
                    "confidence": "high" if explicit else "medium",
                    "human_review_required": True,
                    "provenance": {"detector": "supersession", "logical_id": logical_id},
                }
            )
    return candidates
