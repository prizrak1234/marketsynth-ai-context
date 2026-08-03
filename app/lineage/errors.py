"""Safe domain errors for lineage layer (SKILL-01.7)."""

from __future__ import annotations


class LineageError(Exception):
    def __init__(self, message: str, *, code: str = "lineage_error") -> None:
        self.code = code
        super().__init__(message)


class LineageContractError(LineageError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="lineage_contract_error")


class LineageBuildError(LineageError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="lineage_build_error")


class LineageMergeError(LineageError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="lineage_merge_error")


class LineageValidationError(LineageError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="lineage_validation_error")
