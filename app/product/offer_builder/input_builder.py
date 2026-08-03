"""Build Offer Builder input from persisted upstream artifacts."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from app.connectors.evidence import hash_payload
from app.product.offer_builder.bridge import BRIDGE_LIMITATIONS, BRIDGE_VERSION, bridge_metadata
from app.product.offer_builder.contracts import (
    CIM_VERSION,
    CLAIMS_SKILL,
    CLAIMS_VERSION,
    MARKET_VALIDATION_SKILL,
    MARKET_VALIDATION_VERSION,
    POSITIONING_SKILL,
    POSITIONING_VERSION,
    UpstreamBundle,
)
from app.schemas.contracts import BusinessIdeaValidationOutput, UpstreamSourceMode


def build_upstream_from_biv(
    *,
    owner_id: UUID,
    project_id: UUID,
    output: BusinessIdeaValidationOutput,
    accepted_conditions: list[str],
    mv_verdict: str,
) -> UpstreamBundle:
    """Governed upstream assembly from BIV output — bridged, not native Skill runs."""
    segment_ids: list[str] = []
    if output.audience_segmentation and output.audience_segmentation.segments:
        segment_ids = [seg.segment_id for seg in output.audience_segmentation.segments[:3]]
    if not segment_ids:
        segment_ids = ["seg-primary"]

    evidence_refs = [str(e.evidence_id) for e in output.evidence[:5]]
    claim_ids = [f"claim-{i}" for i, _ in enumerate(output.evidence[:3])] or ["claim-primary"]

    mv_payload = {
        "validation_id": str(output.business_verdict_id or uuid4()),
        "verdict": mv_verdict,
        "conditions": [{"text": c} for c in accepted_conditions],
        "blockers": [],
        "evidence_references": evidence_refs,
    }
    mv_hash = hash_payload(mv_payload)
    mv_bridge = bridge_metadata(
        output=output,
        artifact_type="market_validation",
        generated_from_fields=("verdict", "evidence", "accepted_conditions"),
    )

    positioning_payload = {
        "positioning_id": f"pos-{project_id}",
        "selected_hypothesis_id": "hyp-primary",
        "selected_segment_ids": segment_ids,
        "value_proposition": _first_finding(output, "value"),
        "differentiation": _first_finding(output, "differentiation"),
    }
    pos_hash = hash_payload(positioning_payload)
    pos_bridge = bridge_metadata(
        output=output,
        artifact_type="positioning",
        generated_from_fields=("findings", "audience_segmentation", "evidence"),
    )

    claims_payload = {
        "substantiation_id": f"claims-{project_id}",
        "substantiated_claim_ids": claim_ids,
        "unsupported_claim_ids": [],
        "limitations": list(output.limitations[:3]),
    }
    claims_hash = hash_payload(claims_payload)
    claims_bridge = bridge_metadata(
        output=output,
        artifact_type="claim_substantiation",
        generated_from_fields=("evidence", "limitations"),
    )

    cim_payload = {
        "cim_version": CIM_VERSION,
        "selected_segment_ids": segment_ids,
        "segment_labels": {
            sid: _segment_label(output, sid) for sid in segment_ids
        },
    }
    cim_hash = hash_payload(cim_payload)
    cim_bridge = bridge_metadata(
        output=output,
        artifact_type="cim",
        generated_from_fields=("audience_segmentation",),
    )

    inherited_conditions = tuple(
        {"text": c, "source": "market_validation"} for c in accepted_conditions
    )
    inherited_blockers = tuple(
        {"text": f"{r.title}: {r.description}", "source": "market_validation"}
        for r in output.risks[:3]
    )

    return UpstreamBundle(
        market_validation=_entry(
            owner_id=owner_id,
            project_id=project_id,
            skill_id=MARKET_VALIDATION_SKILL,
            skill_version=MARKET_VALIDATION_VERSION,
            output_hash=mv_hash,
            payload=mv_payload,
            bridge=mv_bridge,
        ),
        positioning=_entry(
            owner_id=owner_id,
            project_id=project_id,
            skill_id=POSITIONING_SKILL,
            skill_version=POSITIONING_VERSION,
            output_hash=pos_hash,
            payload=positioning_payload,
            bridge=pos_bridge,
        ),
        claim_substantiation=_entry(
            owner_id=owner_id,
            project_id=project_id,
            skill_id=CLAIMS_SKILL,
            skill_version=CLAIMS_VERSION,
            output_hash=claims_hash,
            payload=claims_payload,
            bridge=claims_bridge,
        ),
        cim=_entry(
            owner_id=owner_id,
            project_id=project_id,
            skill_id="ms.skill.customer_intelligence",
            skill_version=CIM_VERSION,
            output_hash=cim_hash,
            payload=cim_payload,
            bridge=cim_bridge,
            extra={
                "cim_version": CIM_VERSION,
                "selected_segment_ids": segment_ids,
            },
        ),
        mv_verdict=mv_verdict,
        positioning_hypothesis_id="hyp-primary",
        substantiated_claim_ids=tuple(claim_ids),
        inherited_conditions=inherited_conditions,
        inherited_blockers=inherited_blockers,
    )


def _entry(
    *,
    owner_id: UUID,
    project_id: UUID,
    skill_id: str,
    skill_version: str,
    output_hash: str,
    payload: dict[str, Any],
    bridge: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entry = {
        "artifact_id": str(uuid4()),
        "source_skill_id": skill_id,
        "source_skill_version": skill_version,
        "source_output_hash": output_hash,
        "source_status": "bridged",
        "source_mode": UpstreamSourceMode.BRIDGED_BIV_SNAPSHOT.value,
        "bridge_version": BRIDGE_VERSION,
        "source_biv_id": bridge.get("source_biv_id"),
        "source_biv_hash": bridge.get("source_biv_hash"),
        "generated_from_fields": bridge.get("generated_from_fields", []),
        "limitations": list(BRIDGE_LIMITATIONS),
        "replacement_required": True,
        "tenant_id": str(owner_id),
        "project_id": str(project_id),
        "payload": payload,
    }
    if extra:
        entry.update(extra)
    return entry


def build_skill_input(upstream: UpstreamBundle) -> dict[str, Any]:
    return {
        "source_cim_reference": _ref_from_cim(
            upstream.cim,
            upstream.cim.get("selected_segment_ids", []),
        ),
        "source_positioning_reference": _ref_from_skill(upstream.positioning),
        "source_market_validation_reference": _ref_from_skill(upstream.market_validation),
        "source_claim_substantiation_reference": _ref_from_skill(
            upstream.claim_substantiation
        ),
        "source_meaning_reference": _ref_from_skill(upstream.positioning),
        "market_validation_verdict": upstream.mv_verdict,
        "positioning_hypothesis_id": upstream.positioning_hypothesis_id,
        "substantiated_claim_ids": list(upstream.substantiated_claim_ids),
        "cim_claim_catalog": upstream.cim.get("payload", {}),
        "inherited_conditions": list(upstream.inherited_conditions),
        "inherited_blockers": list(upstream.inherited_blockers),
    }


def _ref_from_skill(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_skill_id": entry.get("source_skill_id"),
        "source_skill_version": entry.get("source_skill_version"),
        "source_output_hash": entry.get("source_output_hash"),
        "source_status": entry.get("source_status", "complete"),
        "source_mode": entry.get(
            "source_mode",
            UpstreamSourceMode.BRIDGED_BIV_SNAPSHOT.value,
        ),
        "bridge_version": entry.get("bridge_version"),
        "replacement_required": entry.get("replacement_required", False),
        "limitations": entry.get("limitations", []),
        "source_evidence_references": entry.get("payload", {}).get("evidence_references", []),
        "source_unknowns": [],
        "source_conflicts": [],
    }


def _ref_from_cim(entry: dict[str, Any], segment_ids: list[str]) -> dict[str, Any]:
    base = _ref_from_skill(entry)
    base["cim_schema_uri"] = (
        "https://schemas.marketsynth.ai/customer-intelligence/0.1.0/"
        "customer-intelligence.schema.json"
    )
    base["cim_version"] = entry.get("cim_version", CIM_VERSION)
    base["cim_document_hash"] = entry.get("source_output_hash")
    base["selected_segment_ids"] = segment_ids
    return base


def _first_finding(output: BusinessIdeaValidationOutput, keyword: str) -> str:
    for finding in output.findings:
        if keyword in finding.title.lower() or keyword in finding.statement.lower():
            return finding.statement[:500]
    if output.findings:
        return output.findings[0].statement[:500]
    return "Value proposition derived from validation research."


def _segment_label(output: BusinessIdeaValidationOutput, segment_id: str) -> str:
    if output.audience_segmentation:
        for seg in output.audience_segmentation.segments:
            if seg.segment_id == segment_id:
                return seg.label
    return segment_id
