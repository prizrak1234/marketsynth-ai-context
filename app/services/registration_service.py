"""Pilot self-registration — member only; invite remains optional."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.base import ensure_naive_utc, utc_now
from app.db.models.browser_session import BrowserSessionTable
from app.db.models.user import UserTable
from app.db.repositories.browser_sessions import BrowserSessionRepository
from app.domain.email_normalize import is_valid_email, normalize_email
from app.schemas.contracts import BetaAccessStatus, BrowserSessionStatus, UserRole
from app.security.browser_sessions import generate_session_token
from app.security.passwords import hash_password, verify_password

log = get_logger(__name__)

MIN_PASSWORD_LENGTH = 10
_WEAK = frozenset(
    {
        "password",
        "password123",
        "1234567890",
        "qwerty1234",
        "letmein123",
    }
)


class RegistrationError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class RegisterResult:
    user: UserTable
    session: BrowserSessionTable
    plain_token: str


class RegistrationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._sessions = BrowserSessionRepository(session)

    async def register(
        self,
        *,
        email: str,
        display_name: str,
        password: str,
        password_confirm: str,
        accept_notice: bool,
        user_agent: str | None,
    ) -> RegisterResult:
        settings = get_settings()
        if not settings.signup_enabled:
            raise RegistrationError("signup_disabled")
        if not accept_notice:
            raise RegistrationError("notice_required")
        if password != password_confirm:
            raise RegistrationError("password_mismatch")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise RegistrationError("password_too_short")
        if password.strip() == "" or password.lower() in _WEAK:
            raise RegistrationError("password_too_weak")

        email_n = normalize_email(email)
        if not is_valid_email(email_n):
            raise RegistrationError("invalid_email")

        name = display_name.strip()[:255]
        if len(name) < 1:
            raise RegistrationError("display_name_required")

        existing = await self._find_by_email(email_n)
        if existing is not None:
            raise RegistrationError("email_taken")

        try:
            pw_hash = hash_password(password)
        except ValueError as exc:
            raise RegistrationError(str(exc)) from exc

        now = ensure_naive_utc(utc_now())
        beta = (
            BetaAccessStatus.APPROVED
            if settings.public_signup_auto_approve_beta
            else BetaAccessStatus.PENDING
        )
        # Hard-coded MEMBER — never accept role from client.
        user = UserTable(
            email=email_n,
            display_name=name,
            role=UserRole.MEMBER,
            is_active=True,
            beta_access_status=beta,
            password_hash=pw_hash,
            email_verified_at=None,
            last_login_at=now,
        )
        self._session.add(user)
        await self._session.flush()

        ttl = timedelta(hours=settings.browser_session_ttl_hours)
        plain, token_hash = generate_session_token()
        ua_hash = None
        if user_agent:
            ua_hash = hashlib.sha256(user_agent.encode("utf-8")).hexdigest()
        row = BrowserSessionTable(
            user_id=user.id,
            token_hash=token_hash,
            status=BrowserSessionStatus.ACTIVE.value,
            purpose="pilot_browser",
            created_at=now,
            expires_at=now + ttl,
            last_seen_at=now,
            user_agent_hash=ua_hash,
            created_by="register",
        )
        await self._sessions.add(row)
        await self._session.commit()
        await self._session.refresh(user)
        await self._session.refresh(row)

        log.info(
            "user_registered",
            user_id=str(user.id),
            role=UserRole.MEMBER.value,
            session_id=str(row.id),
        )
        return RegisterResult(user=user, session=row, plain_token=plain)

    async def change_password(
        self,
        *,
        user: UserTable,
        current_password: str,
        new_password: str,
        new_password_confirm: str,
        current_session_id: UUID | None,
    ) -> int:
        if new_password != new_password_confirm:
            raise RegistrationError("password_mismatch")
        if len(new_password) < MIN_PASSWORD_LENGTH:
            raise RegistrationError("password_too_short")
        if new_password.strip() == "" or new_password.lower() in _WEAK:
            raise RegistrationError("password_too_weak")
        if not user.password_hash or not verify_password(current_password, user.password_hash):
            raise RegistrationError("current_password_invalid")

        try:
            user.password_hash = hash_password(new_password)
        except ValueError as exc:
            raise RegistrationError(str(exc)) from exc
        self._session.add(user)
        await self._session.commit()

        # Revoke all other sessions; keep current if known
        from sqlalchemy import update

        now = ensure_naive_utc(utc_now())
        stmt = (
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
        if current_session_id is not None:
            stmt = stmt.where(BrowserSessionTable.id != current_session_id)
        result = await self._session.execute(stmt)
        await self._session.commit()
        revoked = int(result.rowcount or 0)
        log.info(
            "password_changed",
            user_id=str(user.id),
            revoked_other_sessions=revoked,
        )
        return revoked

    async def _find_by_email(self, email_n: str) -> UserTable | None:
        result = await self._session.execute(
            select(UserTable).where(UserTable.email == email_n)
        )
        return result.scalar_one_or_none()
