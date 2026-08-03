"""Test helpers for SKILL-02.2 Market Research package validation."""

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
    / "ms.skill.market_research"
)

PMC_PACKAGE_ROOT = (
    Path(__file__).resolve().parents[2]
    / "packages"
    / "skills"
    / "ms.skill.product_marketing_context"
)

FROZEN_PACKAGE_HASH = (
    "6acce32a4952de75d97129d8d39cc15c14a97805fc8850927bac3c19cc6fc14e"
)

REQUIRED_PACKAGE_ENTRIES = (
    "SKILL.md",
    "manifest.yaml",
    "schemas/input.schema.json",
    "schemas/output.schema.json",
    "schemas/research_finding.schema.json",
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
    source_skill_id: str | None = None
    source_skill_version: str | None = None
    source_output_hash: str | None = None


class MarketResearchOutputFixture(BaseModel):
    research_id: str
    skill_id: str
    skill_version: str
    source_context_reference: dict[str, Any]
    research_questions: list[str]
    market_definition: list[dict[str, Any]]
    market_structure: list[dict[str, Any]]
    market_signals: list[dict[str, Any]]
    demand_signals: list[dict[str, Any]]
    customer_signals: list[dict[str, Any]]
    pricing_signals: list[dict[str, Any]]
    channel_signals: list[dict[str, Any]]
    competitor_signals: list[dict[str, Any]]
    regulatory_or_operational_constraints: list[dict[str, Any]]
    source_inventory: list[dict[str, Any]]
    supporting_evidence: list[dict[str, Any]]
    contradictory_evidence: list[dict[str, Any]]
    assumptions: list[dict[str, Any]]
    inferences: list[dict[str, Any]]
    unknowns: list[dict[str, Any]]
    evidence_gaps: list[str]
    coverage: str
    evidence_quality: str
    research_status: ResearchStatus
    recommended_next_research: list[str]
    provenance: OutputProvenance
    input_hash: str = Field(min_length=64, max_length=64)
    output_hash: str = Field(min_length=64, max_length=64)

    @field_validator("skill_id")
    @classmethod
    def skill_id_must_match(cls, value: str) -> str:
        if value != "ms.skill.market_research":
            raise ValueError("skill_id must be ms.skill.market_research")
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


def package_structure_valid() -> bool:
    return all((PACKAGE_ROOT / entry).exists() for entry in REQUIRED_PACKAGE_ENTRIES)


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


def validate_input_schema(data: dict[str, Any]) -> None:
    schema_validator("input.schema.json").validate(data)


def validate_output_schema(data: dict[str, Any]) -> None:
    schema_validator("output.schema.json").validate(data)


def validate_finding_schema(data: dict[str, Any]) -> None:
    schema_validator("research_finding.schema.json").validate(data)


def validate_output_fixture(data: dict[str, Any]) -> MarketResearchOutputFixture:
    validate_output_schema(data)
    return MarketResearchOutputFixture.model_validate(data)


def output_has_verdict_or_readiness(data: dict[str, Any]) -> bool:
    return "verdict" in data or "readiness" in data


__all__ = [
    "FROZEN_PACKAGE_HASH",
    "PACKAGE_ROOT",
    "PMC_PACKAGE_ROOT",
    "MarketResearchOutputFixture",
    "ResearchStatus",
    "load_json_fixture",
    "output_has_verdict_or_readiness",
    "package_structure_valid",
    "parse_manifest_scalar",
    "read_manifest_text",
    "validate_finding_schema",
    "validate_input_schema",
    "validate_output_fixture",
    "validate_output_schema",
]
