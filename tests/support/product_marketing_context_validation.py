"""Test helpers for SKILL-02.1 Product Marketing Context package validation."""

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
    / "ms.skill.product_marketing_context"
)

FROZEN_MARKET_VALIDATION_ROOT = (
    Path(__file__).resolve().parents[2]
    / "packages"
    / "skills"
    / "ms.skill.market_validation"
)

FROZEN_MARKET_VALIDATION_HASH = (
    "6c53b5b972e5de900a135b891d8fbbd1641cdb5bf04bb171f83d5023344b8133"
)

SKILL_01_0_ALLOWED_STATUSES = frozenset({"candidate", "quarantined"})

REQUIRED_MANIFEST_KEYS = frozenset(
    {
        "id",
        "name",
        "version",
        "description",
        "owner",
        "source",
        "license",
        "status",
        "capabilities",
        "activation_conditions",
        "required_inputs",
        "output_schema",
        "required_evidence",
        "dependencies",
        "allowed_tools",
        "approval_policy",
        "tenant_scope",
        "quality_threshold",
        "known_limitations",
        "test_suite",
        "provenance",
    }
)

REQUIRED_PACKAGE_ENTRIES = (
    "SKILL.md",
    "manifest.yaml",
    "schemas/input.schema.json",
    "schemas/output.schema.json",
    "schemas/claim.schema.json",
    "tests/eval_manifest.yaml",
)

FORBIDDEN_SECRET_PATTERNS = re.compile(
    r"(api[_-]?key|secret|password|token|credential)\s*:",
    re.IGNORECASE,
)


class ContextReadiness(StrEnum):
    READY = "ready"
    PARTIALLY_READY = "partially_ready"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    CONFLICTED = "conflicted"


class OutputProvenance(BaseModel):
    skill_id: str
    skill_version: str
    generated_at: str | None = None
    methodology_ref: str | None = None
    source_skill_id: str | None = None
    source_skill_version: str | None = None
    source_output_hash: str | None = None


class ProductMarketingContextOutputFixture(BaseModel):
    context_id: str
    skill_id: str
    skill_version: str
    normalized_product: list[dict[str, Any]]
    normalized_business_model: list[dict[str, Any]]
    normalized_market_scope: list[dict[str, Any]]
    normalized_customer_claims: list[dict[str, Any]]
    normalized_problem_claims: list[dict[str, Any]]
    normalized_value_proposition_claims: list[dict[str, Any]]
    normalized_pricing_claims: list[dict[str, Any]]
    normalized_competitor_claims: list[dict[str, Any]]
    channel_context: list[dict[str, Any]]
    brand_constraints: list[dict[str, Any]]
    operational_constraints: list[dict[str, Any]]
    evidence_inventory: list[dict[str, Any]]
    assumptions: list[dict[str, Any]]
    unknowns: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    clarification_questions: list[str]
    readiness: ContextReadiness
    readiness_blockers: list[str]
    provenance: OutputProvenance
    input_hash: str = Field(min_length=64, max_length=64)
    output_hash: str = Field(min_length=64, max_length=64)

    @field_validator("skill_id")
    @classmethod
    def skill_id_must_match(cls, value: str) -> str:
        if value != "ms.skill.product_marketing_context":
            raise ValueError("skill_id must be ms.skill.product_marketing_context")
        return value

    model_config = {"extra": "forbid"}


def load_json_fixture(relative_path: str) -> Any:
    path = PACKAGE_ROOT / relative_path
    return json.loads(path.read_text(encoding="utf-8"))


def read_manifest_text(path: Path | None = None) -> str:
    manifest_path = path or (PACKAGE_ROOT / "manifest.yaml")
    return manifest_path.read_text(encoding="utf-8")


def parse_manifest_scalar(text: str, key: str) -> str | None:
    pattern = rf"^{re.escape(key)}:\s*(.+?)\s*$"
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        return None
    value = match.group(1).strip()
    if value.startswith('"') or value.startswith("'"):
        return value.strip("\"'")
    return value


def manifest_contains_required_keys(text: str) -> list[str]:
    return [key for key in REQUIRED_MANIFEST_KEYS if f"{key}:" not in text]


def package_structure_valid(root: Path | None = None) -> bool:
    base = root or PACKAGE_ROOT
    return all((base / entry).exists() for entry in REQUIRED_PACKAGE_ENTRIES)


def package_paths_safe(root: Path | None = None) -> bool:
    base = root or PACKAGE_ROOT
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(base).as_posix()
        if ".." in rel or rel.startswith("/"):
            return False
    return True


def scripts_disabled(manifest_text: str) -> bool:
    return "script_policy:" in manifest_text and "enabled: false" in manifest_text


def no_secrets_in_manifest(manifest_text: str) -> bool:
    return FORBIDDEN_SECRET_PATTERNS.search(manifest_text) is None


def _schema_registry(root: Path | None = None) -> Registry:
    base = root or PACKAGE_ROOT
    schema_dir = base / "schemas"
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
            item.get("$id")
            for item in parsed.values()
            if isinstance(item.get("$id"), str)
        ):
            _add(urljoin(other_id, f"schemas/{name}"), resource)
    return Registry().with_resources(resources)


def schema_validator(schema_name: str, root: Path | None = None) -> Draft202012Validator:
    base = root or PACKAGE_ROOT
    schema_path = base / "schemas" / schema_name
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=_schema_registry(base))


def validate_input_schema(data: dict[str, Any]) -> None:
    schema_validator("input.schema.json").validate(data)


def validate_output_schema(data: dict[str, Any]) -> None:
    schema_validator("output.schema.json").validate(data)


def validate_claim_schema(data: dict[str, Any]) -> None:
    schema_validator("claim.schema.json").validate(data)


def validate_output_fixture(data: dict[str, Any]) -> ProductMarketingContextOutputFixture:
    validate_output_schema(data)
    return ProductMarketingContextOutputFixture.model_validate(data)


def output_has_verdict_field(data: dict[str, Any]) -> bool:
    return "verdict" in data


__all__ = [
    "ContextReadiness",
    "FROZEN_MARKET_VALIDATION_HASH",
    "FROZEN_MARKET_VALIDATION_ROOT",
    "PACKAGE_ROOT",
    "ProductMarketingContextOutputFixture",
    "SKILL_01_0_ALLOWED_STATUSES",
    "load_json_fixture",
    "manifest_contains_required_keys",
    "no_secrets_in_manifest",
    "output_has_verdict_field",
    "package_paths_safe",
    "package_structure_valid",
    "parse_manifest_scalar",
    "read_manifest_text",
    "schema_validator",
    "scripts_disabled",
    "validate_claim_schema",
    "validate_input_schema",
    "validate_output_fixture",
    "validate_output_schema",
]
