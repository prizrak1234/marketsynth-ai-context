"""Pilot browser session service — login/logout/revocation (CPH.3)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.base import ensure_naive_utc, utc_now
from app.db.models.browser_session import BrowserSessionTable
from app.db.models.user import UserTable
from app.db.repositories.browser_sessions import BrowserSessionRepository
from app.schemas.contracts import BrowserSessionStatus
from app.security.browser_sessions import generate_session_token, hash_session_token
from app.security.passwords import verify_password

log = get_logger(__name__)


@dataclass(frozen=True)
class LoginResult:
    user: UserTable
    session: BrowserSessionTable
    plain_token: str


class BrowserSessionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._sessions = BrowserSessionRepository(session)

    async def authenticate_token(self, plain_token: str) -> tuple[UserTable, BrowserSessionTable] | None:
        if not plain_token or not plain_token.startswith("mss_"):
            return None
        token_hash = hash_session_token(plain_token)
        row = await self._sessions.get_by_token_hash(token_hash)
        if row is None:
            return None
        now = ensure_naive_utc(utc_now())
        expires = ensure_naive_utc(row.expires_at)
        if row.status != BrowserSessionStatus.ACTIVE.value:
            return None
        if row.revoked_at is not None:
            return None
        if expires <= now:
            row.status = BrowserSessionStatus.EXPIRED.value
            await self._sessions.update(row)
            await self._session.commit()
            return None
        user = await self._session.get(UserTable, row.user_id)
        if user is None or not user.is_active:
            return None
        row.last_seen_at = now
        await self._sessions.update(row)
        await self._session.commit()
        return user, row

    async def login(
        self,
        *,
        email: str,
        password: str,
        user_agent: str | None,
    ) -> LoginResult | None:
        normalized = email.strip().lower()
        if not normalized:
            log.info("login_failure", reason="invalid_credentials")
            return None
        result = await self._session.execute(
            select(UserTable).where(UserTable.email == normalized)
        )
        user = result.scalar_one_or_none()
        # Constant-ish path: always verify something if possible
        if user is None or not user.password_hash:
            log.info("login_failure", reason="invalid_credentials")
            return None
        if not verify_password(password, user.password_hash):
            log.info("login_failure", reason="invalid_credentials", user_id=str(user.id))
            return None
        if not user.is_active:
            log.info("login_failure", reason="account_disabled", user_id=str(user.id))
            return None

        settings = get_settings()
        ttl = timedelta(hours=settings.browser_session_ttl_hours)
        plain, token_hash = generate_session_token()
        ua_hash = None
        if user_agent:
            ua_hash = hashlib.sha256(user_agent.encode("utf-8")).hexdigest()
        now = ensure_naive_utc(utc_now())
        row = BrowserSessionTable(
            user_id=user.id,
            token_hash=token_hash,
            status=BrowserSessionStatus.ACTIVE.value,
            purpose="pilot_browser",
            created_at=now,
            expires_at=now + ttl,
            last_seen_at=now,
            user_agent_hash=ua_hash,
            created_by="login",
        )
        await self._sessions.add(row)
        user.last_login_at = now
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(row)
        await self._session.refresh(user)
        log.info(
            "login_success",
            user_id=str(user.id),
            session_id=str(row.id),
            expires_at=row.expires_at.isoformat(),
        )
        return LoginResult(user=user, session=row, plain_token=plain)

    async def revoke_session(
        self, session_id: UUID, user_id: UUID, *, reason: str = "logout"
    ) -> BrowserSessionTable | None:
        row = await self._sessions.get_by_id_for_user(session_id, user_id)
        if row is None:
            return None
        if row.status == BrowserSessionStatus.REVOKED.value:
            return row
        now = utc_now()
        row.status = BrowserSessionStatus.REVOKED.value
        row.revoked_at = now
        await self._sessions.update(row)
        await self._session.commit()
        log.info(
            "session_revoked",
            session_id=str(session_id),
            user_id=str(user_id),
            reason=reason,
        )
        return row

    async def revoke_token(self, plain_token: str, *, reason: str = "logout") -> bool:
        token_hash = hash_session_token(plain_token)
        row = await self._sessions.get_by_token_hash(token_hash)
        if row is None:
            return False
        if row.status == BrowserSessionStatus.REVOKED.value:
            return True
        now = utc_now()
        row.status = BrowserSessionStatus.REVOKED.value
        row.revoked_at = now
        await self._sessions.update(row)
        await self._session.commit()
        log.info("logout", session_id=str(row.id), user_id=str(row.user_id), reason=reason)
        return True

    async def list_sessions(self, user_id: UUID) -> list[BrowserSessionTable]:
        return await self._sessions.list_for_user(user_id)

    async def revoke_all_for_user(self, user_id: UUID, *, reason: str = "password_reset") -> int:
        now = ensure_naive_utc(utc_now())
        result = await self._session.execute(
            update(BrowserSessionTable)
            .where(
                BrowserSessionTable.user_id == user_id,
                BrowserSessionTable.status == BrowserSessionStatus.ACTIVE.value,
            )
            .values(
                status=BrowserSessionStatus.REVOKED.value,
                revoked_at=now,
            )
        )
        await self._session.commit()
        count = int(result.rowcount or 0)
        if count:
            log.info(
                "sessions_revoked_for_user",
                user_id=str(user_id),
                count=count,
                reason=reason,
            )
        return count

    async def set_password(self, user_id: UUID, password_hash: str) -> UserTable | None:
        user = await self._session.get(UserTable, user_id)
        if user is None:
            return None
        user.password_hash = password_hash
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user
