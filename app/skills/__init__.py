"""Marketsynth Skill package validation (SKILL-01.2+)."""

from app.skills.errors import (
    SkillForbiddenContentError,
    SkillHashingError,
    SkillManifestMissingError,
    SkillManifestParseError,
    SkillManifestValidationError,
    SkillPackageNotFoundError,
    SkillPackagePathViolationError,
    SkillSchemaInvalidError,
    SkillSchemaMissingError,
    SkillValidationError,
)
from app.skills.hashing import calculate_skill_package_hash
from app.skills.manifest_parser import parse_skill_manifest
from app.skills.package_validator import validate_skill_package
from app.skills.registry_projection import (
    build_registry_snapshot,
    project_reports_to_snapshot,
    project_validation_report,
)
from app.skills.registry_queries import derive_eligibility_view, get_skill
from app.skills.validation_contracts import SkillPackageValidationReport, SkillValidationMode

__all__ = [
    "SkillForbiddenContentError",
    "SkillHashingError",
    "SkillManifestMissingError",
    "SkillManifestParseError",
    "SkillManifestValidationError",
    "SkillPackageNotFoundError",
    "SkillPackagePathViolationError",
    "SkillPackageValidationReport",
    "SkillSchemaInvalidError",
    "SkillSchemaMissingError",
    "SkillValidationError",
    "SkillValidationMode",
    "build_registry_snapshot",
    "calculate_skill_package_hash",
    "derive_eligibility_view",
    "get_skill",
    "parse_skill_manifest",
    "project_reports_to_snapshot",
    "project_validation_report",
    "validate_skill_package",
]
