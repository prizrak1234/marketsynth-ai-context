"""SKILL-02.2.1 — Product Marketing Context v0.2.0 package smoke tests."""

from __future__ import annotations

from pathlib import Path

from app.schemas.contracts import SkillLifecycleStatus, SkillOutputContractType
from app.skills.hashing import calculate_skill_package_hash
from app.skills.package_validator import validate_skill_package

PACKAGE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "packages"
    / "skills"
    / "ms.skill.product_marketing_context"
    / "0.2.0"
)

PMC_020_HASH = "08bf9d55a261da52a8659f5aa6f06c3f9a63f13f06a21aea5b2416b10a381eaa"


def test_pmc_020_validates_with_output_contract_type() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    assert report.valid is True
    assert report.skill_id == "ms.skill.product_marketing_context"
    assert report.skill_version == "0.2.0"
    assert report.status == SkillLifecycleStatus.CANDIDATE
    assert report.manifest is not None
    assert report.manifest.output_contract_type == SkillOutputContractType.CONTEXT


def test_pmc_020_package_hash_deterministic() -> None:
    assert calculate_skill_package_hash(PACKAGE_ROOT) == PMC_020_HASH
