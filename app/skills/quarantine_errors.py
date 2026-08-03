"""Safe domain errors for quarantine import (SKILL-01.4)."""

from __future__ import annotations


class SkillQuarantineError(Exception):
    def __init__(self, message: str, *, code: str = "skill_quarantine_error") -> None:
        self.code = code
        super().__init__(message)


class SkillQuarantineSourceNotFoundError(SkillQuarantineError):
    def __init__(self, message: str = "Quarantine import source was not found.") -> None:
        super().__init__(message, code="skill_quarantine_source_not_found")


class SkillQuarantineSourceTypeError(SkillQuarantineError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="skill_quarantine_source_type_error")


class SkillQuarantinePathViolationError(SkillQuarantineError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="skill_quarantine_path_violation")


class SkillQuarantineMaterializationError(SkillQuarantineError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="skill_quarantine_materialization_error")


class SkillQuarantineInspectionError(SkillQuarantineError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="skill_quarantine_inspection_error")


class SkillQuarantineConflictError(SkillQuarantineError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="skill_quarantine_conflict_error")


class SkillQuarantineValidationError(SkillQuarantineError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="skill_quarantine_validation_error")


class SkillQuarantineLimitExceededError(SkillQuarantineError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="skill_quarantine_limit_exceeded")


class SkillQuarantineUnsupportedFileError(SkillQuarantineError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="skill_quarantine_unsupported_file")
