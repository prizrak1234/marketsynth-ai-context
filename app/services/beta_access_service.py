"""Beta access gate (Phase AI.96)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BetaAccessDeniedError, NotFoundError
from app.core.security import sanitize_text
from app.db.models.user import UserTable
from app.schemas.beta_access import BetaAccessResponse
from app.schemas.contracts import BetaAccessStatus, UserRole
from app.services.transaction import transactional
from app.schemas.crud import UserUpdate
from app.services.users_service import UserService


class BetaAccessService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserService(session)

    @staticmethod
    def gate_enabled() -> bool:
        settings = get_settings()
        return settings.beta_access_gate_enabled and not settings.beta_access_gate_bypass

    @staticmethod
    def mvp_access_allowed(user: UserTable) -> bool:
        settings = get_settings()
        if not settings.beta_access_gate_enabled or settings.beta_access_gate_bypass:
            return True
        if user.role in (UserRole.ADMIN, UserRole.OWNER):
            return True
        return user.beta_access_status == BetaAccessStatus.APPROVED

    @staticmethod
    def enforce_mvp_access(user: UserTable) -> None:
        if BetaAccessService.mvp_access_allowed(user):
            return
        if user.beta_access_status == BetaAccessStatus.BLOCKED:
            raise BetaAccessDeniedError(
                error_code="beta_access_blocked",
                safe_message="Beta access was revoked. Contact the team if you believe this is a mistake.",
            )
        raise BetaAccessDeniedError(
            error_code="beta_access_pending",
            safe_message="Beta access is pending approval. Check back after your invite is approved.",
        )

    @staticmethod
    def status_response(user: UserTable) -> BetaAccessResponse:
        allowed = BetaAccessService.mvp_access_allowed(user)
        gate = BetaAccessService.gate_enabled()
        safe_message: str | None = None
        if gate and not allowed:
            if user.beta_access_status == BetaAccessStatus.BLOCKED:
                safe_message = "Beta access was revoked."
            else:
                safe_message = "Waiting for beta approval."
        return BetaAccessResponse(
            status=user.beta_access_status,
            gate_enabled=gate,
            can_use_mvp=allowed,
            safe_message=safe_message,
        )

    async def approve(
        self,
        user_id: UUID,
        *,
        notes: str | None = None,
    ) -> UserTable:
        row = await self._users.get_by_id(user_id)
        if row is None:
            raise NotFoundError("User not found")
        cleaned_notes = sanitize_text(notes).strip()[:1024] if notes else None
        async with transactional(self._session):
            updated = await self._users.update(
                user_id,
                UserUpdate(
                    beta_access_status=BetaAccessStatus.APPROVED,
                    beta_notes=cleaned_notes,
                ),
            )
        if updated is None:
            raise NotFoundError("User not found")
        return updated

    async def block(
        self,
        user_id: UUID,
        *,
        notes: str | None = None,
    ) -> UserTable:
        row = await self._users.get_by_id(user_id)
        if row is None:
            raise NotFoundError("User not found")
        cleaned_notes = sanitize_text(notes).strip()[:1024] if notes else None
        async with transactional(self._session):
            updated = await self._users.update(
                user_id,
                UserUpdate(
                    beta_access_status=BetaAccessStatus.BLOCKED,
                    beta_notes=cleaned_notes,
                ),
            )
        if updated is None:
            raise NotFoundError("User not found")
        return updated
