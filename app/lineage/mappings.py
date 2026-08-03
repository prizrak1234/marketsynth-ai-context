"""Evidence mapping boundaries — no new persistence (SKILL-01.7)."""

from __future__ import annotations

from app.audit.contracts import AuditEvidenceReference
from app.connectors.contracts import ConnectorEvidenceDescriptor
from app.lineage.contracts import EvidenceLineageReference
from app.schemas.contracts import KnowledgeEvidenceRef
from app.skills.quarantine_contracts import QuarantineProvenanceRecord
from app.skills.validation_contracts import SkillPackageValidationReport

# Compatibility gaps documented for SKILL-01.8:
# - KnowledgeEvidenceRef expects durable source_uri; connector descriptors provide hashes only.
# - Quarantine provenance has no first-class KnowledgeEvidenceRef in KG subsystem yet.
# - Package validation report hash is used as locator, not persisted Evidence id.


def map_connector_evidence_to_lineage_reference(
    descriptor: ConnectorEvidenceDescriptor,
) -> EvidenceLineageReference:
    return EvidenceLineageReference(
        evidence_id=str(descriptor.evidence_id),
        source_system="connector_evidence_descriptor",
        input_hash=descriptor.input_hash,
        output_hash=descriptor.output_hash,
        provider_metadata_hash=descriptor.provider_metadata_hash,
        lineage_parent_ids=descriptor.lineage_parent_ids,
        external_reference_id=descriptor.external_reference_id,
    )


def map_audit_evidence_to_lineage_reference(
    reference: AuditEvidenceReference,
) -> EvidenceLineageReference:
    return EvidenceLineageReference(
        evidence_id=reference.evidence_id,
        source_system=reference.evidence_kind,
        input_hash=reference.input_hash,
        output_hash=reference.output_hash,
        provider_metadata_hash=reference.provider_metadata_hash,
        lineage_parent_ids=reference.lineage_parent_ids,
        external_reference_id=reference.external_reference_id,
    )


def map_lineage_reference_to_knowledge_evidence(
    reference: EvidenceLineageReference,
    *,
    source_uri: str | None = None,
) -> KnowledgeEvidenceRef:
    locator_parts = [
        part
        for part in (
            f"input={reference.input_hash}" if reference.input_hash else None,
            f"output={reference.output_hash}" if reference.output_hash else None,
            (
                f"provider={reference.provider_metadata_hash}"
                if reference.provider_metadata_hash
                else None
            ),
        )
        if part
    ]
    return KnowledgeEvidenceRef(
        evidence_id=reference.evidence_id,
        source_uri=source_uri,
        locator=";".join(locator_parts) if locator_parts else None,
        note=f"source_system={reference.source_system}",
    )


def map_package_validation_to_evidence_source_reference(
    report: SkillPackageValidationReport,
    *,
    report_hash: str,
) -> KnowledgeEvidenceRef:
    package_hash = report.package_hash or "unknown"
    return KnowledgeEvidenceRef(
        evidence_id=f"validation-source:{package_hash}",
        source_uri=f"skill-package://{report.skill_id}/{report.skill_version}",
        locator=f"validator={report.validator_version};report_hash={report_hash};package_hash={package_hash}",
        note="package_validation_report",
    )


def map_quarantine_provenance_to_evidence_reference(
    provenance: QuarantineProvenanceRecord,
) -> KnowledgeEvidenceRef:
    return KnowledgeEvidenceRef(
        evidence_id=f"quarantine-provenance:{provenance.import_id}",
        source_uri=f"quarantine-import://{provenance.import_id}",
        locator=(
            f"source_fingerprint={provenance.source_fingerprint};"
            f"materialized_hash={provenance.materialized_package_hash or 'unknown'}"
        ),
        note=f"source_type={provenance.source_type.value}",
    )
