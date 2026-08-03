"""Test helpers for SKILL-02.7 Positioning 0.1.0 package validation."""

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

PACKAGE_ROOT = (
    Path(__file__).resolve().parents[2] / "packages" / "skills" / "ms.skill.positioning"
)

CIM_URI = (
    "https://schemas.marketsynth.ai/customer-intelligence/0.1.0/"
    "customer-intelligence.schema.json"
)
CIM_BUNDLE_HASH = (
    "b13cc76eb8f6405d114a457a8a4bf12a4a5330d9a37bd0adcfd93f48353421ea"
)
MV_020_PKG_HASH = (
    "ec7c86ce0bc39b5481e336b7749de3cf087d47630be315c639897dd687568f7a"
)

FROZEN_PACKAGE_HASH: str | None = None

FORBIDDEN_OUTPUT_FIELDS = (
    "verdict",
    "final_offer",
    "offer",
    "offer_price",
    "campaign",
    "execution_status",
    "publication",
    "connector_result",
    "approval_granted",
)

OFFER_FORBIDDEN_FIELDS = (
    "package_name",
    "price",
    "discount",
    "guarantee",
    "bonus",
    "cta",
    "final_copy",
)

REQUIRED_PACKAGE_ENTRIES = (
    "SKILL.md",
    "manifest.yaml",
    "schemas/input.schema.json",
    "schemas/output.schema.json",
    "schemas/positioning_hypothesis.schema.json",
    "schemas/positioning_territory.schema.json",
    "schemas/message_hierarchy.schema.json",
    "schemas/positioning_risk.schema.json",
    "schemas/downstream_offer_input.schema.json",
    "tests/eval_manifest.yaml",
)


class MarketValidationVerdict(StrEnum):
    PROCEED = "proceed"
    PROCEED_WITH_CONDITIONS = "proceed_with_conditions"
    REVISE = "revise"
    DEFER = "defer"
    STOP = "stop"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class PositioningReadiness(StrEnum):
    READY = "ready_for_offer_design"
    PARTIAL = "partially_ready"
    EXPLORATORY = "exploratory_only"
    BLOCKED = "blocked"
    INSUFFICIENT = "insufficient_evidence"
    CONFLICTED = "conflicted"
    OUT_OF_SCOPE = "out_of_scope"


class OutputProvenance(BaseModel):
    skill_id: str
    skill_version: str
    source_cim_skill_id: str
    source_cim_skill_version: str
    source_cim_output_hash: str
    source_cim_document_hash: str
    source_competitor_skill_id: str
    source_competitor_skill_version: str
    source_competitor_output_hash: str
    source_market_validation_skill_id: str
    source_market_validation_skill_version: str
    source_market_validation_output_hash: str


class PositioningOutputFixture(BaseModel):
    positioning_analysis_id: str
    skill_id: str
    skill_version: str
    source_cim_reference: dict[str, Any]
    source_competitor_reference: dict[str, Any]
    source_market_validation_reference: dict[str, Any]
    market_validation_verdict_consumed: MarketValidationVerdict
    selected_segment_ids: list[str]
    positioning_territories: list[dict[str, Any]]
    positioning_hypotheses: list[dict[str, Any]]
    alternative_hypothesis_ids: list[str]
    blocked_hypothesis_ids: list[str]
    message_hierarchy: dict[str, Any]
    differentiation_summary: str
    reason_to_believe_requirements: list[str]
    proof_gaps: list[str]
    unsupported_claims: list[str]
    conditions_inherited: list[dict[str, Any]]
    blockers_inherited: list[dict[str, Any]]
    positioning_risks: list[dict[str, Any]]
    assumptions: list[dict[str, Any]]
    inferences: list[dict[str, Any]]
    unknowns: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    evidence_gaps: list[str]
    coverage: str
    evidence_quality: str
    research_status: str
    positioning_readiness: PositioningReadiness
    downstream_offer_inputs: list[dict[str, Any]]
    downstream_recommendation: str
    human_approval_required: bool
    provenance: OutputProvenance
    input_hash: str = Field(min_length=64, max_length=64)
    output_hash: str = Field(min_length=64, max_length=64)
    preferred_hypothesis_id: str | None = None
    approval_granted: bool | None = None

    @field_validator("skill_id")
    @classmethod
    def skill_id_must_match(cls, value: str) -> str:
        if value != "ms.skill.positioning":
            raise ValueError("skill_id must be ms.skill.positioning")
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


def validate_hypothesis_schema(data: Any) -> None:
    schema_validator("positioning_hypothesis.schema.json").validate(data)


def validate_territory_schema(data: Any) -> None:
    schema_validator("positioning_territory.schema.json").validate(data)


def validate_message_hierarchy_schema(data: Any) -> None:
    schema_validator("message_hierarchy.schema.json").validate(data)


def validate_risk_schema(data: Any) -> None:
    schema_validator("positioning_risk.schema.json").validate(data)


def validate_downstream_offer_input_schema(data: Any) -> None:
    schema_validator("downstream_offer_input.schema.json").validate(data)


def validate_input_semantics(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    cim = data.get("customer_intelligence_reference", {})
    if not cim.get("cim_document_hash"):
        errors.append("missing CIM document hash")
    if not cim.get("cim_schema_uri"):
        errors.append("missing CIM schema URI")
    version = cim.get("cim_version")
    if version and not str(version).startswith("0.1."):
        errors.append("unknown CIM version")
    ca = data.get("competitor_analysis_output", {})
    if not ca.get("source_output_hash"):
        errors.append("missing CA output hash")
    mv = data.get("market_validation_output", {})
    if not mv.get("source_output_hash"):
        errors.append("missing MV output hash")
    catalog = data.get("cim_claim_catalog", {})
    catalog_segments = set(catalog.get("segment_ids", []))
    for seg in data.get("selected_segment_ids", []):
        if seg not in catalog_segments:
            errors.append(f"unknown segment ID: {seg}")
    return errors


def _hypothesis_by_id(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {h["hypothesis_id"]: h for h in data.get("positioning_hypotheses", [])}


def _catalog_from_input(input_data: dict[str, Any] | None) -> dict[str, set[str]]:
    if not input_data:
        return {}
    catalog = input_data.get("cim_claim_catalog", {})
    return {
        "segment_ids": set(catalog.get("segment_ids", [])),
        "pain_point_ids": set(catalog.get("pain_point_ids", [])),
        "jtbd_ids": set(catalog.get("jtbd_ids", [])),
        "objection_ids": set(catalog.get("objection_ids", [])),
    }


def validate_output_semantics(
    data: dict[str, Any],
    *,
    input_data: dict[str, Any] | None = None,
    cim_catalog: dict[str, set[str]] | None = None,
) -> list[str]:
    errors: list[str] = []
    verdict = data.get("market_validation_verdict_consumed")
    readiness = data.get("positioning_readiness")
    hypotheses = _hypothesis_by_id(data)
    selected_segments = set(data.get("selected_segment_ids", []))
    cim_segments = set(data.get("source_cim_reference", {}).get("selected_segment_ids", []))
    unsupported = set(data.get("unsupported_claims", []))
    catalog = cim_catalog or _catalog_from_input(input_data)

    preferred_id = data.get("preferred_hypothesis_id")
    if preferred_id and preferred_id not in hypotheses:
        errors.append("preferred hypothesis ID must exist")

    for alt_id in data.get("alternative_hypothesis_ids", []):
        if alt_id not in hypotheses:
            errors.append(f"alternative hypothesis ID missing: {alt_id}")

    for blocked_id in data.get("blocked_hypothesis_ids", []):
        if blocked_id not in hypotheses:
            errors.append(f"blocked hypothesis ID missing: {blocked_id}")
        elif hypotheses[blocked_id].get("status") not in {"blocked", "rejected"}:
            errors.append("blocked IDs must reference blocked hypotheses")

    for seg in selected_segments:
        if seg not in cim_segments:
            errors.append(f"selected segment not in CIM reference: {seg}")

    for hyp in data.get("positioning_hypotheses", []):
        hyp_segments = set(hyp.get("target_segment_ids", []))
        if hyp_segments and not hyp_segments.issubset(selected_segments):
            errors.append("hypothesis segment IDs must be subset of selected segment IDs")
        pain_ref = hyp.get("primary_customer_problem_ref")
        if catalog.get("pain_point_ids") and pain_ref not in catalog["pain_point_ids"]:
            errors.append("unsupported customer pain introduction")
        jtbd_ref = hyp.get("primary_jtbd_ref")
        if jtbd_ref and catalog.get("jtbd_ids") and jtbd_ref not in catalog["jtbd_ids"]:
            errors.append("unsupported JTBD introduction")
        if hyp.get("status") == "recommended" and verdict == "stop":
            errors.append("recommended hypothesis prohibited when MV verdict is stop")
        if preferred_id == hyp.get("hypothesis_id") and not hyp.get("evidence_references"):
            errors.append("preferred hypothesis requires evidence references")
        ev_refs = hyp.get("evidence_references", [])
        has_competitor_ev = any(ref.startswith("src-") for ref in ev_refs)
        if hyp.get("differentiation_basis") and not has_competitor_ev:
            errors.append("differentiation requires competitor evidence")
        key_msg = hyp.get("key_message", "")
        if key_msg in unsupported:
            errors.append("unsupported claim as key message")

    if verdict == "insufficient_evidence":
        for hyp in data.get("positioning_hypotheses", []):
            if hyp.get("confidence") == "high":
                errors.append("high confidence with insufficient evidence")
        if readiness == PositioningReadiness.READY.value:
            errors.append("ready_for_offer_design with insufficient evidence")

    if (
        verdict in {"stop", "defer", "insufficient_evidence"}
        and readiness == PositioningReadiness.READY.value
    ):
        errors.append(f"ready_for_offer_design with {verdict}")

    if data.get("approval_granted") is True:
        errors.append("approval_granted prohibited")

    if "verdict" in data:
        errors.append("verdict field prohibited in positioning output")

    for field in ("final_offer", "offer_price", "campaign", "execution_status", "publication"):
        if field in data:
            errors.append(f"forbidden field: {field}")

    for offer_input in data.get("downstream_offer_inputs", []):
        hyp_id = offer_input.get("selected_positioning_hypothesis_id")
        if hyp_id and hyp_id not in hypotheses:
            errors.append("downstream offer input must reference valid hypothesis")
        for forbidden in OFFER_FORBIDDEN_FIELDS:
            if forbidden in offer_input:
                errors.append(f"offer field in downstream input: {forbidden}")

    for resp in data.get("message_hierarchy", {}).get("objection_responses", []):
        obj_ref = resp.get("objection_ref")
        if catalog.get("objection_ids") and obj_ref not in catalog["objection_ids"]:
            errors.append("unsupported objection introduction")
    if verdict == "stop" and data.get("downstream_recommendation") == "offer_builder":
        errors.append("downstream offer recommendation blocked on MV stop")

    return errors


def validate_output_fixture(
    data: Any,
    *,
    input_data: dict[str, Any] | None = None,
    cim_catalog: dict[str, set[str]] | None = None,
) -> PositioningOutputFixture:
    validate_output_schema(data)
    semantic_errors = validate_output_semantics(
        data, input_data=input_data, cim_catalog=cim_catalog
    )
    if semantic_errors:
        raise ValueError("; ".join(semantic_errors))
    return PositioningOutputFixture.model_validate(data)


def validate_output_fixture_schema_only(data: Any) -> PositioningOutputFixture:
    validate_output_schema(data)
    return PositioningOutputFixture.model_validate(data)


def package_structure_valid() -> bool:
    return all((PACKAGE_ROOT / entry).exists() for entry in REQUIRED_PACKAGE_ENTRIES)


def output_has_forbidden_fields(data: dict[str, Any]) -> list[str]:
    return [field for field in FORBIDDEN_OUTPUT_FIELDS if field in data]


def saas_catalog() -> dict[str, set[str]]:
    return {
        "segment_ids": {"seg-remote-eng"},
        "pain_point_ids": {"pain-seg-remote-eng"},
        "jtbd_ids": {"jtbd-seg-remote-eng"},
        "objection_ids": {"obj-seg-remote-eng"},
    }


def offer_builder_consumer_stub(consumer: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    if consumer.get("execution_authorized"):
        raise ValueError("offer consumer cannot receive execution authorization")
    if consumer.get("verdict_override_attempted"):
        raise ValueError("consumer cannot override MV verdict")
    return {
        "hypothesis_id": consumer.get("selected_hypothesis_id"),
        "segment_ids": consumer.get("selected_segment_ids"),
        "message_hierarchy": output.get("message_hierarchy"),
        "proof_requirements": consumer.get("proof_requirements"),
        "blockers": consumer.get("blockers_inherited"),
        "conditions": consumer.get("conditions_inherited"),
    }


def content_consumer_stub(consumer: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    if consumer.get("execution_authorized"):
        raise ValueError("content consumer cannot receive execution authorization")
    return {
        "hypothesis_id": consumer.get("selected_hypothesis_id"),
        "segment_ids": consumer.get("selected_segment_ids"),
        "message_hierarchy": output.get("message_hierarchy"),
    }


def copywriting_consumer_stub(consumer: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    return content_consumer_stub(consumer, output)


def launch_strategy_consumer_stub(consumer: dict[str, Any]) -> None:
    if consumer.get("execution_authorized"):
        raise ValueError("launch consumer cannot receive execution authorization")
    if consumer.get("launch_approved"):
        raise ValueError("launch consumer cannot treat positioning as launch approval")


def package_hash() -> str:
    global FROZEN_PACKAGE_HASH
    if FROZEN_PACKAGE_HASH is None:
        from app.skills.hashing import calculate_skill_package_hash

        FROZEN_PACKAGE_HASH = calculate_skill_package_hash(PACKAGE_ROOT)
    return FROZEN_PACKAGE_HASH
