"""KB-WPL-01.3C library-wide freeze manifest builders — read-only audit artifacts."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.knowledge.workflow_patterns.serialization import (
    FROZEN_CATALOG_HASH,
    FROZEN_PILOT_BUNDLE_HASH,
    FROZEN_SCHEMA_HASH,
    audit_semantic_hash,
    load_core_audit_records,
    load_core_manifest,
    load_core_patterns,
    load_core_practices,
    load_core_source_support_map,
    load_pilot_audit_records,
    load_pilot_manifest,
    load_pilot_patterns,
    load_pilot_practices,
    load_pilot_source_support_map,
    practice_semantic_hash,
    sha256_bytes,
    source_support_map_semantic_hash,
)

FROZEN_CORE_BUNDLE_HASH = "b715466982b73f86c11bb05310d72def00a540982baea6ab80882e06b0737fbf"
LIBRARY_VERSION = "0.1.0-frozen"
PROHIBITED_MATURITY = [
    "active",
    "executable",
    "deployed",
    "approved",
    "platform_adapted",
    "production_ready",
    "approved_for_execution",
]
DEFERRED_PATTERNS = [
    "billing_reconciliation",
    "ad_spend_tracking",
    "payment_capture",
    "bulk_delete_without_review",
    "prompt_injection_filter",
    "campaign_result_to_learning_candidate",
    "change_review_before_activation",
    "manual_review_queue",
    "timeout_and_resume",
    "partial_failure_isolation",
    "scheduled_recovery",
    "incremental_processing",
    "structured_output_validation",
    "deduplication_before_write",
    "reflection_and_revision",
    "long_form_to_social_repurposing",
    "approved_content_to_publication",
    "review_analysis_to_insight",
    "workflow_documentation",
    "credential_preserving_update",
    "provider_version_compatibility",
    "sandbox_last_mile_debug",
    "test_fixture_replay",
]
ACCEPTED_LIMITATIONS = [
    "maturity=reviewed does not imply runtime correctness",
    "owner_review_required=true on all audit records",
    "multi-pattern source overlap documented; no source exclusivity",
    "provider-neutral main flows; provider details in variants only",
    "learning patterns create knowledge_candidate only",
    "no pattern grants execution or deployment permission",
    "green schema tests do not prove runtime benchmark",
]


def _tier_for_pattern(pattern_id: str, pilot_ids: set[str]) -> str:
    return "pilot" if pattern_id in pilot_ids else "core"


def build_overlap_matrix() -> dict[str, Any]:
    pilot_map = load_pilot_source_support_map()
    core_map = load_core_source_support_map()
    by_source: dict[str, list[dict[str, Any]]] = {}

    for support_map in (pilot_map, core_map):
        for entry in support_map["entries"]:
            pattern_id = entry["pattern_id"]
            for signal in entry["supporting_signals"]:
                source_id = signal["source_workflow_id"]
                by_source.setdefault(source_id, []).append(
                    {
                        "pattern_id": pattern_id,
                        "signal_type": signal["signal_type"],
                        "supported_rule": signal["supported_pattern_rule"],
                        "topology_location": signal["topology_location"],
                        "confidence": signal["confidence"],
                    }
                )

    overlaps: list[dict[str, Any]] = []
    for source_id, signals in sorted(by_source.items()):
        pattern_ids = sorted({s["pattern_id"] for s in signals})
        supported_rules = sorted({s["supported_rule"] for s in signals})
        independence = "single_pattern"
        if len(pattern_ids) > 1:
            rule_per_pattern = {
                pid: sorted({s["supported_rule"] for s in signals if s["pattern_id"] == pid})
                for pid in pattern_ids
            }
            distinct_rules = len({tuple(rules) for rules in rule_per_pattern.values()})
            independence = (
                "pattern_specific_signals"
                if distinct_rules == len(pattern_ids)
                else "shared_rule_overlap"
            )
        overlaps.append(
            {
                "source_workflow_id": source_id,
                "supported_pattern_ids": pattern_ids,
                "signal_types": sorted({s["signal_type"] for s in signals}),
                "supported_rules": supported_rules,
                "independence_assessment": independence,
                "pattern_signals": signals,
            }
        )

    return {
        "library_version": LIBRARY_VERSION,
        "program_phase": "KB-WPL-01.3C",
        "overlap_count": sum(1 for o in overlaps if len(o["supported_pattern_ids"]) > 1),
        "entries": overlaps,
    }


def overlap_matrix_semantic_hash(matrix: dict[str, Any]) -> str:
    subset = {
        "library_version": matrix["library_version"],
        "program_phase": matrix["program_phase"],
        "entries": matrix["entries"],
    }
    payload = json.dumps(subset, sort_keys=True, separators=(",", ":"))
    return sha256_bytes(payload.encode("utf-8"))


def build_library_index(*, generated_at: str | None = None) -> dict[str, Any]:
    pilot_manifest = load_pilot_manifest()
    core_manifest = load_core_manifest()
    patterns: list[dict[str, Any]] = []
    for pattern in load_pilot_patterns():
        patterns.append({**pattern, "_tier": "pilot"})
    for pattern in load_core_patterns():
        patterns.append({**pattern, "_tier": "core"})

    entries: list[dict[str, Any]] = []
    all_pattern_hashes: dict[str, str] = {}
    for pattern in patterns:
        pid = pattern["pattern_id"]
        tier = pattern["_tier"]
        manifest_hashes = (
            pilot_manifest["pattern_hashes"]
            if tier == "pilot"
            else core_manifest["core_pattern_hashes"]
        )
        semantic_hash = manifest_hashes[pid]
        all_pattern_hashes[pid] = semantic_hash
        audit_id = f"audit-{pid}" if tier == "pilot" else f"audit-core-{pid}"
        entries.append(
            {
                "pattern_id": pid,
                "tier": tier,
                "pattern_category": pattern["pattern_category"],
                "maturity": pattern["maturity"],
                "practice_ids": pattern.get("source_practice_ids") or [],
                "source_workflow_ids": pattern.get("source_workflow_ids") or [],
                "audit_id": audit_id,
                "semantic_hash": semantic_hash,
                "approval_sensitive": pattern.get("approval_requirements", {}).get(
                    "human_approval_required",
                    False,
                ),
                "publication_sensitive": pattern.get("publication_sensitive", False),
                "tenant_scope": pattern.get("tenant_scope", ""),
                "billing_sensitive": pattern.get("billing_sensitive", False),
                "destructive": pattern.get("destructive", False),
                "deferred_capabilities": [],
                "known_limitations": pattern.get("known_limitations") or [],
            }
        )

    all_practices = load_pilot_practices() + load_core_practices()
    practice_hashes = {
        p["practice_id"]: practice_semantic_hash(p) for p in all_practices
    }

    ts = generated_at or datetime.now(UTC).isoformat()
    return {
        "library_version": LIBRARY_VERSION,
        "schema_bundle_version": "0.1.0",
        "pattern_count": len(entries),
        "unique_practice_count": len(practice_hashes),
        "pattern_entries": sorted(entries, key=lambda e: e["pattern_id"]),
        "pattern_hashes": all_pattern_hashes,
        "practice_ids": sorted(practice_hashes.keys()),
        "practice_hashes": practice_hashes,
        "generated_at": ts,
    }


def library_index_semantic_hash(index: dict[str, Any]) -> str:
    subset = {
        "library_version": index["library_version"],
        "schema_bundle_version": index["schema_bundle_version"],
        "pattern_count": index["pattern_count"],
        "unique_practice_count": index["unique_practice_count"],
        "pattern_entries": index["pattern_entries"],
        "pattern_hashes": index["pattern_hashes"],
        "practice_ids": index["practice_ids"],
        "practice_hashes": index["practice_hashes"],
    }
    payload = json.dumps(subset, sort_keys=True, separators=(",", ":"))
    return sha256_bytes(payload.encode("utf-8"))


def build_library_freeze_manifest(*, generated_at: str | None = None) -> dict[str, Any]:
    pilot_manifest = load_pilot_manifest()
    core_manifest = load_core_manifest()
    if pilot_manifest["bundle_hash"] != FROZEN_PILOT_BUNDLE_HASH:
        msg = "pilot bundle hash drift detected"
        raise RuntimeError(msg)
    if core_manifest["bundle_hash"] != FROZEN_CORE_BUNDLE_HASH:
        msg = "core bundle hash drift detected"
        raise RuntimeError(msg)

    pilot_map = load_pilot_source_support_map()
    core_map = load_core_source_support_map()
    overlap = build_overlap_matrix()
    index = build_library_index(generated_at=generated_at)

    all_patterns = load_pilot_patterns() + load_core_patterns()
    all_practices = load_pilot_practices() + load_core_practices()
    pilot_audits = load_pilot_audit_records()
    core_audits = load_core_audit_records()

    pattern_hashes = index["pattern_hashes"]
    practice_hashes = index["practice_hashes"]
    audit_hashes = {
        a["audit_id"]: audit_semantic_hash(a) for a in pilot_audits + core_audits
    }
    support_hashes = {
        "pilot": source_support_map_semantic_hash(pilot_map),
        "core": source_support_map_semantic_hash(core_map),
    }
    overlap_hash = overlap_matrix_semantic_hash(overlap)
    index_hash = library_index_semantic_hash(index)

    ts = generated_at or datetime.now(UTC).isoformat()
    manifest: dict[str, Any] = {
        "library_version": LIBRARY_VERSION,
        "status": "frozen_reviewed_library",
        "pattern_count": len(all_patterns),
        "unique_practice_count": len(practice_hashes),
        "practice_record_count": len(all_practices),
        "audit_record_count": len(pilot_audits) + len(core_audits),
        "pilot_bundle_hash": pilot_manifest["bundle_hash"],
        "core_bundle_hash": core_manifest["bundle_hash"],
        "schema_bundle_hash": FROZEN_SCHEMA_HASH,
        "catalog_bundle_hash": FROZEN_CATALOG_HASH,
        "library_index_hash": index_hash,
        "overlap_matrix_hash": overlap_hash,
        "pattern_hashes": pattern_hashes,
        "practice_hashes": practice_hashes,
        "source_support_hashes": support_hashes,
        "audit_hashes": audit_hashes,
        "accepted_limitations": ACCEPTED_LIMITATIONS,
        "deferred_patterns": DEFERRED_PATTERNS,
        "prohibited_maturity_values": PROHIBITED_MATURITY,
        "owner_decision": "accepted_as_read_only_knowledge_source",
        "runtime_authorized": False,
        "production_eligible": False,
        "generated_at": ts,
    }
    manifest["library_semantic_hash"] = library_semantic_hash(manifest)
    return manifest


def library_semantic_manifest_subset(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "library_version": manifest["library_version"],
        "status": manifest["status"],
        "pattern_count": manifest["pattern_count"],
        "unique_practice_count": manifest["unique_practice_count"],
        "pilot_bundle_hash": manifest["pilot_bundle_hash"],
        "core_bundle_hash": manifest["core_bundle_hash"],
        "schema_bundle_hash": manifest["schema_bundle_hash"],
        "catalog_bundle_hash": manifest["catalog_bundle_hash"],
        "library_index_hash": manifest["library_index_hash"],
        "overlap_matrix_hash": manifest["overlap_matrix_hash"],
        "pattern_hashes": manifest["pattern_hashes"],
        "practice_hashes": manifest["practice_hashes"],
        "source_support_hashes": manifest["source_support_hashes"],
        "audit_hashes": manifest["audit_hashes"],
        "runtime_authorized": manifest["runtime_authorized"],
        "production_eligible": manifest["production_eligible"],
        "owner_decision": manifest["owner_decision"],
    }


def library_semantic_hash(manifest: dict[str, Any]) -> str:
    payload = json.dumps(
        library_semantic_manifest_subset(manifest),
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256_bytes(payload.encode("utf-8"))


def is_valid_sha256(value: str) -> bool:
    if len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()
