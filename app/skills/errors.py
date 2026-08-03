"""Domain errors for Skill package validation — safe messages only."""

from __future__ import annotations


class SkillValidationError(Exception):
    """Base error for Skill package validation."""

    def __init__(self, message: str, *, code: str = "skill_validation_error") -> None:
        self.code = code
        super().__init__(message)


class SkillPackageNotFoundError(SkillValidationError):
    def __init__(self, message: str = "Skill package directory was not found.") -> None:
        super().__init__(message, code="skill_package_not_found")


class SkillManifestMissingError(SkillValidationError):
    def __init__(self, message: str = "manifest.yaml is missing from the Skill package.") -> None:
        super().__init__(message, code="skill_manifest_missing")


class SkillManifestParseError(SkillValidationError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="skill_manifest_parse_error")


class SkillManifestValidationError(SkillValidationError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="skill_manifest_validation_error")


class SkillPackagePathViolationError(SkillValidationError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="skill_package_path_violation")


class SkillSchemaMissingError(SkillValidationError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="skill_schema_missing")


class SkillSchemaInvalidError(SkillValidationError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="skill_schema_invalid")


class SkillForbiddenContentError(SkillValidationError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="skill_forbidden_content")


class SkillHashingError(SkillValidationError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="skill_hashing_error")
