"""Repository for MCP tool call audit records."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.mcp_tool_call_audit import McpToolCallAuditTable


class McpToolCallAuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, row: McpToolCallAuditTable) -> McpToolCallAuditTable:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def list_for_user_request(
        self,
        owner_id: UUID,
        user_request_id: UUID,
    ) -> list[McpToolCallAuditTable]:
        stmt = (
            select(McpToolCallAuditTable)
            .where(
                McpToolCallAuditTable.owner_id == owner_id,
                McpToolCallAuditTable.user_request_id == user_request_id,
            )
            .order_by(McpToolCallAuditTable.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_for_investigation(
        self,
        owner_id: UUID,
        investigation_id: UUID,
    ) -> list[McpToolCallAuditTable]:
        stmt = (
            select(McpToolCallAuditTable)
            .where(
                McpToolCallAuditTable.owner_id == owner_id,
                McpToolCallAuditTable.investigation_id == investigation_id,
            )
            .order_by(McpToolCallAuditTable.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
