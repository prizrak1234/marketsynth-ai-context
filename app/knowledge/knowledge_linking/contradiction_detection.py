"""Contradiction candidate detection for Knowledge Linking."""

from __future__ import annotations

from typing import Any

from app.knowledge.knowledge_linking.contracts import CONTRADICTION_TYPES


def detect_contradiction_candidates(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}

    for artifact in artifacts:
        for claim in artifact.get("declared_claims") or []:
            key = (claim.get("claim_key", ""), claim.get("domain", "general"))
            if key[0]:
                by_key.setdefault(key, []).append({"artifact": artifact, "claim": claim})

    for key, entries in by_key.items():
        if len(entries) < 2:
            continue
        values = {entry["claim"].get("value") for entry in entries}
        if len(values) <= 1:
            continue
        artifact_ids = [entry["artifact"]["artifact_id"] for entry in entries]
        contradiction_type = entries[0]["claim"].get("contradiction_type", "unknown")
        if contradiction_type not in CONTRADICTION_TYPES:
            contradiction_type = "unknown"
        candidates.append(
            {
                "contradiction_id": f"contra-{'-'.join(artifact_ids[:2])[:24]}",
                "artifact_ids": artifact_ids,
                "contradiction_type": contradiction_type,
                "statements_or_rules": [
                    {
                        "artifact_id": entry["artifact"]["artifact_id"],
                        "statement": entry["claim"].get("statement", entry["claim"].get("value")),
                    }
                    for entry in entries
                ],
                "evidence": [{"type": "conflicting_claim_values", "claim_key": key[0]}],
                "severity": entries[0]["claim"].get("severity", "medium"),
                "blocking": entries[0]["claim"].get("blocking", False),
                "resolution_owner": "human_reviewer",
                "recommended_resolution_process": "manual_review_no_auto_winner",
                "provenance": {"detector": "contradiction"},
            }
        )
    return candidates
