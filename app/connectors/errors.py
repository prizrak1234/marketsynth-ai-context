"""Safe domain errors for Connector Gateway (SKILL-01.5)."""

from __future__ import annotations


class ConnectorError(Exception):
    def __init__(self, message: str, *, code: str = "connector_error") -> None:
        self.code = code
        super().__init__(message)


class ConnectorNotFoundError(ConnectorError):
    def __init__(self, message: str = "Connector was not found.") -> None:
        super().__init__(message, code="connector_not_found")


class ConnectorVersionNotFoundError(ConnectorError):
    def __init__(self, message: str = "Connector version was not found.") -> None:
        super().__init__(message, code="connector_version_not_found")


class ConnectorToolNotFoundError(ConnectorError):
    def __init__(self, message: str = "Connector tool was not found.") -> None:
        super().__init__(message, code="connector_tool_not_found")


class ConnectorPolicyDeniedError(ConnectorError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="connector_policy_denied")


class ConnectorApprovalRequiredError(ConnectorError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="connector_approval_required")


class ConnectorCredentialBindingError(ConnectorError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="connector_credential_binding_error")


class ConnectorTenantVisibilityError(ConnectorError):
    def __init__(self, message: str = "Connector binding is not visible.") -> None:
        super().__init__(message, code="connector_tenant_visibility_error")


class ConnectorAdapterUnavailableError(ConnectorError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="connector_adapter_unavailable")


class ConnectorExecutionNormalizationError(ConnectorError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="connector_execution_normalization_error")


class ConnectorIdempotencyError(ConnectorError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="connector_idempotency_error")


class ConnectorBudgetPolicyError(ConnectorError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="connector_budget_policy_error")


class ConnectorRatePolicyError(ConnectorError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="connector_rate_policy_error")


class ConnectorEvidenceRequirementError(ConnectorError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="connector_evidence_requirement_error")
