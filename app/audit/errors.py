"""Safe domain errors for unified audit layer (SKILL-01.6)."""

from __future__ import annotations


class AuditError(Exception):
    def __init__(self, message: str, *, code: str = "audit_error") -> None:
        self.code = code
        super().__init__(message)


class AuditContractError(AuditError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="audit_contract_error")


class AuditAdapterError(AuditError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="audit_adapter_error")


class AuditAggregationError(AuditError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="audit_aggregation_error")
