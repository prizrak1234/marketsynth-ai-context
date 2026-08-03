"""Test helpers for SKILL-02.4 ICP & Segmentation package validation."""

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
    Path(__file__).resolve().parents[2]
    / "packages"
    / "skills"
    / "ms.skill.icp_segmentation"
)

CA_ROOT = (
    Path(__file__).resolve().parents[2]
    / "packages"
    / "skills"
    / "ms.skill.competitor_analysis"
)

PMC_020_ROOT = (
    Path(__file__).resolve().parents[2]
    / "packages"
    / "skills"
    / "ms.skill.product_marketing_context"
    / "0.2.0"
)

MR_ROOT = (
    Path(__file__).resolve().parents[2]
    / "packages"
    / "skills"
    / "ms.skill.market_research"
)

FROZEN_PMC_010_HASH = (
    "5e3dfc1bfc48c56d33951006c3adcf80b4d53ad246e96669d1d32014934cc230"
)
FROZEN_MV_HASH = (
    "6c53b5b972e5de900a135b891d8fbbd1641cdb5bf04bb171f83d5023344b8133"
)
FROZEN_PMC_020_HASH = (
    "08bf9d55a261da52a8659f5aa6f06c3f9a63f13f06a21aea5b2416b10a381eaa"
)
FROZEN_CA_HASH = (
    "14903c8744b57c472bf09875a41d4b825f175c5cb8ae55eecfdce1829a48cde0"
)

FROZEN_PACKAGE_HASH: str | None = (
    "075a4f1989a9050614babec004dda54a420d7f7bd717d9ac7e8a34b41e8ae71a"
)

REQUIRED_PACKAGE_ENTRIES = (
    "SKILL.md",
    "manifest.yaml",
    "schemas/input.schema.json",
    "schemas/output.schema.json",
    "schemas/customer_intelligence.schema.json",
    "schemas/customer_segment.schema.json",
    "schemas/job_to_be_done.schema.json",
    "schemas/customer_claim.schema.json",
    "schemas/decision_role.schema.json",
    "schemas/priority_assessment.schema.json",
    "schemas/segment_conflict.schema.json",
    "tests/eval_manifest.yaml",
)

MKG_ENTITY_MAPPINGS = {
    "CustomerIntelligenceDocument": "customer_intelligence",
    "CustomerSegment": "segment",
    "JobToBeDone": "job",
    "PainPoint": "pain",
    "DesiredOutcome": "outcome",
    "BuyingTrigger": "trigger",
    "BuyingBarrier": "barrier",
    "Objection": "objection",
    "DecisionRole": "decision_role",
    "TrustDriver": "trust_driver",
    "EvidenceReference": "evidence",
    "CompetitorOverlap": "competitor_relationship",
}

MKG_RELATION_EXAMPLES = [
    "segment HAS_JOB job",
    "segment HAS_PAIN pain",
    "segment SEEKS_OUTCOME outcome",
    "segment TRIGGERED_BY trigger",
    "segment BLOCKED_BY barrier",
    "segment HAS_OBJECTION objection",
    "role INFLUENCES segment_buying_process",
    "segment TRUSTS proof_or_driver",
    "segment OVERLAPS_WITH competitor",
    "claim SUPPORTED_BY evidence",
]


class ResearchStatus(StrEnum):
    COMPLETE = "complete"
    PARTIALLY_COMPLETE = "partially_complete"
    INSUFFICIENT_SOURCES = "insufficient_sources"
    CONFLICTED = "conflicted"
    OUT_OF_SCOPE = "out_of_scope"


class CimReadiness(StrEnum):
    READY = "ready_for_downstream_use"
    PARTIAL = "partially_ready"
    INSUFFICIENT = "insufficient_customer_evidence"
    CONFLICTED = "conflicted"
    OUT_OF_SCOPE = "out_of_scope"


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


class IcpSegmentationOutputFixture(BaseModel):
    analysis_id: str
    skill_id: str
    skill_version: str
    source_context_reference: dict[str, Any]
    source_research_reference: dict[str, Any]
    source_competitor_reference: dict[str, Any]
    customer_intelligence: dict[str, Any]
    segment_ranking_summary: dict[str, Any]
    primary_icp_candidates: list[dict[str, Any]]
    secondary_segments: list[str]
    exploratory_segments: list[str]
    excluded_segments: list[dict[str, Any]]
    cross_segment_patterns: list[str]
    evidence_gaps: list[str]
    coverage: str
    evidence_quality: str
    research_status: ResearchStatus
    recommended_next_research: list[str]
    downstream_consumer_notes: list[str]
    provenance: OutputProvenance
    input_hash: str = Field(min_length=64, max_length=64)
    output_hash: str = Field(min_length=64, max_length=64)

    @field_validator("skill_id")
    @classmethod
    def skill_id_must_match(cls, value: str) -> str:
        if value != "ms.skill.icp_segmentation":
            raise ValueError("skill_id must be ms.skill.icp_segmentation")
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

    output_base = "ms.skill.icp_segmentation/output/0.1.0"
    cim_base = "ms.skill.icp_segmentation/customer_intelligence/0.1.0-draft"

    for name, contents in parsed.items():
        resource = Resource.from_contents(contents)
        candidate_uris: set[str] = {f"schemas/{name}"}
        schema_id = contents.get("$id")
        if isinstance(schema_id, str):
            candidate_uris.add(schema_id)
            candidate_uris.add(urljoin(schema_id, f"schemas/{name}"))

        for root_base in (output_base, cim_base):
            chain = root_base
            for _ in range(6):
                chain = urljoin(chain, f"schemas/{name}")
                candidate_uris.add(chain)

        for parent_name in parsed:
            for root_base in (output_base, cim_base):
                parent_chain = urljoin(root_base, f"schemas/{parent_name}")
                for _ in range(5):
                    candidate_uris.add(urljoin(parent_chain, f"schemas/{name}"))
                    parent_chain = urljoin(parent_chain, f"schemas/{parent_name}")

        for other_id in (
            item.get("$id") for item in parsed.values() if isinstance(item.get("$id"), str)
        ):
            candidate_uris.add(urljoin(other_id, f"schemas/{name}"))

        for uri in candidate_uris:
            _add(uri, resource)

    return Registry().with_resources(resources)


def schema_validator(schema_name: str, root: Path | None = None) -> Draft202012Validator:
    base = root or PACKAGE_ROOT
    schema = json.loads((base / "schemas" / schema_name).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=_schema_registry(base))


def validate_input_schema(data: Any) -> None:
    schema_validator("input.schema.json").validate(data)


def validate_output_schema(data: Any) -> None:
    schema_validator("output.schema.json").validate(data)


def validate_cim_schema(data: Any) -> None:
    schema_validator("customer_intelligence.schema.json").validate(data)


def validate_customer_segment_schema(data: Any) -> None:
    schema_validator("customer_segment.schema.json").validate(data)


def validate_jtbd_schema(data: Any) -> None:
    schema_validator("job_to_be_done.schema.json").validate(data)


def validate_decision_role_schema(data: Any) -> None:
    schema_validator("decision_role.schema.json").validate(data)


def validate_customer_claim_schema(data: Any) -> None:
    schema_validator("customer_claim.schema.json").validate(data)


def validate_output_fixture(data: Any) -> IcpSegmentationOutputFixture:
    validate_output_schema(data)
    return IcpSegmentationOutputFixture.model_validate(data)


def package_structure_valid() -> bool:
    return all((PACKAGE_ROOT / entry).exists() for entry in REQUIRED_PACKAGE_ENTRIES)


def output_has_forbidden_discriminators(data: dict[str, Any]) -> bool:
    return any(
        key in data
        for key in (
            "verdict",
            "readiness",
            "execution_status",
            "positioning",
            "final_offer",
            "proceed",
            "stop",
            "viable",
            "unviable",
        )
    )


def positioning_consumer_reads_cim(output: dict[str, Any]) -> dict[str, Any]:
    """Conceptual stub — Positioning consumes CIM without re-derivation."""
    cim = output["customer_intelligence"]
    primary = output["primary_icp_candidates"]
    segment_by_id = {s["segment_id"]: s for s in cim["segments"]}
    consumed: dict[str, Any] = {
        "primary_icp_candidates": primary,
        "segments": [],
        "jtbd": [],
        "pains": [],
        "objections": [],
        "trust_drivers": [],
    }
    for icp in primary:
        seg = segment_by_id.get(icp["segment_id"])
        if not seg:
            continue
        consumed["segments"].append(
            {
                "segment_id": seg["segment_id"],
                "segment_name": seg["segment_name"],
                "awareness_stage": seg.get("awareness_stage"),
                "market_sophistication": seg.get("market_sophistication"),
            }
        )
        consumed["jtbd"].extend(seg.get("jobs_to_be_done", []))
        consumed["pains"].extend(seg.get("pain_points", []))
        consumed["objections"].extend(seg.get("objections", []))
        consumed["trust_drivers"].extend(seg.get("trust_drivers", []))
    consumed["output_hash"] = output["output_hash"]
    consumed["recomputed_fields"] = []
    return consumed


def market_validation_consumer_reads_cim(output: dict[str, Any]) -> dict[str, Any]:
    """Conceptual stub — MV 0.2.0 consumes priority/evidence, not verdict from ICP."""
    cim = output["customer_intelligence"]
    segments = cim["segments"]
    return {
        "segment_priorities": [s.get("priority_assessment") for s in segments],
        "evidence_quality": cim.get("evidence_quality"),
        "coverage": cim.get("coverage"),
        "customer_unknowns": cim.get("customer_unknowns"),
        "segment_conflicts": cim.get("segment_conflicts"),
        "verdict": None,
        "verdict_source": "not_icp_segmentation",
    }


def package_hash() -> str:
    global FROZEN_PACKAGE_HASH
    if FROZEN_PACKAGE_HASH is None:
        from app.skills.hashing import calculate_skill_package_hash

        FROZEN_PACKAGE_HASH = calculate_skill_package_hash(PACKAGE_ROOT)
    return FROZEN_PACKAGE_HASH


__all__ = [
    "CA_ROOT",
    "CimReadiness",
    "FROZEN_CA_HASH",
    "FROZEN_MV_HASH",
    "FROZEN_PACKAGE_HASH",
    "FROZEN_PMC_010_HASH",
    "FROZEN_PMC_020_HASH",
    "IcpSegmentationOutputFixture",
    "MKG_ENTITY_MAPPINGS",
    "MKG_RELATION_EXAMPLES",
    "MR_ROOT",
    "PACKAGE_ROOT",
    "PMC_020_ROOT",
    "ResearchStatus",
    "load_json_fixture",
    "market_validation_consumer_reads_cim",
    "output_has_forbidden_discriminators",
    "package_hash",
    "package_structure_valid",
    "parse_manifest_scalar",
    "positioning_consumer_reads_cim",
    "read_manifest_text",
    "validate_cim_schema",
    "validate_customer_claim_schema",
    "validate_customer_segment_schema",
    "validate_decision_role_schema",
    "validate_input_schema",
    "validate_jtbd_schema",
    "validate_output_fixture",
    "validate_output_schema",
]
