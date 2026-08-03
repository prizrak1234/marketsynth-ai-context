"""Auth-related request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.contracts import BrowserSessionStatus, UserRole


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class ApiKeyCreatedResponse(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    api_key: str


class ApiKeyListItem(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None


class BrowserLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=10, max_length=256)


class AuthMeResponse(BaseModel):
    id: UUID
    email: str | None
    display_name: str | None
    role: UserRole
    is_active: bool
    last_login_at: datetime | None = None


class BrowserLoginResponse(BaseModel):
    user: AuthMeResponse
    session_id: UUID
    expires_at: datetime
    auth_method: str = "browser_session"


class BrowserSessionListItem(BaseModel):
    id: UUID
    status: BrowserSessionStatus
    purpose: str
    created_at: datetime
    expires_at: datetime
    last_seen_at: datetime | None
    revoked_at: datetime | None


class PilotInviteCreateRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    ttl_hours: int = Field(default=48, ge=1, le=168)
    replace_pending: bool = False


class PilotInviteCreateResponse(BaseModel):
    invite_id: UUID
    email: str
    expires_at: datetime
    activation_url: str
    # Shown once — not persisted; clients must not log it.
    token: str


class PilotInviteStatusResponse(BaseModel):
    state: str
    email: str | None = None
    expires_at: datetime | None = None


class PilotInviteAcceptRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=10, max_length=256)
    password_confirm: str = Field(min_length=10, max_length=256)
    accept_pilot_notice: bool = False


class PilotInviteAcceptResponse(BaseModel):
    user: AuthMeResponse
    session_id: UUID
    expires_at: datetime
    auth_method: str = "browser_session"


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=10, max_length=256)
    password_confirmation: str = Field(min_length=10, max_length=256)
    accepted_pilot_notice: bool = False


class RegisterResponse(BaseModel):
    user: AuthMeResponse
    session_id: UUID
    expires_at: datetime
    auth_method: str = "browser_session"


class SignupStatusResponse(BaseModel):
    signup_enabled: bool
    invite_activation_available: bool = True


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=10, max_length=256)
    new_password_confirmation: str = Field(min_length=10, max_length=256)


class ChangePasswordResponse(BaseModel):
    ok: bool = True
    revoked_other_sessions: int = 0


class PasswordResetRequestBody(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class PasswordResetRequestResponse(BaseModel):
    message: str = (
        "If an account exists, password reset instructions have been created."
    )


class PasswordResetStatusResponse(BaseModel):
    state: str


class PasswordResetCompleteRequest(BaseModel):
    password: str = Field(min_length=10, max_length=256)
    password_confirmation: str = Field(min_length=10, max_length=256)


class PasswordResetCompleteResponse(BaseModel):
    ok: bool = True
