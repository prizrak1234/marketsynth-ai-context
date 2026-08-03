"""Beta access gate API schemas (Phase AI.96)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.contracts import BetaAccessStatus


class BetaAccessResponse(BaseModel):
    status: BetaAccessStatus
    gate_enabled: bool = True
    can_use_mvp: bool = False
    safe_message: str | None = None


class BetaAdminUserAccessRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=1024)
