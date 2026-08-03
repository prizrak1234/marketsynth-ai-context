"""Password reset service — request/status/complete; hash-only tokens."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.base import ensure_naive_utc, utc_now
from app.db.models.browser_session import BrowserSessionTable
from app.db.models.password_reset_token import PasswordResetTokenTable
from app.db.models.user import UserTable
from app.domain.email_normalize import is_valid_email, normalize_email
from app.schemas.contracts import BrowserSessionStatus
from app.security.passwords import hash_password
from app.security.reset_tokens import generate_reset_token, hash_reset_token

log = get_logger(__name__)

DEFAULT_RESET_TTL_MINUTES = 45
MIN_PASSWORD_LENGTH = 10
_WEAK = frozenset({"password", "password123", "1234567890", "qwerty1234", "letmein123"})


class ResetStatus(StrEnum):
    PENDING = "pending"
    USED = "used"
    EXPIRED = "expired"
    REVOKED = "revoked"


class ResetPublicState(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    USED = "used"
    REVOKED = "revoked"
    BACKEND_UNAVAILABLE = "backend_unavailable"


class PasswordResetError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class CreateResetResult:
    token_row: PasswordResetTokenTable
    plain_token: str
    user: UserTable


@dataclass(frozen=True)
class ResetStatusView:
    state: ResetPublicState


class PasswordResetService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def request_reset(
        self,
        *,
        email: str,
        client_ip: str | None,
        user_agent: str | None,
        ttl_minutes: int = DEFAULT_RESET_TTL_MINUTES,
    ) -> CreateResetResult | None:
        """Create reset if user exists. Caller always returns generic message."""
        email_n = normalize_email(email)
        if not is_valid_email(email_n):
            log.info("password_reset_requested", outcome="invalid_email")
            return None

        user = await self._find_user(email_n)
        if user is None or not user.is_active or not user.password_hash:
            log.info("password_reset_requested", outcome="no_matching_user")
            return None

        await self._revoke_pending_for_user(user.id)
        plain, token_hash = generate_reset_token()
        now = ensure_naive_utc(utc_now())
        ip_hash = None
        if client_ip:
            ip_hash = hashlib.sha256(client_ip.encode("utf-8")).hexdigest()
        ua_hash = None
        if user_agent:
            ua_hash = hashlib.sha256(user_agent.encode("utf-8")).hexdigest()

        row = PasswordResetTokenTable(
            user_id=user.id,
            token_hash=token_hash,
            status=ResetStatus.PENDING.value,
            expires_at=now + timedelta(minutes=ttl_minutes),
            created_at=now,
            updated_at=now,
            requested_ip_hash=ip_hash,
            requested_user_agent_hash=ua_hash,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        log.info(
            "password_reset_requested",
            outcome="created",
            user_id=str(user.id),
            reset_id=str(row.id),
            expires_at=row.expires_at.isoformat(),
        )
        return CreateResetResult(token_row=row, plain_token=plain, user=user)

    async def status_for_token(self, raw_token: str) -> ResetStatusView:
        row = await self._get_by_raw_token(raw_token)
        if row is None:
            log.info("password_reset_invalid", reason="unknown_token")
            return ResetStatusView(state=ResetPublicState.INVALID)
        return await self._public_status(row)

    async def complete(
        self,
        *,
        raw_token: str,
        new_password: str,
        new_password_confirm: str,
    ) -> UserTable:
        if new_password != new_password_confirm:
            raise PasswordResetError("password_mismatch")
        if len(new_password) < MIN_PASSWORD_LENGTH:
            raise PasswordResetError("password_too_short")
        if new_password.strip() == "" or new_password.lower() in _WEAK:
            raise PasswordResetError("password_too_weak")

        row = await self._get_by_raw_token(raw_token)
        if row is None:
            log.info("password_reset_invalid", reason="unknown_token")
            raise PasswordResetError("invalid_token")

        view = await self._public_status(row)
        if view.state == ResetPublicState.EXPIRED:
            log.info("password_reset_expired", reset_id=str(row.id))
            raise PasswordResetError("token_expired")
        if view.state == ResetPublicState.REVOKED:
            raise PasswordResetError("token_revoked")
        if view.state == ResetPublicState.USED:
            raise PasswordResetError("token_used")
        if view.state != ResetPublicState.VALID:
            raise PasswordResetError("invalid_token")

        user = await self._session.get(UserTable, row.user_id)
        if user is None or not user.is_active:
            raise PasswordResetError("invalid_token")

        try:
            pw_hash = hash_password(new_password)
        except ValueError as exc:
            raise PasswordResetError(str(exc)) from exc

        now = ensure_naive_utc(utc_now())
        # Atomic: password + revoke sessions + consume token
        user.password_hash = pw_hash
        self._session.add(user)

        await self._session.execute(
            update(BrowserSessionTable)
            .where(
                BrowserSessionTable.user_id == user.id,
                BrowserSessionTable.status == BrowserSessionStatus.ACTIVE.value,
            )
            .values(
                status=BrowserSessionStatus.REVOKED.value,
                revoked_at=now,
            )
        )

        row.status = ResetStatus.USED.value
        row.used_at = now
        row.updated_at = now
        self._session.add(row)

        await self._session.commit()
        await self._session.refresh(user)
        log.info(
            "password_reset_completed",
            user_id=str(user.id),
            reset_id=str(row.id),
        )
        return user

    async def _public_status(self, row: PasswordResetTokenTable) -> ResetStatusView:
        now = ensure_naive_utc(utc_now())
        if row.status == ResetStatus.REVOKED.value:
            return ResetStatusView(state=ResetPublicState.REVOKED)
        if row.status == ResetStatus.USED.value:
            return ResetStatusView(state=ResetPublicState.USED)
        if row.status == ResetStatus.EXPIRED.value or ensure_naive_utc(row.expires_at) <= now:
            if row.status == ResetStatus.PENDING.value:
                row.status = ResetStatus.EXPIRED.value
                row.updated_at = now
                self._session.add(row)
                await self._session.commit()
                log.info("password_reset_expired", reset_id=str(row.id))
            return ResetStatusView(state=ResetPublicState.EXPIRED)
        return ResetStatusView(state=ResetPublicState.VALID)

    async def _get_by_raw_token(self, raw_token: str) -> PasswordResetTokenTable | None:
        token = (raw_token or "").strip()
        if not token.startswith("mpr_") or len(token) < 20:
            return None
        token_hash = hash_reset_token(token)
        result = await self._session.execute(
            select(PasswordResetTokenTable).where(
                PasswordResetTokenTable.token_hash == token_hash
            )
        )
        return result.scalar_one_or_none()

    async def _find_user(self, email_n: str) -> UserTable | None:
        result = await self._session.execute(
            select(UserTable).where(UserTable.email == email_n)
        )
        return result.scalar_one_or_none()

    async def _revoke_pending_for_user(self, user_id: UUID) -> int:
        now = ensure_naive_utc(utc_now())
        result = await self._session.execute(
            update(PasswordResetTokenTable)
            .where(
                PasswordResetTokenTable.user_id == user_id,
                PasswordResetTokenTable.status == ResetStatus.PENDING.value,
            )
            .values(
                status=ResetStatus.REVOKED.value,
                revoked_at=now,
                updated_at=now,
            )
        )
        return int(result.rowcount or 0)
