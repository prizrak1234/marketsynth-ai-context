"""Build KB-WPL-01.2 / 01.2.1 workflow catalog from intake."""

from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from app.knowledge.workflow_catalog.candidate_eligibility import evaluate_candidate_eligibility
from app.knowledge.workflow_catalog.contracts import SOURCE_ARCHIVE_ID, WorkflowCatalogBundle
from app.knowledge.workflow_catalog.deduplication import (
    build_duplicate_families,
    deduplicate_exact,
    deduplication_diagnostics,
)
from app.knowledge.workflow_catalog.parser import parse_workflow_file
from app.knowledge.workflow_catalog.serialization import write_catalog_outputs

REPO = Path(__file__).resolve().parents[1]
INTAKE = REPO / ".tmp_archive_intake" / "bots-knowledge"
DOCS = REPO / "docs" / "research" / "workflow-catalog"


def _find_workflow_dir() -> Path:
    for candidate in INTAKE.rglob("воркфлоу"):
        if candidate.is_dir():
            return candidate
    for candidate in INTAKE.rglob("*"):
        if candidate.is_dir() and candidate.name.lower() in {"воркфлоу", "workflow", "workflows"}:
            return candidate
    return INTAKE


def _canonical_ids(families) -> set[str]:
    return {family.canonical_candidate_id for family in families}


def _apply_canonical_gate(
    templates: list,
    outcomes,
    families,
) -> list:
    canonical = _canonical_ids(families)
    family_by_member = {}
    for family in families:
        for member_id in family.member_workflow_ids:
            family_by_member[member_id] = family

    updated_templates = list(templates)
    for outcome in outcomes:
        record = outcome.record
        if record is None or outcome.diagnostics.classification is None:
            continue
        family = family_by_member.get(record.workflow_template_id)
        is_canonical = record.workflow_template_id in canonical or family is None
        if family and not is_canonical:
            evaluation = evaluate_candidate_eligibility(
                record,
                outcome.diagnostics.classification,
                is_unique_or_canonical=False,
            )
            outcome.diagnostics.candidate_evaluation = evaluation
            updated = record.model_copy(update={"adaptation_status": evaluation.adaptation_status})
            outcome.record = updated
            for index, template in enumerate(updated_templates):
                if template.workflow_template_id == updated.workflow_template_id:
                    updated_templates[index] = updated
                    break
    return updated_templates


def _security_summary(unique, outcomes) -> dict:
    finding_counts: Counter[str] = Counter()
    affected_by_type: Counter[str] = Counter()
    total_code_nodes = 0

    for outcome in outcomes:
        record = outcome.record
        if record is None:
            continue
        seen_types: set[str] = set()
        for finding in record.security_findings:
            finding_counts[finding.finding_type] += 1
            seen_types.add(finding.finding_type)
        for finding_type in seen_types:
            affected_by_type[finding_type] += 1
        total_code_nodes += outcome.diagnostics.code_node_count

    code_findings = finding_counts.get("code_node", 0)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "total_findings": sum(finding_counts.values()),
        "finding_counts": dict(finding_counts),
        "affected_workflows_by_finding_type": dict(affected_by_type),
        "code_nodes": {
            "total_findings": code_findings,
            "affected_workflows": sum(1 for r in unique if r.code_nodes),
            "total_detected_nodes": total_code_nodes,
        },
        "publication_nodes": {
            "total_findings": finding_counts.get("publication_node", 0),
            "affected_workflows": sum(1 for r in unique if r.publication_actions),
        },
        "credentials": {
            "total_findings": finding_counts.get("credential_reference", 0),
            "affected_workflows": sum(1 for r in unique if r.credential_references),
        },
        "shell_node_workflows": sum(1 for r in unique if r.shell_nodes),
        "billing_workflows": sum(1 for r in unique if r.billing_actions),
        "destructive_workflows": sum(1 for r in unique if r.destructive_actions),
    }


def build_catalog() -> dict:
    wf_dir = _find_workflow_dir()
    json_files = sorted(wf_dir.rglob("*.json"))
    outcomes = [parse_workflow_file(path) for path in json_files]
    records = [outcome.record for outcome in outcomes if outcome.record is not None]
    invalid = [outcome.invalid for outcome in outcomes if outcome.invalid is not None]
    assert records  # noqa: S101

    topology_aware = {
        outcome.record.workflow_template_id: outcome.diagnostics.topology_hash_aware
        for outcome in outcomes
        if outcome.record is not None
    }
    unique, dup_count = deduplicate_exact(records)
    unique_ids = {record.workflow_template_id for record in unique}
    unique_outcomes = [
        outcome
        for outcome in outcomes
        if outcome.record and outcome.record.workflow_template_id in unique_ids
    ]

    families = build_duplicate_families(unique, topology_aware_by_id=topology_aware)
    unique = _apply_canonical_gate(unique, unique_outcomes, families)
    dedup_diag = deduplication_diagnostics(unique, topology_aware_by_id=topology_aware)

    from tests.support.wpl_schema_validation import validate_workflow_template

    for record in unique:
        validate_workflow_template(json.loads(record.model_dump_json()))

    capability_counts: Counter[str] = Counter()
    provider_counts: Counter[str] = Counter()
    node_counts: Counter[str] = Counter()
    functional_counts: Counter[str] = Counter()
    priority_counts: Counter[str] = Counter()
    adaptation_counts: Counter[str] = Counter()
    approval_counts: Counter[str] = Counter()
    by_workflow: dict = {}

    for outcome in unique_outcomes:
        record = outcome.record
        assert record is not None
        classification = outcome.diagnostics.classification
        candidate = outcome.diagnostics.candidate_evaluation
        for category in record.categories:
            capability_counts[category] += 1
        for provider in record.providers:
            provider_counts[provider] += 1
        for node_type in record.node_types:
            node_counts[node_type] += 1
        for fn_class in outcome.diagnostics.functional_classes:
            functional_counts[fn_class] += 1
        priority = classification.commercial_priority if classification else "catalog_only"
        priority_counts[priority] += 1
        adaptation_counts[record.adaptation_status] += 1
        if classification and classification.approval_signal_strength != "none":
            approval_counts[classification.approval_signal_strength] += 1
        by_workflow[record.workflow_template_id] = {
            "commercial_priority": priority,
            "priority_confidence": classification.priority_confidence if classification else "low",
            "priority_reasons": classification.priority_reasons if classification else [],
            "classification_explanation": classification.explanation if classification else [],
            "capability_confidence": (
                classification.capability_confidence if classification else "low"
            ),
            "approval_signal_strength": (
                classification.approval_signal_strength if classification else "none"
            ),
            "approval_explanation": classification.approval_explanation if classification else [],
            "documentation_quality": outcome.diagnostics.documentation_quality,
            "documentation_signal": outcome.diagnostics.sticky_note_present,
            "functional_classes": outcome.diagnostics.functional_classes,
            "candidate_reasons": candidate.candidate_reasons if candidate else [],
            "candidate_blockers": candidate.candidate_blockers if candidate else [],
            "manual_audit_required": candidate.manual_audit_required if candidate else True,
            "topology_hash_aware": outcome.diagnostics.topology_hash_aware,
            "active_flag_source": outcome.diagnostics.active_flag,
            "node_count": outcome.diagnostics.node_count,
            "code_node_count": outcome.diagnostics.code_node_count,
        }

    security_summary = _security_summary(unique, unique_outcomes)
    statistics = {
        "generated_at": datetime.now(UTC).isoformat(),
        "program_phase": "KB-WPL-01.2.1",
        "json_discovered": len(json_files),
        "valid_exports": len(records),
        "unique_exports": len(unique),
        "exact_duplicates_removed": dup_count,
        "invalid_count": len(invalid),
        "valid_workflow_denominator": len(unique),
        "capability_distribution": dict(capability_counts),
        "provider_distribution": dict(provider_counts),
        "functional_class_distribution": dict(functional_counts),
        "node_type_distribution": dict(node_counts.most_common(50)),
        "commercial_priority_distribution": dict(priority_counts),
        "adaptation_status_distribution": dict(adaptation_counts),
        "approval_signal_distribution": dict(approval_counts),
        "duplicate_family_count": len(families),
        "deduplication_diagnostics": dedup_diag,
        "by_workflow": by_workflow,
    }

    bundle = WorkflowCatalogBundle(
        schema_version="0.1.0",
        schema_bundle_ref="packages/knowledge/workflow_patterns/0.1.0/",
        generated_at=datetime.now(UTC).isoformat(),
        source_archive_id=SOURCE_ARCHIVE_ID,
        json_discovered=len(json_files),
        valid_exports=len(records),
        invalid_count=len(invalid),
        templates=unique,
        invalid_files=[item for item in invalid if item is not None],
    )

    write_catalog_outputs(bundle, families, statistics, security_summary)
    _write_docs(
        bundle,
        statistics,
        security_summary,
        families,
        capability_counts,
        provider_counts,
        node_counts,
    )
    return {
        "json_discovered": len(json_files),
        "valid_exports": len(records),
        "unique": len(unique),
        "invalid": len(invalid),
        "families": len(families),
    }


def _write_docs(bundle, statistics, security_summary, families, cap, prov, nodes) -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "README.md").write_text(
        "# Workflow Catalog — KB-WPL-01.2.1\n\n"
        f"- JSON discovered: **{statistics['json_discovered']}**\n"
        f"- Valid exports: **{statistics['valid_exports']}**\n"
        f"- Unique catalog records: **{statistics['unique_exports']}**\n"
        f"- Invalid: **{statistics['invalid_count']}**\n"
        "Metadata only — no raw workflow bodies.\n",
        encoding="utf-8",
    )
    templates = bundle.templates
    index_lines = [
        f"- `{template.workflow_template_id}` — {template.original_name[:80]}"
        for template in templates[:60]
    ]
    (DOCS / "workflow-index.md").write_text(
        "# Workflow Index\n\n"
        + "\n".join(index_lines)
        + f"\n\n… total **{len(templates)}** unique records.\n",
        encoding="utf-8",
    )
    (DOCS / "capability-statistics.md").write_text(
        "# Capability Statistics\n\n"
        + "\n".join(f"- {key}: {value}" for key, value in cap.most_common())
        + "\n",
        encoding="utf-8",
    )
    (DOCS / "provider-statistics.md").write_text(
        "# Provider Statistics\n\n"
        "Integrated external providers only (no generic n8n node types).\n\n"
        + "\n".join(f"- {key}: {value}" for key, value in prov.most_common(30))
        + "\n",
        encoding="utf-8",
    )
    (DOCS / "node-statistics.md").write_text(
        "# Node Statistics\n\n"
        + "\n".join(f"- {key}: {value}" for key, value in nodes.most_common(30))
        + "\n",
        encoding="utf-8",
    )
    family_lines = [
        f"- `{family.family_id}` ({family.family_type}): {len(family.member_workflow_ids)} members"
        for family in families[:40]
    ]
    dedup = statistics.get("deduplication_diagnostics", {})
    neutral_collisions = dedup.get("provider_neutral_topology_collisions", 0)
    renamed_groups = dedup.get("renamed_topology_candidate_groups", 0)
    credential_groups = dedup.get("credential_only_candidate_groups", 0)
    (DOCS / "duplicate-families.md").write_text(
        "# Duplicate Families\n\n"
        f"Total families: **{len(families)}**\n\n"
        f"- Provider-neutral topology collisions: **{neutral_collisions}**\n"
        f"- Renamed-topology candidate groups: **{renamed_groups}**\n"
        f"- Credential-only candidate groups: **{credential_groups}**\n\n"
        + "\n".join(family_lines)
        + "\n",
        encoding="utf-8",
    )
    (DOCS / "security-findings.md").write_text(
        "# Security Findings\n\n"
        f"- Total findings: **{security_summary.get('total_findings', 0)}**\n"
        + "\n".join(
            f"- {key}: {value}" for key, value in security_summary.get("finding_counts", {}).items()
        )
        + "\n",
        encoding="utf-8",
    )
    for fname, pri in [
        ("P0-marketing-workflows.md", "P0_core_marketing"),
        ("P1-content-and-analytics.md", "P1_content_distribution_analytics"),
        ("engineering-reference.md", "engineering_reference"),
    ]:
        ids = [
            wf_id
            for wf_id, meta in statistics["by_workflow"].items()
            if meta.get("commercial_priority") == pri
        ]
        (DOCS / fname).write_text(f"# {fname}\n\nCount: **{len(ids)}**\n", encoding="utf-8")
    rejected = bundle.invalid_files
    (DOCS / "rejected-workflows.md").write_text(
        "# Rejected / Invalid Files\n\n"
        + "\n".join(f"- {record.file_name}: {record.error_type}" for record in rejected)
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    stats = build_catalog()
    print(stats)


if __name__ == "__main__":
    main()
