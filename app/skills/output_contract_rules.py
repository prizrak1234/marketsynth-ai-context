"""Output contract taxonomy rules for Skill package output schema validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.schemas.contracts import (
    SkillContextReadiness,
    SkillEvidenceQuality,
    SkillExecutionStatus,
    SkillOutputContractType,
    SkillResearchCoverage,
    SkillResearchStatus,
    SkillValidationVerdict,
)

LINEAGE_FIELDS = ("skill_id", "skill_version")

FORBIDDEN_COMMERCIAL_VERDICT_VALUES = frozenset(
    {
        "proceed",
        "stop",
        "viable",
        "unviable",
        "proceed_with_conditions",
        "revise",
        "defer",
        "insufficient_evidence",
    }
)


@dataclass(frozen=True)
class OutputContractSpec:
    contract_type: SkillOutputContractType
    required_discriminators: tuple[str, ...]
    forbidden_discriminators: tuple[str, ...]
    enum_fields: dict[str, frozenset[str]]


OUTPUT_CONTRACT_SPECS: dict[SkillOutputContractType, OutputContractSpec] = {
    SkillOutputContractType.CONTEXT: OutputContractSpec(
        contract_type=SkillOutputContractType.CONTEXT,
        required_discriminators=("readiness",),
        forbidden_discriminators=(
            "verdict",
            "research_status",
            "evidence_quality",
            "coverage",
            "execution_status",
        ),
        enum_fields={
            "readiness": frozenset(member.value for member in SkillContextReadiness),
        },
    ),
    SkillOutputContractType.RESEARCH: OutputContractSpec(
        contract_type=SkillOutputContractType.RESEARCH,
        required_discriminators=(
            "research_status",
            "evidence_quality",
            "coverage",
            "evidence_gaps",
        ),
        forbidden_discriminators=("verdict", "readiness", "execution_status"),
        enum_fields={
            "research_status": frozenset(member.value for member in SkillResearchStatus),
            "evidence_quality": frozenset(member.value for member in SkillEvidenceQuality),
            "coverage": frozenset(member.value for member in SkillResearchCoverage),
        },
    ),
    SkillOutputContractType.DECISION: OutputContractSpec(
        contract_type=SkillOutputContractType.DECISION,
        required_discriminators=("verdict",),
        forbidden_discriminators=(
            "readiness",
            "research_status",
            "evidence_quality",
            "coverage",
            "execution_status",
        ),
        enum_fields={
            "verdict": frozenset(member.value for member in SkillValidationVerdict),
        },
    ),
    SkillOutputContractType.EXECUTION: OutputContractSpec(
        contract_type=SkillOutputContractType.EXECUTION,
        required_discriminators=("execution_status",),
        forbidden_discriminators=(
            "verdict",
            "readiness",
            "research_status",
            "evidence_quality",
            "coverage",
        ),
        enum_fields={
            "execution_status": frozenset(member.value for member in SkillExecutionStatus),
        },
    ),
}


def validate_output_contract_schema(
    schema: dict[str, Any],
    output_contract_type: SkillOutputContractType,
) -> list[str]:
    """Validate output JSON Schema against manifest output_contract_type rules."""
    errors: list[str] = []
    spec = OUTPUT_CONTRACT_SPECS.get(output_contract_type)
    if spec is None:
        return [f"Unknown output_contract_type: {output_contract_type}"]

    required = schema.get("required", [])
    if not isinstance(required, list):
        return ["Output schema required must be an array."]

    properties = schema.get("properties")
    if not isinstance(properties, dict):
        properties = {}

    for field in LINEAGE_FIELDS:
        if field not in required:
            errors.append(f"Output schema missing required lineage field: {field}")

    for discriminator in spec.required_discriminators:
        if discriminator not in required:
            errors.append(
                f"Output schema missing required {output_contract_type.value} "
                f"discriminator: {discriminator}"
            )

    for forbidden in spec.forbidden_discriminators:
        if forbidden in properties:
            errors.append(
                f"Output schema forbids {forbidden!r} for "
                f"output_contract_type={output_contract_type.value!r}."
            )

    for field_name, allowed_values in spec.enum_fields.items():
        if field_name not in spec.required_discriminators:
            continue
        field_schema = properties.get(field_name, {})
        if not isinstance(field_schema, dict):
            if field_name in required:
                errors.append(
                    f"Output schema discriminator {field_name!r} must define properties."
                )
            continue
        enum_values = field_schema.get("enum")
        if not isinstance(enum_values, list):
            errors.append(f"Output schema discriminator {field_name!r} must declare enum.")
            continue
        unknown = set(enum_values) - allowed_values
        if unknown:
            errors.append(
                f"Output schema {field_name!r} enum contains unknown values: "
                f"{sorted(unknown)}"
            )
        if set(enum_values) & FORBIDDEN_COMMERCIAL_VERDICT_VALUES and field_name != "verdict":
            errors.append(
                f"Output schema {field_name!r} must not use commercial verdict values."
            )

    verdict_schema = properties.get("verdict")
    if isinstance(verdict_schema, dict):
        verdict_enum = verdict_schema.get("enum")
        if (
            output_contract_type != SkillOutputContractType.DECISION
            and isinstance(verdict_enum, list)
            and verdict_enum
        ):
            errors.append(
                "Commercial verdict field is only permitted for decision output contracts."
            )

    return errors


__all__ = [
    "FORBIDDEN_COMMERCIAL_VERDICT_VALUES",
    "OUTPUT_CONTRACT_SPECS",
    "OutputContractSpec",
    "validate_output_contract_schema",
]
