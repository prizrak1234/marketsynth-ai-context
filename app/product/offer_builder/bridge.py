"""Bridged upstream snapshot metadata (PRODUCT-01.1)."""

from __future__ import annotations

from typing import Any

from app.connectors.evidence import hash_payload
from app.schemas.contracts import BusinessIdeaValidationOutput, UpstreamSourceMode

BRIDGE_VERSION = "product-01-biv-bridge-v1"

BRIDGE_LIMITATIONS = (
    "Synthesized from Business Idea Validation output — not a native Skill execution.",
    "Positioning, claims substantiation and CIM require dedicated Skill runtimes.",
)


def biv_output_hash(output: BusinessIdeaValidationOutput) -> str:
    return hash_payload(output.model_dump(mode="json"))


def bridge_metadata(
    *,
    output: BusinessIdeaValidationOutput,
    artifact_type: str,
    generated_from_fields: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "source_mode": UpstreamSourceMode.BRIDGED_BIV_SNAPSHOT.value,
        "bridge_version": BRIDGE_VERSION,
        "source_biv_id": str(output.business_verdict_id or ""),
        "source_biv_hash": biv_output_hash(output),
        "generated_from_fields": list(generated_from_fields),
        "limitations": list(BRIDGE_LIMITATIONS),
        "replacement_required": True,
        "artifact_type": artifact_type,
    }


def native_metadata(*, artifact_type: str) -> dict[str, Any]:
    return {
        "source_mode": UpstreamSourceMode.NATIVE_SKILL_OUTPUT.value,
        "bridge_version": None,
        "source_biv_id": None,
        "source_biv_hash": None,
        "generated_from_fields": [],
        "limitations": [],
        "replacement_required": False,
        "artifact_type": artifact_type,
    }
