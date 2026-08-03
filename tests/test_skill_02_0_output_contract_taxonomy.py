"""SKILL-02.0 — Output contract taxonomy tests."""

from __future__ import annotations

import json
from pathlib import Path

from app.schemas.contracts import SkillOutputContractType
from app.skills.hashing import calculate_skill_package_hash
from app.skills.legacy_output_contract import (
    LEGACY_OUTPUT_CONTRACT_TYPES,
    resolve_output_contract_type,
)
from app.skills.output_contract_rules import validate_output_contract_schema
from app.skills.package_validator import validate_skill_package

PMC_ROOT = (
    Path(__file__).resolve().parents[1]
    / "packages"
    / "skills"
    / "ms.skill.product_marketing_context"
)
PMC_020_ROOT = PMC_ROOT / "0.2.0"
MR_ROOT = (
    Path(__file__).resolve().parents[1] / "packages" / "skills" / "ms.skill.market_research"
)
MV_ROOT = (
    Path(__file__).resolve().parents[1] / "packages" / "skills" / "ms.skill.market_validation"
)

PMC_010_HASH = "5e3dfc1bfc48c56d33951006c3adcf80b4d53ad246e96669d1d32014934cc230"
PMC_020_HASH = "08bf9d55a261da52a8659f5aa6f06c3f9a63f13f06a21aea5b2416b10a381eaa"
MV_HASH = "6c53b5b972e5de900a135b891d8fbbd1641cdb5bf04bb171f83d5023344b8133"
MR_HASH = "6acce32a4952de75d97129d8d39cc15c14a97805fc8850927bac3c19cc6fc14e"


def test_pmc_010_legacy_resolves_context_contract() -> None:
    report = validate_skill_package(PMC_ROOT)
    assert report.valid is True
    assert report.manifest is not None
    assert report.manifest.output_contract_type is None
    assert (
        resolve_output_contract_type(report.manifest) == SkillOutputContractType.CONTEXT
    )
    assert report.package_hash == PMC_010_HASH


def test_pmc_020_manifest_declares_context_contract() -> None:
    report = validate_skill_package(PMC_020_ROOT)
    assert report.valid is True
    assert report.manifest is not None
    assert report.manifest.output_contract_type == SkillOutputContractType.CONTEXT
    assert report.package_hash == PMC_020_HASH


def test_market_validation_legacy_resolves_decision_contract() -> None:
    report = validate_skill_package(MV_ROOT)
    assert report.valid is True
    assert report.manifest is not None
    assert report.manifest.output_contract_type is None
    assert (
        resolve_output_contract_type(report.manifest) == SkillOutputContractType.DECISION
    )
    assert report.package_hash == MV_HASH


def test_market_research_manifest_declares_research_contract() -> None:
    report = validate_skill_package(MR_ROOT)
    assert report.valid is True
    assert report.manifest is not None
    assert report.manifest.output_contract_type == SkillOutputContractType.RESEARCH
    assert report.package_hash == MR_HASH


def test_legacy_mapping_documents_market_validation_only_minimum() -> None:
    assert LEGACY_OUTPUT_CONTRACT_TYPES[("ms.skill.market_validation", "0.1.0")] == (
        SkillOutputContractType.DECISION
    )


def test_context_output_schema_forbids_verdict() -> None:
    schema = json.loads((PMC_ROOT / "schemas/output.schema.json").read_text(encoding="utf-8"))
    errors = validate_output_contract_schema(schema, SkillOutputContractType.CONTEXT)
    assert errors == []
    assert "verdict" not in schema.get("properties", {})


def test_research_output_schema_forbids_verdict_and_readiness() -> None:
    schema = json.loads((MR_ROOT / "schemas/output.schema.json").read_text(encoding="utf-8"))
    errors = validate_output_contract_schema(schema, SkillOutputContractType.RESEARCH)
    assert errors == []
    assert "verdict" not in schema.get("properties", {})
    assert "readiness" not in schema.get("properties", {})


def test_decision_output_schema_forbids_readiness() -> None:
    schema = json.loads((MV_ROOT / "schemas/output.schema.json").read_text(encoding="utf-8"))
    errors = validate_output_contract_schema(schema, SkillOutputContractType.DECISION)
    assert errors == []
    assert "readiness" not in schema.get("properties", {})


def test_context_schema_with_verdict_fails_contract_check() -> None:
    schema = json.loads((PMC_ROOT / "schemas/output.schema.json").read_text(encoding="utf-8"))
    schema = dict(schema)
    schema["properties"] = dict(schema["properties"])
    schema["properties"]["verdict"] = {"type": "string", "enum": ["proceed"]}
    errors = validate_output_contract_schema(schema, SkillOutputContractType.CONTEXT)
    assert any("forbids 'verdict'" in err for err in errors)


def test_research_schema_with_readiness_fails_contract_check() -> None:
    schema = json.loads((MR_ROOT / "schemas/output.schema.json").read_text(encoding="utf-8"))
    schema = dict(schema)
    schema["properties"] = dict(schema["properties"])
    schema["properties"]["readiness"] = {"type": "string", "enum": ["ready"]}
    errors = validate_output_contract_schema(schema, SkillOutputContractType.RESEARCH)
    assert any("forbids 'readiness'" in err for err in errors)


def test_research_status_enum_excludes_commercial_verdict_values() -> None:
    schema = json.loads((MR_ROOT / "schemas/output.schema.json").read_text(encoding="utf-8"))
    status_enum = schema["properties"]["research_status"]["enum"]
    for forbidden in ("proceed", "stop", "viable", "unviable"):
        assert forbidden not in status_enum


def test_nested_version_dir_does_not_change_frozen_010_hash() -> None:
    assert calculate_skill_package_hash(PMC_ROOT) == PMC_010_HASH


def test_new_package_without_output_contract_type_fails(tmp_path: Path) -> None:
    import shutil

    dest = tmp_path / "pkg"
    shutil.copytree(MR_ROOT, dest)
    manifest_text = (dest / "manifest.yaml").read_text(encoding="utf-8")
    manifest_text = manifest_text.replace("output_contract_type: research\n", "")
    (dest / "manifest.yaml").write_text(manifest_text, encoding="utf-8")
    report = validate_skill_package(dest)
    assert report.valid is False
    assert any(err.code == "skill_output_contract_type_missing" for err in report.errors)
