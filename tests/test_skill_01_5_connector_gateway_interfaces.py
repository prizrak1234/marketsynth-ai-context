"""SKILL-01.5 — Connector Gateway interface tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from app.connectors import (
    BudgetPolicy,
    ConnectorDataSensitivity,
    ConnectorExecutionRequest,
    ConnectorExecutionResultStatus,
    ConnectorPolicyOutcome,
    ConnectorStatus,
    CredentialBindingReference,
    ProjectConnectorBinding,
    RetryPolicy,
    TenantConnectorBinding,
    build_test_gateway,
    hash_payload,
    payload_contains_secret_like_keys,
    redact_provider_metadata,
    skill_tool_intersection_allowed,
    validate_connector_status,
)
from app.connectors.contracts import (
    ConnectorActionType,
    ConnectorApprovalClass,
    ConnectorDescriptor,
    ConnectorHealthState,
    ConnectorIdempotencyClass,
    ConnectorSideEffectClass,
    ConnectorToolDefinition,
)
from app.connectors.errors import ConnectorNotFoundError
from app.connectors.fixtures import (
    ADVERTISING_CONNECTOR_ID,
    ADVERTISING_TOOL_ID,
    CONNECTOR_VERSION,
    CONTENT_GEN_CONNECTOR_ID,
    CONTENT_GEN_TOOL_ID,
    PUBLICATION_CONNECTOR_ID,
    PUBLICATION_TOOL_ID,
    RESEARCH_CONNECTOR_ID,
    RESEARCH_TOOL_ID,
    TELEGRAM_MCP_CONNECTOR_ID,
    TELEGRAM_MCP_TOOL_ID,
    advertising_descriptor,
    advertising_spend_tool,
    all_fixture_tools,
    content_generation_descriptor,
    content_generation_tool,
    native_telegram_descriptor,
    publication_descriptor,
    publication_tool,
    research_read_descriptor,
    research_read_tool,
    telegram_mcp_descriptor,
    telegram_mcp_tool,
)
from app.connectors.policies import evaluate_connector_request as policy_eval
from pydantic import ValidationError

TENANT_A = UUID("11111111-1111-1111-1111-111111111111")
TENANT_B = UUID("22222222-2222-2222-2222-222222222222")
PROJECT_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
ACTOR = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
NOW = datetime(2026, 7, 23, 12, 0, 0, tzinfo=UTC)
MARKET_VALIDATION_SKILL_ID = "ms.skill.market_validation"
MARKET_VALIDATION_SKILL_VERSION = "0.1.0"


def _credential(
    *, tenant_id: UUID = TENANT_A, connector_id: str = RESEARCH_CONNECTOR_ID
) -> CredentialBindingReference:
    return CredentialBindingReference(
        binding_id="bind-001",
        tenant_id=tenant_id,
        provider="fixture",
        connector_id=connector_id,
        scope_names=("read",),
        status="active",
    )


def _tenant_binding(
    *,
    tenant_id: UUID = TENANT_A,
    connector_id: str = RESEARCH_CONNECTOR_ID,
    tool_ids: frozenset[str] | None = None,
    visible: bool = True,
) -> TenantConnectorBinding:
    return TenantConnectorBinding(
        tenant_id=tenant_id,
        connector_id=connector_id,
        connector_version=CONNECTOR_VERSION,
        visible=visible,
        enabled_tool_ids=tool_ids if tool_ids is not None else frozenset({RESEARCH_TOOL_ID}),
        credential_binding_id="bind-001",
    )


def _project_binding(
    *,
    tenant_id: UUID = TENANT_A,
    connector_id: str = RESEARCH_CONNECTOR_ID,
    tool_ids: frozenset[str] | None = None,
) -> ProjectConnectorBinding:
    return ProjectConnectorBinding(
        tenant_id=tenant_id,
        project_id=PROJECT_A,
        connector_id=connector_id,
        connector_version=CONNECTOR_VERSION,
        enabled_tool_ids=tool_ids if tool_ids is not None else frozenset({RESEARCH_TOOL_ID}),
        credential_binding_id="bind-001",
    )


def _request(
    *,
    connector_id: str = RESEARCH_CONNECTOR_ID,
    tool_id: str = RESEARCH_TOOL_ID,
    tenant_id: UUID = TENANT_A,
    skill_id: str | None = MARKET_VALIDATION_SKILL_ID,
    skill_version: str | None = MARKET_VALIDATION_SKILL_VERSION,
    skill_allowed_tools: tuple[str, ...] = (RESEARCH_TOOL_ID,),
    approval_reference: str | None = None,
    credential: CredentialBindingReference | None = None,
    budget_context: BudgetPolicy | None = None,
    input_payload: dict | None = None,
    retry_policy: RetryPolicy | None = None,
    runtime_id: str = "operator_dry_run",
) -> ConnectorExecutionRequest:
    return ConnectorExecutionRequest(
        request_id=uuid4(),
        correlation_id=uuid4(),
        tenant_id=tenant_id,
        project_id=PROJECT_A,
        actor_id=ACTOR,
        skill_id=skill_id,
        skill_version=skill_version,
        connector_id=connector_id,
        connector_version=CONNECTOR_VERSION,
        tool_id=tool_id,
        input_payload=input_payload or {"query": "marketsynth"},
        credential_binding_reference=credential,
        approval_reference=approval_reference,
        budget_context=budget_context,
        requested_at=NOW,
        retry_policy=retry_policy or RetryPolicy(),
        skill_allowed_tools=skill_allowed_tools,
        runtime_id=runtime_id,
    )


def test_connector_contracts_are_immutable() -> None:
    tool = research_read_tool()
    with pytest.raises(ValidationError):
        tool.enabled_by_default = True  # type: ignore[misc]


def test_unknown_connector_status_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown connector status"):
        validate_connector_status("paused")


def test_no_paused_status_accepted() -> None:
    assert "paused" not in {item.value for item in ConnectorStatus}


def test_tool_enabled_by_default_is_false() -> None:
    for tool in all_fixture_tools().values():
        assert tool.enabled_by_default is False


def test_server_active_alone_does_not_enable_tool() -> None:
    descriptor = research_read_descriptor(status=ConnectorStatus.ACTIVE)
    tool = research_read_tool()
    request = _request(skill_allowed_tools=())
    decision = policy_eval(
        request,
        descriptor,
        tool,
        _tenant_binding(tool_ids=frozenset()),
        _project_binding(tool_ids=frozenset()),
    )
    assert decision.outcome == ConnectorPolicyOutcome.DENY


def test_missing_tool_level_allowlist_denies() -> None:
    descriptor = research_read_descriptor()
    tool = research_read_tool()
    request = _request(skill_allowed_tools=(RESEARCH_TOOL_ID,))
    tenant = _tenant_binding(tool_ids=frozenset())
    project = _project_binding(tool_ids=frozenset({RESEARCH_TOOL_ID}))
    decision = policy_eval(request, descriptor, tool, tenant, project)
    assert decision.outcome == ConnectorPolicyOutcome.DENY


def test_skill_allowed_tools_empty_denies() -> None:
    descriptor = research_read_descriptor()
    tool = research_read_tool()
    request = _request(skill_allowed_tools=())
    decision = policy_eval(
        request,
        descriptor,
        tool,
        _tenant_binding(),
        _project_binding(),
    )
    assert decision.outcome == ConnectorPolicyOutcome.DENY


def test_frozen_market_validation_skill_cannot_invoke_connector() -> None:
    gateway, _ = build_test_gateway()
    request = _request(
        skill_id=MARKET_VALIDATION_SKILL_ID,
        skill_version=MARKET_VALIDATION_SKILL_VERSION,
        skill_allowed_tools=(),
    )
    result = gateway.execute(
        request,
        tenant_binding=_tenant_binding(),
        project_binding=_project_binding(),
    )
    assert result.status == ConnectorExecutionResultStatus.REJECTED_BY_POLICY


def test_cross_tenant_binding_is_invisible() -> None:
    descriptor = research_read_descriptor()
    tool = research_read_tool()
    invisible_tenant = _tenant_binding(visible=False)
    decision = policy_eval(
        _request(tenant_id=TENANT_B, credential=_credential(tenant_id=TENANT_A)),
        descriptor,
        tool,
        invisible_tenant,
        _project_binding(),
    )
    assert decision.outcome == ConnectorPolicyOutcome.DENY
    err = ConnectorNotFoundError()
    assert "tenant" not in str(err).lower()


def test_missing_credential_reference_denies_when_required() -> None:
    descriptor = content_generation_descriptor()
    tool = content_generation_tool()
    request = _request(
        connector_id=CONTENT_GEN_CONNECTOR_ID,
        tool_id=CONTENT_GEN_TOOL_ID,
        skill_allowed_tools=(CONTENT_GEN_TOOL_ID,),
        approval_reference="appr-1",
        budget_context=BudgetPolicy(request_budget_limit=10.0),
        credential=None,
    )
    decision = policy_eval(
        request,
        descriptor,
        tool,
        _tenant_binding(
            connector_id=CONTENT_GEN_CONNECTOR_ID, tool_ids=frozenset({CONTENT_GEN_TOOL_ID})
        ),
        _project_binding(
            connector_id=CONTENT_GEN_CONNECTOR_ID, tool_ids=frozenset({CONTENT_GEN_TOOL_ID})
        ),
    )
    assert decision.outcome == ConnectorPolicyOutcome.DENY


def test_credential_reference_contains_no_secret_material() -> None:
    binding = _credential()
    assert binding.metadata_only is True
    assert (
        "token" not in binding.model_dump_json().lower() or "metadata_only" in binding.model_dump()
    )


def test_read_only_allowed_synthetic_request_passes_policy() -> None:
    descriptor = research_read_descriptor()
    tool = research_read_tool()
    request = _request(credential=_credential())
    decision = policy_eval(request, descriptor, tool, _tenant_binding(), _project_binding())
    assert decision.outcome == ConnectorPolicyOutcome.ALLOW


def test_denied_request_does_not_call_adapter() -> None:
    gateway, adapters = build_test_gateway()
    adapter = adapters[RESEARCH_CONNECTOR_ID]
    request = _request(skill_allowed_tools=())
    gateway.execute(request, tenant_binding=_tenant_binding(), project_binding=_project_binding())
    assert adapter.invocation_count == 0


def test_approval_required_request_does_not_call_adapter() -> None:
    gateway, adapters = build_test_gateway()
    adapter = adapters[CONTENT_GEN_CONNECTOR_ID]
    request = _request(
        connector_id=CONTENT_GEN_CONNECTOR_ID,
        tool_id=CONTENT_GEN_TOOL_ID,
        skill_allowed_tools=(CONTENT_GEN_TOOL_ID,),
        credential=_credential(connector_id=CONTENT_GEN_CONNECTOR_ID),
        budget_context=BudgetPolicy(request_budget_limit=5.0),
    )
    gateway.execute(
        request,
        tenant_binding=_tenant_binding(
            connector_id=CONTENT_GEN_CONNECTOR_ID, tool_ids=frozenset({CONTENT_GEN_TOOL_ID})
        ),
        project_binding=_project_binding(
            connector_id=CONTENT_GEN_CONNECTOR_ID, tool_ids=frozenset({CONTENT_GEN_TOOL_ID})
        ),
    )
    assert adapter.invocation_count == 0


def test_allowed_request_calls_adapter_once() -> None:
    gateway, adapters = build_test_gateway()
    adapter = adapters[RESEARCH_CONNECTOR_ID]
    request = _request(credential=_credential())
    result = gateway.execute(
        request, tenant_binding=_tenant_binding(), project_binding=_project_binding()
    )
    assert adapter.invocation_count == 1
    assert result.status == ConnectorExecutionResultStatus.SUCCEEDED


def test_write_tool_requires_approval() -> None:
    tool = ConnectorToolDefinition(
        connector_id=RESEARCH_CONNECTOR_ID,
        tool_id="research.write",
        name="Write",
        action_type=ConnectorActionType.WRITE,
        side_effect_class=ConnectorSideEffectClass.REVERSIBLE,
        data_sensitivity=ConnectorDataSensitivity.TENANT_INTERNAL,
        approval_class=ConnectorApprovalClass.NONE,
        idempotency=ConnectorIdempotencyClass.UNKNOWN,
    )
    request = _request(
        tool_id="research.write", skill_allowed_tools=("research.write",), credential=_credential()
    )
    decision = policy_eval(
        request,
        research_read_descriptor(),
        tool,
        _tenant_binding(tool_ids=frozenset({"research.write"})),
        _project_binding(tool_ids=frozenset({"research.write"})),
    )
    assert decision.outcome == ConnectorPolicyOutcome.REQUIRE_APPROVAL


def test_delete_tool_requires_elevated_approval() -> None:
    tool = ConnectorToolDefinition(
        connector_id=RESEARCH_CONNECTOR_ID,
        tool_id="research.delete",
        name="Delete",
        action_type=ConnectorActionType.DELETE,
        side_effect_class=ConnectorSideEffectClass.IRREVERSIBLE,
        data_sensitivity=ConnectorDataSensitivity.TENANT_INTERNAL,
        approval_class=ConnectorApprovalClass.NONE,
        idempotency=ConnectorIdempotencyClass.NOT_IDEMPOTENT,
    )
    request = _request(
        tool_id="research.delete",
        skill_allowed_tools=("research.delete",),
        credential=_credential(),
    )
    decision = policy_eval(
        request,
        research_read_descriptor(),
        tool,
        _tenant_binding(tool_ids=frozenset({"research.delete"})),
        _project_binding(tool_ids=frozenset({"research.delete"})),
    )
    assert decision.outcome == ConnectorPolicyOutcome.REQUIRE_APPROVAL


def test_admin_tool_requires_elevated_approval() -> None:
    tool = ConnectorToolDefinition(
        connector_id=RESEARCH_CONNECTOR_ID,
        tool_id="research.admin",
        name="Admin",
        action_type=ConnectorActionType.ADMIN,
        side_effect_class=ConnectorSideEffectClass.IRREVERSIBLE,
        data_sensitivity=ConnectorDataSensitivity.CONFIDENTIAL,
        approval_class=ConnectorApprovalClass.NONE,
        idempotency=ConnectorIdempotencyClass.NOT_IDEMPOTENT,
    )
    request = _request(
        tool_id="research.admin", skill_allowed_tools=("research.admin",), credential=_credential()
    )
    decision = policy_eval(
        request,
        research_read_descriptor(),
        tool,
        _tenant_binding(tool_ids=frozenset({"research.admin"})),
        _project_binding(tool_ids=frozenset({"research.admin"})),
    )
    assert decision.outcome == ConnectorPolicyOutcome.REQUIRE_APPROVAL


def test_publish_tool_requires_approval() -> None:
    descriptor = publication_descriptor()
    tool = publication_tool()
    request = _request(
        connector_id=PUBLICATION_CONNECTOR_ID,
        tool_id=PUBLICATION_TOOL_ID,
        skill_allowed_tools=(PUBLICATION_TOOL_ID,),
        credential=_credential(connector_id=PUBLICATION_CONNECTOR_ID),
    )
    decision = policy_eval(
        request,
        descriptor,
        tool,
        _tenant_binding(
            connector_id=PUBLICATION_CONNECTOR_ID, tool_ids=frozenset({PUBLICATION_TOOL_ID})
        ),
        _project_binding(
            connector_id=PUBLICATION_CONNECTOR_ID, tool_ids=frozenset({PUBLICATION_TOOL_ID})
        ),
    )
    assert decision.outcome == ConnectorPolicyOutcome.REQUIRE_APPROVAL


def test_billing_sensitive_tool_requires_approval_and_budget() -> None:
    descriptor = content_generation_descriptor()
    tool = content_generation_tool()
    request = _request(
        connector_id=CONTENT_GEN_CONNECTOR_ID,
        tool_id=CONTENT_GEN_TOOL_ID,
        skill_allowed_tools=(CONTENT_GEN_TOOL_ID,),
        credential=_credential(connector_id=CONTENT_GEN_CONNECTOR_ID),
        approval_reference="appr-1",
        budget_context=None,
    )
    decision = policy_eval(
        request,
        descriptor,
        tool,
        _tenant_binding(
            connector_id=CONTENT_GEN_CONNECTOR_ID, tool_ids=frozenset({CONTENT_GEN_TOOL_ID})
        ),
        _project_binding(
            connector_id=CONTENT_GEN_CONNECTOR_ID, tool_ids=frozenset({CONTENT_GEN_TOOL_ID})
        ),
    )
    assert decision.outcome == ConnectorPolicyOutcome.REQUIRE_APPROVAL


def test_unknown_billing_cost_does_not_auto_allow() -> None:
    descriptor = content_generation_descriptor()
    tool = content_generation_tool()
    request = _request(
        connector_id=CONTENT_GEN_CONNECTOR_ID,
        tool_id=CONTENT_GEN_TOOL_ID,
        skill_allowed_tools=(CONTENT_GEN_TOOL_ID,),
        credential=_credential(connector_id=CONTENT_GEN_CONNECTOR_ID),
        approval_reference="appr-1",
        budget_context=BudgetPolicy(deny_above_limit=True, request_budget_limit=None),
    )
    decision = policy_eval(
        request,
        descriptor,
        tool,
        _tenant_binding(
            connector_id=CONTENT_GEN_CONNECTOR_ID, tool_ids=frozenset({CONTENT_GEN_TOOL_ID})
        ),
        _project_binding(
            connector_id=CONTENT_GEN_CONNECTOR_ID, tool_ids=frozenset({CONTENT_GEN_TOOL_ID})
        ),
    )
    assert decision.outcome == ConnectorPolicyOutcome.REQUIRE_APPROVAL


def test_advertising_spend_denied_by_default() -> None:
    descriptor = advertising_descriptor()
    tool = advertising_spend_tool()
    request = _request(
        connector_id=ADVERTISING_CONNECTOR_ID,
        tool_id=ADVERTISING_TOOL_ID,
        skill_allowed_tools=(ADVERTISING_TOOL_ID,),
        credential=_credential(connector_id=ADVERTISING_CONNECTOR_ID),
        approval_reference="appr-1",
        budget_context=BudgetPolicy(request_budget_limit=100.0),
    )
    decision = policy_eval(
        request,
        descriptor,
        tool,
        _tenant_binding(
            connector_id=ADVERTISING_CONNECTOR_ID, tool_ids=frozenset({ADVERTISING_TOOL_ID})
        ),
        _project_binding(
            connector_id=ADVERTISING_CONNECTOR_ID, tool_ids=frozenset({ADVERTISING_TOOL_ID})
        ),
    )
    assert decision.outcome == ConnectorPolicyOutcome.DENY


def test_telegram_mcp_descriptor_rejected() -> None:
    descriptor = telegram_mcp_descriptor()
    tool = telegram_mcp_tool()
    request = _request(
        connector_id=TELEGRAM_MCP_CONNECTOR_ID,
        tool_id=TELEGRAM_MCP_TOOL_ID,
        skill_allowed_tools=(TELEGRAM_MCP_TOOL_ID,),
        credential=_credential(connector_id=TELEGRAM_MCP_CONNECTOR_ID),
        approval_reference="appr-1",
    )
    decision = policy_eval(
        request,
        descriptor,
        tool,
        _tenant_binding(
            connector_id=TELEGRAM_MCP_CONNECTOR_ID, tool_ids=frozenset({TELEGRAM_MCP_TOOL_ID})
        ),
        _project_binding(
            connector_id=TELEGRAM_MCP_CONNECTOR_ID, tool_ids=frozenset({TELEGRAM_MCP_TOOL_ID})
        ),
    )
    assert decision.outcome == ConnectorPolicyOutcome.DENY


def test_native_telegram_descriptor_distinct_from_mcp() -> None:
    native = native_telegram_descriptor()
    mcp = telegram_mcp_descriptor()
    assert native.is_native_authoritative is True
    assert native.is_mcp is False
    assert mcp.is_mcp is True
    assert mcp.status == ConnectorStatus.REJECTED


def test_suspended_connector_denied() -> None:
    descriptor = research_read_descriptor(status=ConnectorStatus.SUSPENDED)
    decision = policy_eval(
        _request(credential=_credential()),
        descriptor,
        research_read_tool(),
        _tenant_binding(),
        _project_binding(),
    )
    assert decision.outcome == ConnectorPolicyOutcome.DENY


def test_degraded_connector_produces_defer_or_unavailable() -> None:
    descriptor = research_read_descriptor(status=ConnectorStatus.DEGRADED)
    decision = policy_eval(
        _request(credential=_credential()),
        descriptor,
        research_read_tool(),
        _tenant_binding(),
        _project_binding(),
    )
    assert decision.outcome in {ConnectorPolicyOutcome.DEFER, ConnectorPolicyOutcome.UNAVAILABLE}


def test_archived_connector_not_selectable() -> None:
    descriptor = research_read_descriptor(status=ConnectorStatus.ARCHIVED)
    decision = policy_eval(
        _request(credential=_credential()),
        descriptor,
        research_read_tool(),
        _tenant_binding(),
        _project_binding(),
    )
    assert decision.outcome == ConnectorPolicyOutcome.DENY


def test_rejected_connector_denied() -> None:
    descriptor = research_read_descriptor(status=ConnectorStatus.REJECTED)
    decision = policy_eval(
        _request(credential=_credential()),
        descriptor,
        research_read_tool(),
        _tenant_binding(),
        _project_binding(),
    )
    assert decision.outcome == ConnectorPolicyOutcome.DENY


def test_unknown_policy_input_does_not_become_allow() -> None:
    descriptor = research_read_descriptor()
    tool = research_read_tool()
    request = _request(skill_allowed_tools=(RESEARCH_TOOL_ID,), runtime_id="unknown_runtime")
    decision = policy_eval(request, descriptor, tool, _tenant_binding(), _project_binding())
    assert decision.outcome != ConnectorPolicyOutcome.ALLOW


def test_tool_connector_id_mismatch_denied() -> None:
    tool = research_read_tool().model_copy(update={"connector_id": "other.connector"})
    decision = policy_eval(
        _request(credential=_credential()),
        research_read_descriptor(),
        tool,
        _tenant_binding(),
        _project_binding(),
    )
    assert decision.outcome == ConnectorPolicyOutcome.DENY


def test_skill_version_preserved_in_request_and_result() -> None:
    gateway, _ = build_test_gateway()
    request = _request(
        skill_version="0.1.0",
        credential=_credential(),
    )
    result = gateway.execute(
        request, tenant_binding=_tenant_binding(), project_binding=_project_binding()
    )
    assert result.skill_id == MARKET_VALIDATION_SKILL_ID
    assert result.skill_version == "0.1.0"


def test_evidence_descriptor_includes_required_lineage_fields() -> None:
    gateway, _ = build_test_gateway()
    result = gateway.execute(
        _request(credential=_credential()),
        tenant_binding=_tenant_binding(),
        project_binding=_project_binding(),
    )
    evidence = result.evidence_descriptor
    assert evidence is not None
    assert evidence.input_hash
    assert evidence.output_hash
    assert evidence.provider_metadata_hash
    assert evidence.lineage_parent_ids == ()


def test_evidence_hashes_deterministic() -> None:
    payload = {"a": 1, "b": "two"}
    assert hash_payload(payload) == hash_payload({"b": "two", "a": 1})


def test_input_payload_secret_like_key_rejected() -> None:
    assert payload_contains_secret_like_keys({"api_key": "x"}) == "api_key"
    decision = policy_eval(
        _request(input_payload={"access_token": "secret"}, credential=_credential()),
        research_read_descriptor(),
        research_read_tool(),
        _tenant_binding(),
        _project_binding(),
    )
    assert decision.outcome == ConnectorPolicyOutcome.DENY


def test_raw_provider_secret_metadata_redacted() -> None:
    redacted = redact_provider_metadata({"access_token": "abc", "safe": "ok"})
    assert redacted["access_token"] == "[REDACTED]"
    assert redacted["safe"] == "ok"


def test_non_idempotent_write_not_retryable() -> None:
    tool = publication_tool()
    request = _request(
        connector_id=PUBLICATION_CONNECTOR_ID,
        tool_id=PUBLICATION_TOOL_ID,
        skill_allowed_tools=(PUBLICATION_TOOL_ID,),
        credential=_credential(connector_id=PUBLICATION_CONNECTOR_ID),
        retry_policy=RetryPolicy(max_attempts=3),
    )
    decision = policy_eval(
        request,
        publication_descriptor(),
        tool,
        _tenant_binding(
            connector_id=PUBLICATION_CONNECTOR_ID, tool_ids=frozenset({PUBLICATION_TOOL_ID})
        ),
        _project_binding(
            connector_id=PUBLICATION_CONNECTOR_ID, tool_ids=frozenset({PUBLICATION_TOOL_ID})
        ),
    )
    assert decision.outcome == ConnectorPolicyOutcome.DENY


def test_unknown_outcome_write_not_auto_retried() -> None:
    tool = content_generation_tool()
    assert tool.idempotency == ConnectorIdempotencyClass.UNKNOWN
    request = _request(
        connector_id=CONTENT_GEN_CONNECTOR_ID,
        tool_id=CONTENT_GEN_TOOL_ID,
        skill_allowed_tools=(CONTENT_GEN_TOOL_ID,),
        credential=_credential(connector_id=CONTENT_GEN_CONNECTOR_ID),
        retry_policy=RetryPolicy(max_attempts=2),
    )
    decision = policy_eval(
        request,
        content_generation_descriptor(),
        tool,
        _tenant_binding(
            connector_id=CONTENT_GEN_CONNECTOR_ID, tool_ids=frozenset({CONTENT_GEN_TOOL_ID})
        ),
        _project_binding(
            connector_id=CONTENT_GEN_CONNECTOR_ID, tool_ids=frozenset({CONTENT_GEN_TOOL_ID})
        ),
    )
    assert decision.outcome in {
        ConnectorPolicyOutcome.DENY,
        ConnectorPolicyOutcome.REQUIRE_APPROVAL,
    }


def test_idempotent_read_may_declare_retry_policy() -> None:
    tool = research_read_tool()
    assert tool.idempotency == ConnectorIdempotencyClass.GUARANTEED
    request = _request(
        credential=_credential(),
        retry_policy=RetryPolicy(max_attempts=3),
    )
    decision = policy_eval(
        request, research_read_descriptor(), tool, _tenant_binding(), _project_binding()
    )
    assert decision.outcome == ConnectorPolicyOutcome.ALLOW


def test_duplicate_prevention_result_represented() -> None:
    result_status = ConnectorExecutionResultStatus.DUPLICATE_PREVENTED
    assert result_status.value == "duplicate_prevented"


def test_result_normalization_deterministic() -> None:
    gateway, _ = build_test_gateway()
    request = _request(credential=_credential())
    first = gateway.execute(
        request, tenant_binding=_tenant_binding(), project_binding=_project_binding()
    )
    second = gateway.execute(
        request.model_copy(update={"request_id": uuid4()}),
        tenant_binding=_tenant_binding(),
        project_binding=_project_binding(),
    )
    assert first.output_payload == second.output_payload
    assert first.safe_provider_metadata == second.safe_provider_metadata


def test_safe_errors_leak_no_tenant_existence() -> None:
    err = ConnectorNotFoundError()
    assert "tenant" not in str(err).lower()


def test_no_real_network_adapter_exists() -> None:
    from pathlib import Path

    import app.connectors.adapters as adapters_module

    source = Path(adapters_module.__file__).read_text(encoding="utf-8")
    for forbidden in ("httpx", "requests", "aiohttp", "socket", "subprocess"):
        assert forbidden not in source


def test_no_provider_sdk_imported() -> None:
    from pathlib import Path

    import app.connectors as connectors_pkg

    source = Path(connectors_pkg.__file__).read_text(encoding="utf-8")
    assert "firecrawl" not in source.lower()
    assert "xmlriver" not in source.lower()


def test_skill_tool_intersection_rule() -> None:
    assert skill_tool_intersection_allowed((), RESEARCH_TOOL_ID) is False
    assert skill_tool_intersection_allowed((RESEARCH_TOOL_ID,), RESEARCH_TOOL_ID) is True


def test_degraded_unavailable_health_state() -> None:
    descriptor = ConnectorDescriptor(
        connector_id=RESEARCH_CONNECTOR_ID,
        connector_version=CONNECTOR_VERSION,
        name="Degraded Unavailable",
        status=ConnectorStatus.DEGRADED,
        primary_class=research_read_descriptor().primary_class,
        adapter=research_read_descriptor().adapter,
        health_state=ConnectorHealthState.UNAVAILABLE,
        fixture_only=True,
    )
    decision = policy_eval(
        _request(credential=_credential()),
        descriptor,
        research_read_tool(),
        _tenant_binding(),
        _project_binding(),
    )
    assert decision.outcome == ConnectorPolicyOutcome.UNAVAILABLE
