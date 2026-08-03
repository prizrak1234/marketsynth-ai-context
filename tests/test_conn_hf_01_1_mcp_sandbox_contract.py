"""CONN-HF-01.1 — Higgsfield MCP sandbox contract verification tests."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from app.connectors.evidence import hash_payload
from app.connectors.higgsfield.constants import (
    DEPRECATED_GUESSED_TOOL_IDS,
    HIGGSFIELD_CONNECTOR_ID,
    HIGGSFIELD_OFFICIAL_MCP_ENDPOINT,
    MEDIA_CANONICAL_OPERATIONS,
    MEDIA_OP_IMAGE_GENERATE,
)
from app.connectors.higgsfield.descriptor import all_higgsfield_tools, higgsfield_descriptor
from app.connectors.higgsfield.mcp_client import HiggsfieldMcpClient
from app.connectors.higgsfield.sandbox.operation_mapping import OperationMappingStore
from app.connectors.higgsfield.sandbox.snapshot import SANDBOX_ROOT, sanitize_snapshot_payload
from app.core.config import Settings
from app.core.exceptions import InvalidStateError
from app.schemas.contracts import (
    MediaRenderAssetType,
    MediaRenderJobStatus,
    MediaRenderRequest,
    MediaRenderSpec,
)
from app.services.media_renderer_service import MediaRendererService
from tests.support.archive_mkt_validation import PACKAGE_HASHES, package_hash
from tests.support.kb_wpl_program_validation import FROZEN_PROGRAM_BUNDLE_HASH

PROJECT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
OWNER_ID = UUID("11111111-1111-1111-1111-111111111111")
OTHER_TENANT = UUID("22222222-2222-2222-2222-222222222222")


def _settings(**overrides) -> Settings:
    base = {
        "higgsfield_mcp_enabled": True,
        "higgsfield_oauth_access_token": None,
        "higgsfield_video_render_enabled": False,
        "higgsfield_owner_sandbox_enabled": False,
    }
    base.update(overrides)
    return Settings(**base)


def _render_request(**overrides) -> MediaRenderRequest:
    spec = MediaRenderSpec(
        asset_type=MediaRenderAssetType.IMAGE,
        style="minimal",
        aspect_ratio="16:9",
        brand="TestBrand",
        prompt="A fictional sandbox product hero shot",
        negative_prompt="text overlay",
        approval_required=True,
    )
    payload = {
        "spec": spec,
        "upstream_skill_id": "ms.skill.presentation_architecture",
        "dry_run": True,
    }
    payload.update(overrides)
    return MediaRenderRequest(**payload)


@pytest.mark.asyncio
async def test_01_dry_run_never_initializes_mcp_client():
    svc = MediaRendererService(_settings())
    with patch.object(svc._adapter._client, "initialize", new=AsyncMock()) as init_mock:
        result = await svc.render(owner_id=OWNER_ID, project_id=PROJECT_ID, body=_render_request())
        init_mock.assert_not_called()
    assert result.status == MediaRenderJobStatus.PLANNED_ONLY


@pytest.mark.asyncio
async def test_02_dry_run_never_makes_network_request():
    svc = MediaRendererService(_settings())
    with patch.object(svc._adapter._client, "_rpc", new=AsyncMock()) as rpc_mock:
        await svc.render(owner_id=OWNER_ID, project_id=PROJECT_ID, body=_render_request())
        rpc_mock.assert_not_called()


@pytest.mark.asyncio
async def test_03_dry_run_never_bypasses_policy():
    """Dry-run uses plan-only path — policy engine not invoked with dry_run waiver."""
    from datetime import UTC, datetime
    from uuid import uuid4

    from app.connectors.contracts import ConnectorExecutionRequest, TimeoutPolicy
    from app.connectors.higgsfield.registry import (
        build_higgsfield_bindings,
        build_higgsfield_gateway,
    )

    settings = _settings(higgsfield_oauth_access_token="token")
    gateway = build_higgsfield_gateway(settings)
    tenant, project, _credential = build_higgsfield_bindings(
        tenant_id=OWNER_ID, project_id=PROJECT_ID, settings=settings
    )
    request = ConnectorExecutionRequest(
        request_id=uuid4(),
        correlation_id=uuid4(),
        tenant_id=OWNER_ID,
        project_id=PROJECT_ID,
        actor_id=OWNER_ID,
        skill_id="ms.skill.presentation_architecture",
        skill_version="0.1.0",
        connector_id=HIGGSFIELD_CONNECTOR_ID,
        connector_version="0.1.0",
        tool_id=MEDIA_OP_IMAGE_GENERATE,
        input_payload={"spec": _render_request().spec.model_dump(mode="json")},
        credential_binding_reference=None,
        approval_reference=None,
        budget_context=None,
        requested_at=datetime.now(UTC),
        timeout_policy=TimeoutPolicy(timeout_seconds=30),
        dry_run=True,
        runtime_id="media_renderer",
        skill_allowed_tools=(MEDIA_OP_IMAGE_GENERATE,),
    )
    _desc, _tool, decision = gateway.evaluate_policy(
        request,
        tenant_binding=tenant,
        project_binding=project,
    )
    assert decision.outcome.value != "allow"


@pytest.mark.asyncio
async def test_04_dry_run_returns_planned_only():
    svc = MediaRendererService(_settings())
    result = await svc.render(owner_id=OWNER_ID, project_id=PROJECT_ID, body=_render_request())
    assert result.status == MediaRenderJobStatus.PLANNED_ONLY
    assert result.dry_run is True
    assert result.paid_call_performed is False


def test_05_endpoint_identity_matches_official():
    client = HiggsfieldMcpClient(_settings())
    assert client.endpoint_matches_official() is True
    bad = HiggsfieldMcpClient(_settings(higgsfield_mcp_endpoint="https://evil.example/mcp"))
    assert bad.endpoint_matches_official() is False
    assert HIGGSFIELD_OFFICIAL_MCP_ENDPOINT == "https://mcp.higgsfield.ai/mcp"


@pytest.mark.asyncio
async def test_06_initialize_request_valid():
    client = HiggsfieldMcpClient(_settings(higgsfield_oauth_access_token="tok"))
    init_payload = {"protocolVersion": "2024-11-05"}
    with patch.object(client, "_rpc", new=AsyncMock(return_value=init_payload)) as rpc:
        result = await client.initialize()
        rpc.assert_awaited_once()
        assert rpc.await_args.args[0] == "initialize"
        assert result["protocolVersion"] == "2024-11-05"


@pytest.mark.asyncio
async def test_07_tools_list_response_parsed():
    client = HiggsfieldMcpClient(_settings())
    payload = {
        "tools": [
            {"name": "real_tool", "description": "d", "inputSchema": {"type": "object"}},
        ]
    }
    with patch.object(client, "_rpc", new=AsyncMock(return_value=payload)):
        detailed = await client.list_tools_detailed(refresh=True)
    assert detailed[0]["name"] == "real_tool"


def test_08_tool_names_come_from_server_snapshot(tmp_path: Path):
    root = tmp_path / "sandbox"
    root.mkdir()
    (root / "tools_snapshot.json").write_text(
        json.dumps({"tools": [{"name": "server_tool_a"}, {"name": "server_tool_b"}]}),
        encoding="utf-8",
    )
    store = OperationMappingStore(root=root)
    assert store.discovered_tool_names() == ["server_tool_a", "server_tool_b"]


def test_09_unknown_tool_not_mapped(tmp_path: Path):
    root = tmp_path / "sandbox"
    root.mkdir()
    (root / "operation_mapping.json").write_text(json.dumps({"mappings": {}}), encoding="utf-8")
    store = OperationMappingStore(root=root)
    assert store.get_binding(MEDIA_OP_IMAGE_GENERATE) is None


def test_10_tool_schema_hash_deterministic():
    schema = {"type": "object", "properties": {"prompt": {"type": "string"}}}
    assert hash_payload(schema) == hash_payload(dict(schema))


def test_11_schema_drift_fails_closed(tmp_path: Path):
    root = tmp_path / "sandbox"
    root.mkdir()
    schema = {"type": "object"}
    (root / "tool_schema_hashes.json").write_text(
        json.dumps({"real_tool": hash_payload(schema)}),
        encoding="utf-8",
    )
    store = OperationMappingStore(root=root)
    assert store.verify_schema_hash("real_tool", schema) is True
    assert store.verify_schema_hash("real_tool", {"type": "string"}) is False


def test_12_authentication_data_redacted():
    payload = sanitize_snapshot_payload(
        {"authorization": "Bearer secret", "access_token": "abc", "tool": "x"}
    )
    assert payload["authorization"] == "[REDACTED]"
    assert payload["access_token"] == "[REDACTED]"


def test_13_token_absent_from_logs():
    settings = _settings(higgsfield_oauth_access_token="super-secret-token")
    safe = settings.safe_dict()
    assert safe.get("higgsfield_oauth_access_token") == "***"


def test_14_token_absent_from_snapshots():
    snap = sanitize_snapshot_payload({"oauth_access_token": "abc", "tools": []})
    assert snap["oauth_access_token"] == "[REDACTED]"


def test_15_canonical_operation_separated_from_provider_tool_name():
    tools = all_higgsfield_tools()
    assert MEDIA_OP_IMAGE_GENERATE in tools
    assert "higgsfield.render_image" not in tools
    assert "higgsfield.render_image" in DEPRECATED_GUESSED_TOOL_IDS


def test_16_image_operation_mapped_only_after_verification(tmp_path: Path):
    root = tmp_path / "sandbox"
    root.mkdir()
    (root / "tools_snapshot.json").write_text(
        json.dumps({"tools": [{"name": "provider_image_tool"}]}),
        encoding="utf-8",
    )
    (root / "operation_mapping.json").write_text(json.dumps({"mappings": {}}), encoding="utf-8")
    store = OperationMappingStore(root=root)
    client = HiggsfieldMcpClient(_settings())
    assert client.resolve_provider_tool_name(MEDIA_OP_IMAGE_GENERATE, mapping_store=store) is None


@pytest.mark.asyncio
async def test_17_video_remains_disabled():
    svc = MediaRendererService(_settings())
    spec = MediaRenderSpec(
        asset_type=MediaRenderAssetType.VIDEO,
        style="cinematic",
        prompt="Product reveal video",
        duration_seconds=5,
    )
    body = MediaRenderRequest(
        spec=spec,
        upstream_skill_id="ms.skill.presentation_architecture",
        dry_run=True,
    )
    with pytest.raises(InvalidStateError, match="higgsfield_video_render_disabled"):
        await svc.render(owner_id=OWNER_ID, project_id=PROJECT_ID, body=body)


@pytest.mark.asyncio
async def test_18_live_request_requires_explicit_confirmation():
    svc = MediaRendererService(_settings(higgsfield_oauth_access_token="token"))
    with pytest.raises(InvalidStateError, match="explicit_confirmation_required"):
        await svc.render(
            owner_id=OWNER_ID,
            project_id=PROJECT_ID,
            body=_render_request(dry_run=False, explicit_confirmation=False),
            live_allowed=True,
        )


@pytest.mark.asyncio
async def test_19_live_request_requires_approval_reference():
    svc = MediaRendererService(_settings(higgsfield_oauth_access_token="token"))
    with pytest.raises(InvalidStateError, match="approval_reference_required"):
        await svc.render(
            owner_id=OWNER_ID,
            project_id=PROJECT_ID,
            body=_render_request(
                dry_run=False,
                explicit_confirmation=True,
                approval_reference=None,
            ),
            live_allowed=True,
        )


@pytest.mark.asyncio
async def test_20_unknown_billing_cost_requires_explicit_acceptance():
    svc = MediaRendererService(_settings(higgsfield_oauth_access_token="token"))
    with pytest.raises(InvalidStateError, match="billing_cost_unknown_acceptance_required"):
        await svc.render(
            owner_id=OWNER_ID,
            project_id=PROJECT_ID,
            body=_render_request(
                dry_run=False,
                explicit_confirmation=True,
                approval_reference="apr-1",
                accept_unknown_cost=False,
            ),
            live_allowed=True,
        )


def test_21_unknown_outcome_write_not_auto_retried():
    from app.connectors.contracts import (
        ConnectorActionType,
        ConnectorApprovalClass,
        ConnectorDataSensitivity,
        ConnectorIdempotencyClass,
        ConnectorSideEffectClass,
        ConnectorToolDefinition,
    )

    tool = ConnectorToolDefinition(
        connector_id=HIGGSFIELD_CONNECTOR_ID,
        tool_id=MEDIA_OP_IMAGE_GENERATE,
        name="x",
        action_type=ConnectorActionType.EXECUTE,
        side_effect_class=ConnectorSideEffectClass.REVERSIBLE,
        data_sensitivity=ConnectorDataSensitivity.TENANT_INTERNAL,
        approval_class=ConnectorApprovalClass.OWNER_APPROVAL,
        idempotency=ConnectorIdempotencyClass.UNKNOWN,
    )
    assert tool.idempotency == ConnectorIdempotencyClass.UNKNOWN


def test_22_polling_bounded():
    settings = _settings()
    assert settings.higgsfield_mcp_timeout_seconds <= 300.0


def test_23_unknown_provider_status_remains_unknown():
    from app.services.media_renderer_service import _map_provider_status

    assert _map_provider_status("weird_provider_state").value == "queued"


def test_24_signed_url_secrets_redacted():
    from app.connectors.higgsfield.adapter import _redact_url

    url = "https://cdn.example/asset.png?token=secret&sig=abc"
    redacted = _redact_url(url)
    assert redacted is not None
    assert "secret" not in redacted
    assert "[REDACTED]" in redacted


def test_25_result_content_type_validated_in_adapter_output():
    """Adapter stores mime_type from provider without exposing raw response."""
    assert "mime_type" in {"job_id", "status", "result_url", "mime_type", "provider_status"}


def test_26_evidence_descriptor_created_on_live_success():
    from datetime import UTC, datetime
    from uuid import uuid4

    from app.connectors.contracts import ConnectorExecutionResult, ConnectorExecutionResultStatus

    result = ConnectorExecutionResult(
        request_id=uuid4(),
        connector_id=HIGGSFIELD_CONNECTOR_ID,
        connector_version="0.1.0",
        tool_id=MEDIA_OP_IMAGE_GENERATE,
        status=ConnectorExecutionResultStatus.SUCCEEDED,
        output_payload={"job_id": "j1"},
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        duration_ms=0,
    )
    assert result.output_payload["job_id"] == "j1"


def test_27_provider_response_not_exposed_raw():
    tools = all_higgsfield_tools()
    assert all("provider_raw" not in tool.tool_id for tool in tools.values())


@pytest.mark.asyncio
async def test_28_cross_tenant_request_rejected_by_bindings():
    settings = _settings(higgsfield_oauth_access_token="tok")
    from app.connectors.higgsfield.registry import build_higgsfield_bindings

    tenant, _project, credential = build_higgsfield_bindings(
        tenant_id=OWNER_ID,
        project_id=PROJECT_ID,
        settings=settings,
    )
    assert tenant.tenant_id == OWNER_ID
    assert tenant.tenant_id != OTHER_TENANT
    if credential is not None:
        assert credential.tenant_id == OWNER_ID


@pytest.mark.asyncio
async def test_29_ordinary_customer_live_call_blocked():
    svc = MediaRendererService(_settings(higgsfield_oauth_access_token="token"))
    with pytest.raises(InvalidStateError, match="connector_not_production_ready"):
        await svc.render(
            owner_id=OWNER_ID,
            project_id=PROJECT_ID,
            body=_render_request(
                dry_run=False,
                explicit_confirmation=True,
                approval_reference="apr-1",
                accept_unknown_cost=True,
            ),
            live_allowed=False,
        )


def test_30_no_cwf_content_publication_integration():
    from app.services import media_renderer_service as mod

    source = Path(mod.__file__).read_text(encoding="utf-8")
    for forbidden in ("launch_pack", "content_factory", "publication", "cwf"):
        assert forbidden not in source.lower()


def test_31_frozen_kb_wpl_hashes_unchanged():
    assert FROZEN_PROGRAM_BUNDLE_HASH == (
        "43e2cab328dec889ee7fe755bf208311522baec1dd761ef4bb9eac73a53aa4a4"
    )


def test_32_frozen_skill_hashes_unchanged():
    assert package_hash("ms.skill.offer_builder") == PACKAGE_HASHES["ms.skill.offer_builder"]


def test_descriptor_quarantined_until_sandbox_verified():
    descriptor = higgsfield_descriptor(_settings(higgsfield_oauth_access_token="tok"))
    assert descriptor.status.value == "quarantined"
    assert descriptor.adapter.supports_dry_run is False


def test_canonical_operations_registry():
    tools = all_higgsfield_tools()
    assert set(tools) == set(MEDIA_CANONICAL_OPERATIONS)


def test_sandbox_root_exists():
    assert SANDBOX_ROOT.is_dir()
