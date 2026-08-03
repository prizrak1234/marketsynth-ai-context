"""CMVP.1 — immutable MCP tool call audit records."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from app.db.base import UUIDPrimaryKeyMixin, utc_now
from app.schemas.contracts import McpServerRole, McpToolCallStatus


class McpToolCallAuditTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "mcp_tool_call_audits"
    __table_args__ = (
        Index("ix_mcp_tool_call_audits_owner", "owner_id"),
        Index("ix_mcp_tool_call_audits_user_request", "user_request_id"),
        Index("ix_mcp_tool_call_audits_investigation", "investigation_id"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    tenant_id: UUID = Field(nullable=False)
    user_request_id: UUID = Field(foreign_key="user_requests.id", nullable=False)
    investigation_id: UUID | None = Field(default=None, foreign_key="investigations.id")
    server_role: McpServerRole = Field(max_length=32, nullable=False)
    server_id: str = Field(max_length=64, nullable=False)
    tool_name: str = Field(max_length=128, nullable=False)
    tool_schema_fingerprint: str = Field(max_length=128, nullable=False)
    status: McpToolCallStatus = Field(max_length=32, nullable=False)
    duration_ms: int = Field(default=0, nullable=False)
    response_size_bytes: int = Field(default=0, nullable=False)
    error_code: str | None = Field(default=None, max_length=128)
    request_summary: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    response_summary: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
