"""Safe domain errors for Skill registry read models (SKILL-01.3)."""

from __future__ import annotations


class SkillRegistryError(Exception):
    """Base error for registry read operations."""

    def __init__(self, message: str, *, code: str = "skill_registry_error") -> None:
        self.code = code
        super().__init__(message)


class SkillRegistryRecordNotFoundError(SkillRegistryError):
    def __init__(self, message: str = "Skill registry record was not found.") -> None:
        super().__init__(message, code="skill_registry_record_not_found")


class SkillRegistryVersionNotFoundError(SkillRegistryError):
    def __init__(self, message: str = "Skill registry version was not found.") -> None:
        super().__init__(message, code="skill_registry_version_not_found")


class SkillRegistryProjectionError(SkillRegistryError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="skill_registry_projection_error")


class SkillRegistryConflictError(SkillRegistryError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="skill_registry_conflict_error")


class SkillRegistryVisibilityError(SkillRegistryError):
    def __init__(self, message: str = "Skill is not visible in this registry view.") -> None:
        super().__init__(message, code="skill_registry_visibility_error")


class SkillRegistryQueryError(SkillRegistryError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="skill_registry_query_error")
