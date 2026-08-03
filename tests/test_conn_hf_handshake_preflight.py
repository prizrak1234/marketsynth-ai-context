"""CONN-HF-01.1L — Handshake preflight dry tests (no live MCP traffic)."""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from app.connectors.higgsfield.sandbox.handshake import HiggsfieldSandboxHandshake
from app.connectors.higgsfield.sandbox.snapshot import (
    sanitize_snapshot_payload,
    write_sandbox_artifacts,
)
from app.core.config import Settings

FAKE_TOKEN = "hf_test_secret_token_abc123xyz_should_never_leak"
FAKE_BEARER_HEADER = f"Bearer {FAKE_TOKEN}"


def _settings(**overrides) -> Settings:
    base = {
        "higgsfield_mcp_enabled": True,
        "higgsfield_oauth_access_token": FAKE_TOKEN,
        "higgsfield_mcp_timeout_seconds": 5,
    }
    base.update(overrides)
    return Settings(**base)


def test_sanitize_redacts_token_like_keys() -> None:
    payload = {
        "access_token": FAKE_TOKEN,
        "Authorization": FAKE_BEARER_HEADER,
        "cookie": "session=secret",
        "safe_field": "visible",
        "nested": {"refresh_token": FAKE_TOKEN},
    }
    cleaned = sanitize_snapshot_payload(payload)
    assert FAKE_TOKEN not in json.dumps(cleaned)
    assert cleaned["safe_field"] == "visible"
    assert cleaned["access_token"] == "[REDACTED]"


def test_sanitize_redacts_signed_url_query_secrets() -> None:
    url = "https://cdn.example.com/asset.png?sig=secret123&token=abc"
    cleaned = sanitize_snapshot_payload(url)
    assert "secret123" not in cleaned
    assert "abc" not in cleaned or "[REDACTED]" in cleaned


def test_write_sandbox_artifacts_never_contains_token(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.connectors.higgsfield.sandbox.snapshot.SANDBOX_ROOT",
        tmp_path,
    )
    write_sandbox_artifacts(
        server_capabilities={"endpoint": "https://mcp.higgsfield.ai/mcp", "token": FAKE_TOKEN},
        tools_snapshot={"tools": [{"name": "t", "auth": FAKE_BEARER_HEADER}]},
        tool_schema_hashes={"t": "abc"},
        operation_mapping={"status": "tools_discovered_pending_mapping"},
        authentication_findings={"mechanism": "bearer_token_env"},
        freeze_manifest={"status": "tools_discovered_pending_mapping"},
    )
    for path in tmp_path.glob("*.json"):
        text = path.read_text(encoding="utf-8")
        assert FAKE_TOKEN not in text
        assert FAKE_BEARER_HEADER not in text


@pytest.mark.asyncio
async def test_handshake_stdout_never_contains_token() -> None:
    settings = _settings()
    handshake = HiggsfieldSandboxHandshake(settings)
    fake_init = {"protocolVersion": "2024-11-05", "serverInfo": {"name": "hf"}}
    fake_tools = [{"name": "image_gen", "description": "gen", "inputSchema": {"type": "object"}}]

    with (
        patch.object(handshake._client, "initialize", new=AsyncMock(return_value=fake_init)),
        patch.object(
            handshake._client,
            "list_tools_detailed",
            new=AsyncMock(return_value=fake_tools),
        ),
        patch(
            "app.connectors.higgsfield.sandbox.handshake.write_sandbox_artifacts",
        ) as write_mock,
    ):
        buf = io.StringIO()
        with redirect_stdout(buf):
            result = await handshake.run()
        output = buf.getvalue() + json.dumps(result)
        assert FAKE_TOKEN not in output
        write_mock.assert_called_once()
        written = write_mock.call_args.kwargs
        serialized = json.dumps(written)
        assert FAKE_TOKEN not in serialized


@pytest.mark.asyncio
async def test_handshake_does_not_call_tools_call() -> None:
    settings = _settings()
    handshake = HiggsfieldSandboxHandshake(settings)
    with (
        patch.object(
            handshake._client,
            "initialize",
            new=AsyncMock(return_value={"protocolVersion": "2024-11-05"}),
        ),
        patch.object(handshake._client, "list_tools_detailed", new=AsyncMock(return_value=[])),
        patch.object(handshake._client, "call_tool", new=AsyncMock()) as call_mock,
        patch("app.connectors.higgsfield.sandbox.handshake.write_sandbox_artifacts"),
    ):
        await handshake.run()
        call_mock.assert_not_called()


def test_handshake_script_documents_token_safety() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "scripts" / "higgsfield_mcp_sandbox_handshake.py"
    text = script.read_text(encoding="utf-8")
    assert "HIGGSFIELD_OAUTH_ACCESS_TOKEN" in text
    assert "Does not print access tokens" in text