"""Test helpers for SKILL-02.6B Market Validation 0.2.0 package validation."""

from __future__ import annotations

import json
import re
from enum import StrEnum
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from jsonschema import Draft202012Validator
from pydantic import BaseModel, Field, field_validator
from referencing import Registry, Resource

MV_ROOT = (
    Path(__file__).resolve().parents[2]
    / "packages"
    / "skills"
    / "ms.skill.market_validation"
)
PACKAGE_ROOT = MV_ROOT / "0.2.0"

CIM_URI = (
    "https://schemas.marketsynth.ai/customer-intelligence/0.1.0/"
    "customer-intelligence.schema.json"
)
CIM_BUNDLE_HASH = (
    "b13cc76eb8f6405d114a457a8a4bf12a4a5330d9a37bd0adcfd93f48353421ea"
)

FROZEN_MV_010_HASH = (
    "6c53b5b972e5de900a135b891d8fbbd1641cdb5bf04bb171f83d5023344b8133"
)
FROZEN_PACKAGE_HASH: str | None = None

FORBIDDEN_OUTPUT_FIELDS = (
    "positioning",
    "positioning_statement",
    "final_offer",
    "offer",
    "campaign",
    "launch_execution",
    "execution_status",
    "publication",
    "connector_result",
    "advertising_plan",
)

REQUIRED_PACKAGE_ENTRIES = (
    "SKILL.md",
    "manifest.yaml",
    "schemas/input.schema.json",
    "schemas/output.schema.json",
    "schemas/decision_readiness.schema.json",
    "schemas/decision_dimension.schema.json",
    "schemas/hard_blocker.schema.json",
    "schemas/validation_condition.schema.json",
    "schemas/validation_risk.schema.json",
    "tests/eval_manifest.yaml",
)


class MarketValidationVerdict(StrEnum):
    PROCEED = "proceed"
    PROCEED_WITH_CONDITIONS = "proceed_with_conditions"
    REVISE = "revise"
    DEFER = "defer"
    STOP = "stop"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class OutputProvenance(BaseModel):
    skill_id: str
    skill_version: str
    generated_at: str | None = None
    methodology_ref: str | None = None
    source_context_skill_id: str | None = None
    source_context_skill_version: str | None = None
    source_context_output_hash: str | None = None
    source_research_skill_id: str | None = None
    source_research_skill_version: str | None = None
    source_research_output_hash: str | None = None
    source_competitor_skill_id: str | None = None
    source_competitor_skill_version: str | None = None
    source_competitor_output_hash: str | None = None
    source_cim_skill_id: str | None = None
    source_cim_skill_version: str | None = None
    source_cim_output_hash: str | None = None


class MarketValidationOutputFixture(BaseModel):
    validation_id: str
    skill_id: str
    skill_version: str
    source_context_reference: dict[str, Any]
    source_research_reference: dict[str, Any]
    source_competitor_reference: dict[str, Any]
    source_cim_reference: dict[str, Any]
    decision_readiness: dict[str, Any]
    verdict: MarketValidationVerdict
    verdict_confidence: str
    executive_summary: str
    decision_dimensions: list[dict[str, Any]]
    supporting_evidence: list[dict[str, Any]]
    contradictory_evidence: list[dict[str, Any]]
    assumptions: list[dict[str, Any]]
    inferences: list[dict[str, Any]]
    unknowns: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    evidence_gaps: list[str]
    critical_risks: list[dict[str, Any]]
    noncritical_risks: list[dict[str, Any]]
    conditions: list[dict[str, Any]]
    blockers: list[dict[str, Any]]
    required_changes: list[str]
    next_validation_steps: list[str]
    recommended_next_stage: str
    human_approval_required: bool
    provenance: OutputProvenance
    input_hash: str = Field(min_length=64, max_length=64)
    output_hash: str = Field(min_length=64, max_length=64)
    defer_reason: str | None = None
    approval_granted: bool | None = None

    @field_validator("skill_id")
    @classmethod
    def skill_id_must_match(cls, value: str) -> str:
        if value != "ms.skill.market_validation":
            raise ValueError("skill_id must be ms.skill.market_validation")
        return value

    model_config = {"extra": "forbid"}


def load_json_fixture(relative_path: str) -> Any:
    return json.loads((PACKAGE_ROOT / relative_path).read_text(encoding="utf-8"))


def read_manifest_text() -> str:
    return (PACKAGE_ROOT / "manifest.yaml").read_text(encoding="utf-8")


def parse_manifest_scalar(text: str, key: str) -> str | None:
    pattern = rf"^{re.escape(key)}:\s*(.+?)\s*$"
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        return None
    value = match.group(1).strip()
    if value.startswith('"') or value.startswith("'"):
        return value.strip("\"'")
    return value


def _schema_registry(root: Path) -> Registry:
    schema_dir = root / "schemas"
    parsed: dict[str, dict[str, Any]] = {}
    for path in sorted(schema_dir.glob("*.json")):
        parsed[path.name] = json.loads(path.read_text(encoding="utf-8"))

    resources: list[tuple[str, Resource[Any]]] = []
    seen: set[str] = set()

    def _add(uri: str, resource: Resource[Any]) -> None:
        if uri not in seen:
            seen.add(uri)
            resources.append((uri, resource))

    for name, contents in parsed.items():
        resource = Resource.from_contents(contents)
        _add(f"schemas/{name}", resource)
        schema_id = contents.get("$id")
        if isinstance(schema_id, str):
            _add(schema_id, resource)
        for other_id in (
            item.get("$id") for item in parsed.values() if isinstance(item.get("$id"), str)
        ):
            _add(urljoin(other_id, f"schemas/{name}"), resource)
    return Registry().with_resources(resources)


def schema_validator(schema_name: str, root: Path | None = None) -> Draft202012Validator:
    base = root or PACKAGE_ROOT
    schema = json.loads((base / "schemas" / schema_name).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=_schema_registry(base))


def validate_input_schema(data: Any) -> None:
    schema_validator("input.schema.json").validate(data)


def validate_output_schema(data: Any) -> None:
    schema_validator("output.schema.json").validate(data)


def validate_readiness_schema(data: Any) -> None:
    schema_validator("decision_readiness.schema.json").validate(data)


def validate_dimension_schema(data: Any) -> None:
    schema_validator("decision_dimension.schema.json").validate(data)


def validate_blocker_schema(data: Any) -> None:
    schema_validator("hard_blocker.schema.json").validate(data)


def validate_condition_schema(data: Any) -> None:
    schema_validator("validation_condition.schema.json").validate(data)


def validate_risk_schema(data: Any) -> None:
    schema_validator("validation_risk.schema.json").validate(data)


def validate_output_semantics(data: dict[str, Any]) -> list[str]:
    """Return semantic violation messages; empty list means valid."""
    errors: list[str] = []
    verdict = data.get("verdict")
    readiness = data.get("decision_readiness", {}).get("readiness")
    blockers = data.get("blockers", [])
    critical_blockers = [
        b
        for b in blockers
        if b.get("blocking") and b.get("severity") == "critical"
    ]

    if verdict == "proceed":
        if critical_blockers:
            errors.append("proceed with critical blocker")
        if readiness in {"insufficient_evidence", "conflicted", "out_of_scope"}:
            errors.append("proceed with insufficient readiness")
        if not data.get("supporting_evidence"):
            errors.append("proceed without supporting evidence")
        if not data.get("source_cim_reference"):
            errors.append("proceed without CIM reference")
        for dim in data.get("decision_dimensions", []):
            if dim.get("status") == "blocking":
                errors.append("proceed with blocking dimension")

    if verdict == "proceed_with_conditions" and not data.get("conditions"):
        errors.append("proceed_with_conditions without conditions")

    if verdict == "revise" and not data.get("required_changes"):
        errors.append("revise without required_changes")

    if verdict == "defer" and not data.get("defer_reason"):
        errors.append("defer without defer_reason")

    if verdict == "stop":
        blocking = [b for b in blockers if b.get("blocking")]
        if not blocking:
            errors.append("stop without blocking hard blocker")
        elif all(not b.get("evidence_references") for b in blocking):
            supporting = data.get("supporting_evidence", [])
            if supporting and all(item.get("trace_type") == "inference" for item in supporting):
                errors.append("stop based only on inference")

    if verdict == "insufficient_evidence" and not data.get("evidence_gaps"):
        errors.append("insufficient_evidence without evidence_gaps")

    if data.get("verdict_confidence") == "high":
        prov = data.get("provenance", {})
        required = (
            "source_context_output_hash",
            "source_research_output_hash",
            "source_competitor_output_hash",
            "source_cim_output_hash",
        )
        if any(not prov.get(key) for key in required):
            errors.append("high confidence without critical provenance")

    if data.get("approval_granted") is True:
        errors.append("approval_granted must not be true in skill output")

    return errors


def validate_output_fixture(data: Any) -> MarketValidationOutputFixture:
    validate_output_schema(data)
    semantic_errors = validate_output_semantics(data)
    if semantic_errors:
        raise ValueError("; ".join(semantic_errors))
    return MarketValidationOutputFixture.model_validate(data)


def validate_output_fixture_schema_only(data: Any) -> MarketValidationOutputFixture:
    validate_output_schema(data)
    return MarketValidationOutputFixture.model_validate(data)


def package_structure_valid() -> bool:
    return all((PACKAGE_ROOT / entry).exists() for entry in REQUIRED_PACKAGE_ENTRIES)


def output_has_forbidden_fields(data: dict[str, Any]) -> list[str]:
    return [field for field in FORBIDDEN_OUTPUT_FIELDS if field in data]


def positioning_consumer_reads_mv(
    consumer: dict[str, Any], output: dict[str, Any]
) -> dict[str, Any]:
    if output.get("verdict") == "stop" and consumer.get("verdict_consumed") == "proceed":
        raise ValueError("positioning cannot reinterpret stop as proceed")
    return {
        "segment_ids": consumer.get("selected_segment_ids", []),
        "conditions": consumer.get("conditions_acknowledged", []),
        "blockers_ignored": consumer.get("blockers_ignored", []),
    }


def offer_consumer_respects_blockers(consumer: dict[str, Any]) -> None:
    if consumer.get("blockers_ignored"):
        raise ValueError("offer consumer cannot ignore blockers")
    if consumer.get("execution_authorized"):
        raise ValueError("offer consumer cannot treat blocked state as authorized")


def package_hash() -> str:
    global FROZEN_PACKAGE_HASH
    if FROZEN_PACKAGE_HASH is None:
        from app.skills.hashing import calculate_skill_package_hash

        FROZEN_PACKAGE_HASH = calculate_skill_package_hash(PACKAGE_ROOT)
    return FROZEN_PACKAGE_HASH


__all__ = [
    "CIM_BUNDLE_HASH",
    "CIM_URI",
    "FROZEN_MV_010_HASH",
    "FROZEN_PACKAGE_HASH",
    "FORBIDDEN_OUTPUT_FIELDS",
    "MV_ROOT",
    "PACKAGE_ROOT",
    "MarketValidationOutputFixture",
    "MarketValidationVerdict",
    "load_json_fixture",
    "offer_consumer_respects_blockers",
    "output_has_forbidden_fields",
    "package_hash",
    "package_structure_valid",
    "parse_manifest_scalar",
    "positioning_consumer_reads_mv",
    "read_manifest_text",
    "validate_blocker_schema",
    "validate_condition_schema",
    "validate_dimension_schema",
    "validate_input_schema",
    "validate_output_fixture",
    "validate_output_fixture_schema_only",
    "validate_output_schema",
    "validate_output_semantics",
    "validate_readiness_schema",
    "validate_risk_schema",
]
