"""SKILL-02.2.1 — Immutable version repair tests."""

from __future__ import annotations

import shutil
from pathlib import Path

from app.schemas.contracts import SkillOutputContractType
from app.skills.hashing import calculate_skill_package_hash
from app.skills.legacy_output_contract import (
    FROZEN_PACKAGE_HASHES,
    frozen_package_hash_conflict,
    resolve_output_contract_type,
)
from app.skills.package_validator import validate_skill_package

PMC_ROOT = (
    Path(__file__).resolve().parents[1]
    / "packages"
    / "skills"
    / "ms.skill.product_marketing_context"
)
PMC_020_ROOT = PMC_ROOT / "0.2.0"
MV_ROOT = (
    Path(__file__).resolve().parents[1] / "packages" / "skills" / "ms.skill.market_validation"
)

PMC_010_HASH = FROZEN_PACKAGE_HASHES[("ms.skill.product_marketing_context", "0.1.0")]
MV_HASH = FROZEN_PACKAGE_HASHES[("ms.skill.market_validation", "0.1.0")]


def test_frozen_pmc_010_hash_restored() -> None:
    assert calculate_skill_package_hash(PMC_ROOT) == PMC_010_HASH
    report = validate_skill_package(PMC_ROOT)
    assert report.valid is True
    assert report.package_hash == PMC_010_HASH


def test_frozen_market_validation_010_hash_restored() -> None:
    assert calculate_skill_package_hash(MV_ROOT) == MV_HASH
    report = validate_skill_package(MV_ROOT)
    assert report.valid is True
    assert report.package_hash == MV_HASH


def test_pmc_020_has_manifest_output_contract_type() -> None:
    report = validate_skill_package(PMC_020_ROOT)
    assert report.valid is True
    assert report.manifest is not None
    assert report.manifest.version == "0.2.0"
    assert report.manifest.output_contract_type == SkillOutputContractType.CONTEXT


def test_legacy_mapping_resolves_mv_decision_without_manifest_field() -> None:
    report = validate_skill_package(MV_ROOT)
    assert report.manifest is not None
    assert report.manifest.output_contract_type is None
    assert resolve_output_contract_type(report.manifest) == SkillOutputContractType.DECISION


def test_frozen_hash_conflict_helper_detects_mismatch() -> None:
    message = frozen_package_hash_conflict(
        skill_id="ms.skill.market_validation",
        version="0.1.0",
        package_hash="0" * 64,
    )
    assert message is not None
    assert "Immutable version conflict" in message


def test_validator_blocks_frozen_hash_mutation(tmp_path: Path) -> None:
    pkg = tmp_path / "mv"
    shutil.copytree(MV_ROOT, pkg)
    (pkg / "resources" / "README.md").write_text("tampered\n", encoding="utf-8")
    report = validate_skill_package(pkg)
    assert report.valid is False
    assert any(err.code == "immutable_version_hash_conflict" for err in report.errors)


def test_validator_allows_non_frozen_package_content_change(tmp_path: Path) -> None:
    pkg = tmp_path / "pmc020"
    shutil.copytree(PMC_020_ROOT, pkg)
    (pkg / "resources" / "README.md").write_text("draft tweak\n", encoding="utf-8")
    report = validate_skill_package(pkg)
    assert report.valid is True
    assert not any(err.code == "immutable_version_hash_conflict" for err in report.errors)
