"""UserRequest persistence — home conversational intake (Phase H1 + H2.5)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from app.db.base import UUIDPrimaryKeyMixin, utc_now
from app.schemas.contracts import (
    UserRequestExecutionReadiness,
    UserRequestRouteCategory,
    UserRequestRouteKind,
    UserRequestStatus,
)


class UserRequestTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "user_requests"

    owner_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)
    text: str = Field(max_length=8000, nullable=False)
    normalized_text: str = Field(default="", max_length=8000, nullable=False)
    selected_scenario: str | None = Field(default=None, max_length=64)
    route_category: UserRequestRouteCategory = Field(
        default=UserRequestRouteCategory.GENERAL,
        nullable=False,
        index=True,
    )
    route_kind: UserRequestRouteKind = Field(
        default=UserRequestRouteKind.CLARIFY,
        nullable=False,
    )
    route_confidence: float = Field(default=0.0, nullable=False)
    status: UserRequestStatus = Field(
        default=UserRequestStatus.SUBMITTED,
        nullable=False,
        index=True,
    )
    clarification_question: str | None = Field(default=None, max_length=2000)
    clarification_answer: str | None = Field(default=None, max_length=4000)
    project_id: UUID | None = Field(default=None, foreign_key="projects.id", index=True)
    task_id: UUID | None = Field(default=None, foreign_key="tasks.id", index=True)
    assigned_specialist: str | None = Field(default=None, max_length=64)
    requires_project: bool = Field(default=False, nullable=False)
    avoids_investigation: bool = Field(default=False, nullable=False)
    next_href: str | None = Field(default=None, max_length=512)
    next_action_label: str | None = Field(default=None, max_length=256)
    assistant_message: str = Field(default="", max_length=4000, nullable=False)
    title: str = Field(default="", max_length=512, nullable=False)
    source: str = Field(default="home_conversation", max_length=64, nullable=False)
    # Phase H2.5 skill / knowledge context
    skill_code: str | None = Field(default=None, max_length=128)
    skill_version: str | None = Field(default=None, max_length=32)
    capability_pack_code: str | None = Field(default=None, max_length=128)
    capability_pack_version: str | None = Field(default=None, max_length=32)
    knowledge_snapshot_id: UUID | None = Field(
        default=None,
        foreign_key="knowledge_snapshots.id",
    )
    knowledge_snapshot_hash: str | None = Field(default=None, max_length=128)
    execution_readiness: UserRequestExecutionReadiness = Field(
        default=UserRequestExecutionReadiness.NOT_APPLICABLE,
        nullable=False,
    )
    missing_inputs: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    quality_profile_code: str | None = Field(default=None, max_length=128)
    skill_inputs: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    generated_visual_asset_ids: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    generation_status: str | None = Field(default=None, max_length=64)
    generation_warnings: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    # Phase H2.7 — content.telegram_post draft execution (draft-only lineage)
    content_draft: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    content_draft_lineage: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    content_draft_review_status: str | None = Field(default=None, max_length=32)
    prompt_package_hash: str | None = Field(default=None, max_length=128)
    prompt_package_version: str | None = Field(default=None, max_length=32)
    execution_provider: str | None = Field(default=None, max_length=32)
    execution_model: str | None = Field(default=None, max_length=128)
    # Chat golden path — idempotency + lineage
    client_message_id: str | None = Field(default=None, max_length=128, index=True)
    idempotency_key: str | None = Field(default=None, max_length=128, index=True)
    conversation_id: UUID | None = Field(default=None, index=True)
    sequence_number: int | None = Field(default=None)
    assistant_run_id: UUID | None = Field(default=None)
    routing_decision_id: UUID | None = Field(default=None)
    chat_route: str | None = Field(default=None, max_length=64)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
