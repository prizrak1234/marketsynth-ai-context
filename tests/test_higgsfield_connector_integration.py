"""CONN-HF-01 — Higgsfield MCP connector integration tests (updated for CONN-HF-01.1)."""

from __future__ import annotations

import json
from uuid import UUID

import pytest
from app.connectors.higgsfield.constants import (
    HIGGSFIELD_CONNECTOR_ID,
    MEDIA_OP_IMAGE_GENERATE,
)
from app.connectors.higgsfield.descriptor import higgsfield_descriptor
from app.connectors.higgsfield.mcp_client import HiggsfieldMcpClient
from app.connectors.higgsfield.sandbox.operation_mapping import OperationMappingStore
from app.core.config import Settings
from app.core.exceptions import InvalidStateError
from app.schemas.contracts import (
    MediaRenderAssetType,
    MediaRenderJobStatus,
    MediaRenderRequest,
    MediaRenderSpec,
)
from app.services.media_renderer_service import MediaRendererService

PROJECT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
OWNER_ID = UUID("11111111-1111-1111-1111-111111111111")


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
        prompt="A clean product hero shot on white background",
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


def test_higgsfield_descriptor_quarantined_when_disabled():
    descriptor = higgsfield_descriptor(_settings(higgsfield_mcp_enabled=False))
    assert descriptor.connector_id == HIGGSFIELD_CONNECTOR_ID
    assert descriptor.status.value == "quarantined"


def test_higgsfield_descriptor_quarantined_until_sandbox_verified():
    descriptor = higgsfield_descriptor(
        _settings(higgsfield_oauth_access_token="test-token-abc")
    )
    assert descriptor.status.value == "quarantined"
    assert descriptor.is_mcp is True
    assert descriptor.adapter.supports_dry_run is False


def test_mcp_client_resolve_tool_name_only_from_verified_mapping(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    (root / "tools_snapshot.json").write_text(
        '{"tools":[{"name":"generate_image"}]}',
        encoding="utf-8",
    )
    (root / "operation_mapping.json").write_text(
        json.dumps(
            {
                "mappings": {
                    MEDIA_OP_IMAGE_GENERATE: {
                        "provider_tool_name": "generate_image",
                        "tool_schema_hash": "abc123",
                        "enabled": True,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (root / "tool_schema_hashes.json").write_text('{"generate_image":"abc123"}', encoding="utf-8")
    store = OperationMappingStore(root=root)
    client = HiggsfieldMcpClient(_settings())
    name = client.resolve_provider_tool_name(MEDIA_OP_IMAGE_GENERATE, mapping_store=store)
    assert name == "generate_image"


@pytest.mark.asyncio
async def test_media_renderer_dry_run_render_plan_only():
    svc = MediaRendererService(_settings())
    result = await svc.render(
        owner_id=OWNER_ID,
        project_id=PROJECT_ID,
        body=_render_request(),
    )
    assert result.status == MediaRenderJobStatus.PLANNED_ONLY
    assert result.dry_run is True
    assert result.paid_call_performed is False
    assert result.job_id == ""


@pytest.mark.asyncio
async def test_media_renderer_rejects_unknown_upstream_skill():
    svc = MediaRendererService(_settings())
    with pytest.raises(InvalidStateError, match="upstream_skill_not_allowed"):
        await svc.render(
            owner_id=OWNER_ID,
            project_id=PROJECT_ID,
            body=_render_request(upstream_skill_id="ms.skill.offer_builder"),
        )


@pytest.mark.asyncio
async def test_media_renderer_live_requires_explicit_confirmation():
    svc = MediaRendererService(_settings(higgsfield_oauth_access_token="token-xyz"))
    with pytest.raises(InvalidStateError, match="explicit_confirmation_required"):
        await svc.render(
            owner_id=OWNER_ID,
            project_id=PROJECT_ID,
            body=_render_request(dry_run=False, explicit_confirmation=False),
        )


@pytest.mark.asyncio
async def test_media_renderer_readiness_when_disabled():
    svc = MediaRendererService(_settings(higgsfield_mcp_enabled=False))
    readiness = await svc.readiness()
    assert readiness.enabled is False
    assert readiness.image_render_available is False
    assert readiness.sandbox_verified is False


@pytest.mark.asyncio
async def test_media_renderer_video_blocked_without_gate():
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


def test_connector_tools_use_canonical_operations():
    from app.connectors.higgsfield.descriptor import all_higgsfield_tools

    tools = all_higgsfield_tools()
    render = tools[MEDIA_OP_IMAGE_GENERATE]
    assert render.billing_sensitive is True
    assert render.action_type.value == "execute"
    assert "render_spec_hash" in render.evidence_requirements
