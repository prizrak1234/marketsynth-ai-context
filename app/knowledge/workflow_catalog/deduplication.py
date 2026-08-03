"""Workflow deduplication into duplicate families."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any

from app.knowledge.workflow_catalog.contracts import DuplicateFamily, WorkflowTemplateRecord

SOURCE_ARCHIVE_ID = "arc-bots-knowledge-rar"


def _family_id(seed: str) -> str:
    return f"dup-{hashlib.sha256(seed.encode()).hexdigest()[:16]}"


def deduplication_diagnostics(
    templates: list[WorkflowTemplateRecord],
    *,
    topology_aware_by_id: dict[str, str] | None = None,
) -> dict[str, Any]:
    by_topology: dict[str, list[str]] = defaultdict(list)
    by_aware: dict[str, list[str]] = defaultdict(list)
    credential_only_candidates = 0
    sample_content_candidates = 0

    for template in templates:
        by_topology[template.topology_hash].append(template.workflow_template_id)
        aware = (topology_aware_by_id or {}).get(
            template.workflow_template_id,
            template.topology_hash,
        )
        by_aware[aware].append(template.workflow_template_id)

    topology_collisions = sum(1 for members in by_topology.values() if len(members) > 1)
    aware_collisions = sum(1 for members in by_aware.values() if len(members) > 1)

    for members_ids in by_topology.values():
        if len(members_ids) < 2:
            continue
        member_records = [t for t in templates if t.workflow_template_id in members_ids]
        cred_counts = {len(t.credential_references) for t in member_records}
        if len(cred_counts) > 1 and len({t.workflow_hash for t in member_records}) > 1:
            credential_only_candidates += 1
        name_set = {t.normalized_name.lower() for t in member_records}
        if len(name_set) == len(member_records) and len(member_records) > 1:
            sample_content_candidates += 1

    renamed_topology_families = sum(
        1
        for members in by_topology.values()
        if len(members) > 1
        and len({t.workflow_hash for t in templates if t.workflow_template_id in members}) > 1
    )

    return {
        "provider_neutral_topology_collisions": topology_collisions,
        "provider_aware_topology_collisions": aware_collisions,
        "renamed_topology_candidate_groups": renamed_topology_families,
        "credential_only_candidate_groups": credential_only_candidates,
        "sample_content_only_candidate_groups": sample_content_candidates,
        "reason_codes": [
            "exact_duplicate_removed_before_family_build",
            "renamed_topology_requires_same_neutral_hash_and_different_workflow_hash",
            "provider_swapped_requires_same_aware_hash_and_different_neutral_hash",
            "credential_only_not_merged_without_topology_and_hash_delta",
            "sample_content_only_not_merged_without_name_collision",
        ],
    }


def build_duplicate_families(
    templates: list[WorkflowTemplateRecord],
    *,
    topology_aware_by_id: dict[str, str] | None = None,
) -> list[DuplicateFamily]:
    by_workflow_hash: dict[str, list[WorkflowTemplateRecord]] = defaultdict(list)
    by_topology: dict[str, list[WorkflowTemplateRecord]] = defaultdict(list)
    by_aware: dict[str, list[WorkflowTemplateRecord]] = defaultdict(list)
    by_normalized_name: dict[str, list[WorkflowTemplateRecord]] = defaultdict(list)

    for template in templates:
        by_workflow_hash[template.workflow_hash].append(template)
        by_topology[template.topology_hash].append(template)
        aware = (topology_aware_by_id or {}).get(
            template.workflow_template_id,
            template.topology_hash,
        )
        by_aware[aware].append(template)
        by_normalized_name[template.normalized_name.lower()].append(template)

    families: list[DuplicateFamily] = []
    seen_members: set[str] = set()

    def _add_family(
        family_type: str,
        members: list[WorkflowTemplateRecord],
        differences: list[str],
        confidence: str,
        reason_code: str,
    ) -> None:
        ids = sorted({member.workflow_template_id for member in members})
        if len(ids) < 2:
            return
        if all(member_id in seen_members for member_id in ids):
            return
        canonical = ids[0]
        fam = DuplicateFamily(
            family_id=_family_id(":".join(ids)),
            family_type=family_type,  # type: ignore[arg-type]
            member_workflow_ids=ids,
            canonical_candidate_id=canonical,
            differences=[*differences, f"reason_code:{reason_code}"],
            confidence=confidence,
            manual_review_required=True,
            provenance={
                "source_type": "deduplication",
                "archive_id": SOURCE_ARCHIVE_ID,
                "program_phase": "KB-WPL-01.2.1",
            },
        )
        families.append(fam)
        seen_members.update(ids)

    for members in by_workflow_hash.values():
        _add_family(
            "exact_duplicate",
            members,
            ["identical workflow_hash"],
            "high",
            "exact_hash_match",
        )

    for members in by_topology.values():
        if len({member.workflow_hash for member in members}) > 1:
            _add_family(
                "renamed_topology",
                members,
                ["same provider-neutral topology_hash", "different workflow_hash"],
                "medium",
                "neutral_topology_collision",
            )

    for members in by_aware.values():
        topo_set = {member.topology_hash for member in members}
        if len(topo_set) > 1 and len(members) >= 2:
            _add_family(
                "provider_swapped",
                members,
                ["same provider-aware topology", "different neutral topology"],
                "medium",
                "aware_topology_collision",
            )

    for members in by_normalized_name.values():
        if len({member.workflow_hash for member in members}) > 1 and len(members) >= 2:
            _add_family(
                "translated_duplicate",
                members,
                ["same normalized_name", "different content hash"],
                "low",
                "normalized_name_collision",
            )

    for members in by_topology.values():
        if len(members) < 2:
            continue
        cred_counts = {len(member.credential_references) for member in members}
        if len(cred_counts) > 1 and len({member.workflow_hash for member in members}) > 1:
            _add_family(
                "credential_only_variant",
                members,
                ["topology match with credential count differences"],
                "low",
                "credential_only_delta",
            )

    return sorted(families, key=lambda item: item.family_id)


def deduplicate_exact(
    templates: list[WorkflowTemplateRecord],
) -> tuple[list[WorkflowTemplateRecord], int]:
    seen: set[str] = set()
    unique: list[WorkflowTemplateRecord] = []
    for template in templates:
        if template.workflow_hash in seen:
            continue
        seen.add(template.workflow_hash)
        unique.append(template)
    return unique, len(templates) - len(unique)
