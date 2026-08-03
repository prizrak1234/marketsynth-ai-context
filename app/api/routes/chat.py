"""Chat API (Phase AI.19) — alias paths under /projects/{project_id}/chat."""

from __future__ import annotations

from app.api.routes import agent_chat as agent_chat_routes
from app.schemas.agent_chat import (
    AgentChatMessageSearchHit,
    AgentChatMetricsResponse,
    AgentChatSendResponse,
    ChatAuditEventRead,
    ChatBlockActionResponse,
)
from app.schemas.contracts import AgentChatMessage, AgentChatSession, AgentChatSessionListItem
from fastapi import APIRouter, status

router = APIRouter(
    prefix="/projects/{project_id}/chat",
    tags=["chat"],
)

router.post(
    "",
    response_model=AgentChatSendResponse,
    status_code=status.HTTP_200_OK,
    name="send_chat_message",
)(agent_chat_routes.send_agent_chat_message)

router.get(
    "/sessions",
    response_model=list[AgentChatSessionListItem],
    name="list_chat_sessions",
)(agent_chat_routes.list_agent_chat_sessions)

router.get(
    "/sessions/{session_id}/messages",
    response_model=list[AgentChatMessage],
    name="list_chat_messages",
)(agent_chat_routes.list_agent_chat_messages)

router.get(
    "/metrics",
    response_model=AgentChatMetricsResponse,
    name="get_chat_metrics",
)(agent_chat_routes.get_agent_chat_metrics)

router.get(
    "/audit-events",
    response_model=list[ChatAuditEventRead],
    name="list_chat_audit_events",
)(agent_chat_routes.list_agent_chat_audit_events)

router.get(
    "/search-messages",
    response_model=list[AgentChatMessageSearchHit],
    name="search_chat_messages",
)(agent_chat_routes.search_agent_chat_messages)

router.post(
    "/block-actions",
    response_model=ChatBlockActionResponse,
    status_code=status.HTTP_200_OK,
    name="execute_chat_block_action",
)(agent_chat_routes.execute_chat_block_action)

router.post(
    "/sessions/{session_id}/archive",
    response_model=AgentChatSession,
    status_code=status.HTTP_200_OK,
    name="archive_chat_session",
)(agent_chat_routes.archive_agent_chat_session)
