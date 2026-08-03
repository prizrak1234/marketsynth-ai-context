"""Shared test helpers for ARCHIVE-MKT-01 native skill packages."""

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

REPO_ROOT = Path(__file__).resolve().parents[2]

CIM_BUNDLE_HASH = "b13cc76eb8f6405d114a457a8a4bf12a4a5330d9a37bd0adcfd93f48353421ea"
POS_PKG_HASH = "cbd8283f4addaa9c8496504a9c6dbccd580e8ca317b2cf86bf628be6557e8da6"
MV_020_PKG_HASH = "ec7c86ce0bc39b5481e336b7749de3cf087d47630be315c639897dd687568f7a"
SEG = "seg-remote-eng"

PACKAGE_HASHES = {
    "ms.skill.customer_interview_design": (
        "e9e3b3f213e04e8a455285bb2f6c7aaf6f9856ae2a8d9738e5970bd98a92e8f2"
    ),
    "ms.skill.customer_meaning_extraction": (
        "acc0082a88d867f340e14ef9fc5a5590c57f3799b4f29016b97662c39f97d771"
    ),
    "ms.skill.claim_substantiation": (
        "faad9e2f23e1cc318d3aefa56e4943188b8204751882af870420da70016583b4"
    ),
    "ms.skill.offer_builder": (
        "b637c3920066953f3080c8dc3e7c58bc08dc95138a85c545cac04d80a04d02f4"
    ),
}

PROHIBITED_PHRASES = (
    "100% guaranteed income",
    "100% safety",
    "technology cannot fail",
    "guaranteed income",
)


class MarketValidationVerdict(StrEnum):
    PROCEED = "proceed"
    PROCEED_WITH_CONDITIONS = "proceed_with_conditions"
    REVISE = "revise"
    DEFER = "defer"
    STOP = "stop"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


def package_root(skill_id: str) -> Path:
    return REPO_ROOT / "packages" / "skills" / skill_id


def load_json_fixture(skill_id: str, relative_path: str) -> Any:
    return json.loads((package_root(skill_id) / relative_path).read_text(encoding="utf-8"))


def read_manifest_text(skill_id: str) -> str:
    return (package_root(skill_id) / "manifest.yaml").read_text(encoding="utf-8")


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

    def add(uri: str, resource: Resource[Any]) -> None:
        if uri not in seen:
            seen.add(uri)
            resources.append((uri, resource))

    for name, contents in parsed.items():
        resource = Resource.from_contents(contents)
        add(f"schemas/{name}", resource)
        schema_id = contents.get("$id")
        if isinstance(schema_id, str):
            add(schema_id, resource)
        for other_id in (
            item.get("$id") for item in parsed.values() if isinstance(item.get("$id"), str)
        ):
            add(urljoin(other_id, f"schemas/{name}"), resource)
    return Registry().with_resources(resources)


def schema_validator(skill_id: str, schema_name: str) -> Draft202012Validator:
    root = package_root(skill_id)
    schema = json.loads((root / "schemas" / schema_name).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=_schema_registry(root))


def saas_catalog() -> dict[str, set[str]]:
    return {
        "segment_ids": {SEG},
        "pain_point_ids": {"pain-seg-remote-eng"},
        "jtbd_ids": {"jtbd-seg-remote-eng"},
        "objection_ids": {"obj-seg-remote-eng"},
    }


def validate_interview_output_semantics(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if "respondent_answers" in data:
        errors.append("no invented answers")
    if "verdict" in data:
        errors.append("no viability verdict")
    for key in ("final_offer", "offer", "positioning", "approved_claim"):
        if key in data:
            errors.append(f"forbidden field: {key}")
    for q in data.get("questions", []):
        if q.get("expected_evidence_type") != "user_statement":
            pass  # allowed types vary
        if "client will 100%" in q.get("question_text", "").lower():
            errors.append("no 100% agree assumption in question")
    cim_segments = set(data.get("cim_reference", {}).get("selected_segment_ids", []))
    for seg in data.get("selected_segment_ids", []):
        if seg not in cim_segments:
            errors.append("CIM segment IDs must be preserved")
    return errors


def validate_meaning_output_semantics(
    data: dict[str, Any],
    *,
    cim_catalog: dict[str, set[str]] | None = None,
) -> list[str]:
    errors: list[str] = []
    catalog = cim_catalog or saas_catalog()
    cim_segments = set(data.get("source_cim_reference", {}).get("selected_segment_ids", []))
    for meaning in data.get("customer_meanings", []):
        for seg in meaning.get("selected_segment_ids", []):
            if seg not in catalog["segment_ids"] and seg not in cim_segments:
                errors.append("no new CIM segment invented")
    for dtb in data.get("desire_to_benefit_maps", []):
        if dtb.get("satisfaction_status") == "supported" and not dtb.get("evidence_references"):
            errors.append("unsupported desire marked supported")
        if (
            dtb.get("satisfaction_status") == "partially_supported"
            and dtb.get("confidence") == "high"
        ):
            pass  # allowed
    for forbidden in ("final_offer", "approved_claim", "verdict", "approval_granted"):
        if forbidden in data:
            errors.append(f"forbidden: {forbidden}")
    for pc in data.get("promise_candidates", []):
        stmt = pc.get("proposed_statement", "")
        if "guarantee" in stmt.lower() and pc.get("substantiation_status") == "supported":
            errors.append("regulated promise requires review")
    return errors


def validate_substantiation_semantics(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for assessment in data.get("claim_assessments", []):
        stmt = assessment.get("original_statement", "")
        status = assessment.get("substantiation_status")
        for phrase in PROHIBITED_PHRASES:
            if phrase.lower() in stmt.lower() and status != "prohibited":
                errors.append(f"prohibited claim not rejected: {phrase}")
        if status == "supported" and not assessment.get("evidence_references"):
            errors.append("supported claim requires evidence")
    for rr in data.get("risk_reversal_candidates", []):
        if rr.get("proves_outcome") is True:
            errors.append("guarantee does not prove result")
    return errors


def validate_offer_output_semantics(
    data: dict[str, Any],
    *,
    mv_verdict: str = "proceed",
    substantiated_claim_ids: set[str] | None = None,
    cim_catalog: dict[str, set[str]] | None = None,
) -> list[str]:
    errors: list[str] = []
    catalog = cim_catalog or saas_catalog()
    claims = substantiated_claim_ids or {"claim-async-1"}
    readiness = data.get("offer_readiness")
    preferred_id = data.get("preferred_offer_id")
    cim_segments = set(data.get("source_cim_reference", {}).get("selected_segment_ids", []))

    for offer in data.get("offer_candidates", []):
        for seg in offer.get("selected_segment_ids", []):
            if seg not in catalog["segment_ids"] and seg not in cim_segments:
                errors.append("Offer segment must exist in CIM")
        hyp = offer.get("positioning_hypothesis_id")
        if not hyp:
            errors.append("Offer references positioning hypothesis")
        for cref in offer.get("claim_references", []):
            if (
                cref not in claims
                and cref not in data.get("unsupported_claims_excluded", [])
                and offer.get("status") in {"preferred", "viable_alternative"}
            ):
                errors.append("unsupported claim cannot be used in viable offer")
        promise = offer.get("offer_promise", "")
        for phrase in PROHIBITED_PHRASES:
            if phrase.lower() in promise.lower():
                errors.append(f"prohibited promise in offer: {phrase}")
        rr = offer.get("risk_reversal", {})
        if rr.get("proves_outcome") is True:
            errors.append("guarantee does not imply outcome proof")
        ttv = offer.get("time_to_value", {})
        if ttv and not ttv.get("evidence_references") and not ttv.get("is_assumption"):
            errors.append("time-to-value requires evidence or assumption marker")
        for pj in offer.get("price_justification", []):
            if pj.get("justification_type") in {"lower_total_cost", "faster_outcome"} and (
                not pj.get("comparison_basis") and not pj.get("is_assumption")
            ):
                errors.append("price-saving claim requires comparison basis")

    if mv_verdict == "stop":
        if preferred_id:
            errors.append("preferred Offer cannot exist under MV stop")
        for offer in data.get("offer_candidates", []):
            if offer.get("status") == "preferred":
                errors.append("preferred status offer under MV stop")
        if readiness == "ready_for_owner_review":
            errors.append("MV stop blocks ready_for_owner_review")
    if mv_verdict == "defer" and readiness == "ready_for_owner_review":
        errors.append("MV defer produces exploratory only")
    if readiness == "ready_for_owner_review" and data.get("approval_granted"):
        errors.append("offer readiness does not equal approval")

    forbidden_exec = (
        "campaign",
        "execution_status",
        "publication",
        "approval_granted",
        "connector_result",
    )
    for forbidden in forbidden_exec:
        if forbidden in data:
            errors.append(f"forbidden execution field: {forbidden}")

    if not data.get("human_approval_required"):
        errors.append("human approval required")

    return errors


class InterviewOutput(BaseModel):
    interview_guide_id: str
    skill_id: str
    skill_version: str
    selected_segment_ids: list[str]
    questions: list[dict[str, Any]]
    human_review_required: bool
    input_hash: str = Field(min_length=64, max_length=64)
    output_hash: str = Field(min_length=64, max_length=64)

    @field_validator("skill_id")
    @classmethod
    def check_skill(cls, v: str) -> str:
        if v != "ms.skill.customer_interview_design":
            raise ValueError("wrong skill_id")
        return v

    model_config = {"extra": "forbid"}


def package_hash(skill_id: str) -> str:
    from app.skills.hashing import calculate_skill_package_hash

    return calculate_skill_package_hash(package_root(skill_id))
