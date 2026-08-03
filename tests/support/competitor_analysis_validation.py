"""Test helpers for SKILL-02.3 Competitor Analysis package validation."""

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

FROZEN_PACKAGE_HASH: str | None = None

REQUIRED_PACKAGE_ENTRIES = (
    "SKILL.md",
    "manifest.yaml",
    "schemas/input.schema.json",
    "schemas/output.schema.json",
    "schemas/competitor.schema.json",
    "schemas/comparison_dimension.schema.json",
    "schemas/differentiation_gap.schema.json",
    "tests/eval_manifest.yaml",
)


class ResearchStatus(StrEnum):
    COMPLETE = "complete"
    PARTIALLY_COMPLETE = "partially_complete"
    INSUFFICIENT_SOURCES = "insufficient_sources"
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


class CompetitorAnalysisOutputFixture(BaseModel):
    analysis_id: str
    skill_id: str
    skill_version: str
    source_context_reference: dict[str, Any]
    source_research_reference: dict[str, Any]
    competitor_inventory: list[dict[str, Any]]
    competitor_type_summary: dict[str, int]
    direct_competitors: list[str]
    indirect_competitors: list[str]
    substitutes: list[str]
    alternatives: list[str]
    emerging_competitors: list[str]
    comparison_dimensions: list[dict[str, Any]]
    competitive_landscape: dict[str, Any]
    market_pressure_findings: list[dict[str, Any]]
    audience_overlap_findings: list[dict[str, Any]]
    pricing_findings: list[dict[str, Any]]
    offer_findings: list[dict[str, Any]]
    channel_findings: list[dict[str, Any]]
    proof_and_trust_findings: list[dict[str, Any]]
    differentiation_gaps: list[dict[str, Any]]
    defensibility_findings: list[dict[str, Any]]
    unsupported_competitor_claims: list[dict[str, Any]]
    supporting_evidence: list[dict[str, Any]]
    contradictory_evidence: list[dict[str, Any]]
    assumptions: list[dict[str, Any]]
    inferences: list[dict[str, Any]]
    unknowns: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
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
        if value != "ms.skill.competitor_analysis":
            raise ValueError("skill_id must be ms.skill.competitor_analysis")
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


def validate_competitor_schema(data: Any) -> None:
    schema_validator("competitor.schema.json").validate(data)


def validate_comparison_schema(data: Any) -> None:
    schema_validator("comparison_dimension.schema.json").validate(data)


def validate_output_fixture(data: Any) -> CompetitorAnalysisOutputFixture:
    validate_output_schema(data)
    return CompetitorAnalysisOutputFixture.model_validate(data)


def package_structure_valid() -> bool:
    return all((PACKAGE_ROOT / entry).exists() for entry in REQUIRED_PACKAGE_ENTRIES)


def output_has_forbidden_discriminators(data: dict[str, Any]) -> bool:
    return any(key in data for key in ("verdict", "readiness", "execution_status"))


def package_hash() -> str:
    global FROZEN_PACKAGE_HASH
    if FROZEN_PACKAGE_HASH is None:
        from app.skills.hashing import calculate_skill_package_hash

        FROZEN_PACKAGE_HASH = calculate_skill_package_hash(PACKAGE_ROOT)
    return FROZEN_PACKAGE_HASH


__all__ = [
    "FROZEN_MV_HASH",
    "FROZEN_PACKAGE_HASH",
    "FROZEN_PMC_010_HASH",
    "MR_ROOT",
    "PACKAGE_ROOT",
    "PMC_020_ROOT",
    "CompetitorAnalysisOutputFixture",
    "ResearchStatus",
    "load_json_fixture",
    "output_has_forbidden_discriminators",
    "package_hash",
    "package_structure_valid",
    "parse_manifest_scalar",
    "read_manifest_text",
    "validate_competitor_schema",
    "validate_comparison_schema",
    "validate_input_schema",
    "validate_output_fixture",
    "validate_output_schema",
]
