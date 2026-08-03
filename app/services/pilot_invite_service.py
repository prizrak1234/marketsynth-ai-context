"""Pilot invitation service — create, status, accept, revoke."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.base import ensure_naive_utc, utc_now
from app.db.models.browser_session import BrowserSessionTable
from app.db.models.pilot_invite import PilotInviteTable
from app.db.models.user import UserTable
from app.db.repositories.browser_sessions import BrowserSessionRepository
from app.domain.email_normalize import normalize_email
from app.schemas.contracts import BetaAccessStatus, BrowserSessionStatus, UserRole
from app.security.browser_sessions import generate_session_token
from app.security.invite_tokens import generate_invite_token, hash_invite_token
from app.security.passwords import hash_password

log = get_logger(__name__)

DEFAULT_INVITE_TTL_HOURS = 48
MIN_PASSWORD_LENGTH = 10


class InviteStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class InvitePublicState(StrEnum):
    """Safe status for activation UI — no account enumeration beyond token possession."""

    LOADING = "loading"
    VALID = "valid"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ALREADY_USED = "already_used"
    INVALID = "invalid"
    ACCOUNT_EXISTS = "account_exists"
    BACKEND_UNAVAILABLE = "backend_unavailable"


@dataclass(frozen=True)
class CreateInviteResult:
    invite: PilotInviteTable
    plain_token: str


@dataclass(frozen=True)
class InviteStatusView:
    state: InvitePublicState
    email: str | None = None
    expires_at: datetime | None = None
    invite_id: UUID | None = None


@dataclass(frozen=True)
class AcceptInviteResult:
    user: UserTable
    session: BrowserSessionTable
    plain_token: str
    invite: PilotInviteTable


class PilotInviteError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class PilotInviteService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._sessions = BrowserSessionRepository(session)

    async def create_invite(
        self,
        *,
        email: str,
        created_by_user_id: UUID | None,
        ttl_hours: int = DEFAULT_INVITE_TTL_HOURS,
        replace_pending: bool = False,
        grant_role: UserRole = UserRole.MEMBER,
    ) -> CreateInviteResult:
        if ttl_hours < 1 or ttl_hours > 168:
            raise PilotInviteError("invalid_ttl")
        email_n = normalize_email(email)
        if "@" not in email_n or len(email_n) < 3:
            raise PilotInviteError("invalid_email")
        if grant_role not in {UserRole.MEMBER, UserRole.OWNER}:
            raise PilotInviteError("invalid_grant_role")

        existing = await self._find_user_by_email(email_n)
        if existing is not None:
            raise PilotInviteError("account_exists")

        pending = await self._pending_for_email(email_n)
        if pending and not replace_pending:
            raise PilotInviteError("pending_invite_exists")
        if pending and replace_pending:
            now = ensure_naive_utc(utc_now())
            pending.status = InviteStatus.REVOKED.value
            pending.revoked_at = now
            pending.updated_at = now
            self._session.add(pending)

        plain, token_hash = generate_invite_token()
        now = ensure_naive_utc(utc_now())
        invite = PilotInviteTable(
            email_normalized=email_n,
            token_hash=token_hash,
            status=InviteStatus.PENDING.value,
            grant_role=grant_role.value,
            expires_at=now + timedelta(hours=ttl_hours),
            created_by_user_id=created_by_user_id,
            created_at=now,
            updated_at=now,
        )
        self._session.add(invite)
        await self._session.commit()
        await self._session.refresh(invite)
        log.info(
            "pilot_invite_created",
            invite_id=str(invite.id),
            email=email_n,
            expires_at=invite.expires_at.isoformat(),
            replaced=bool(pending and replace_pending),
            grant_role=grant_role.value,
        )
        return CreateInviteResult(invite=invite, plain_token=plain)

    async def status_for_token(self, raw_token: str) -> InviteStatusView:
        invite = await self._get_by_raw_token(raw_token)
        if invite is None:
            return InviteStatusView(state=InvitePublicState.INVALID)
        return await self._public_status(invite)

    async def accept(
        self,
        *,
        raw_token: str,
        display_name: str,
        password: str,
        password_confirm: str,
        accept_notice: bool,
        user_agent: str | None,
    ) -> AcceptInviteResult:
        if not accept_notice:
            raise PilotInviteError("notice_required")
        if password != password_confirm:
            raise PilotInviteError("password_mismatch")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise PilotInviteError("password_too_short")
        if password.strip() == "" or password.lower() in {"password", "1234567890"}:
            raise PilotInviteError("password_too_weak")

        name = display_name.strip()[:255]
        if len(name) < 1:
            raise PilotInviteError("display_name_required")

        invite = await self._get_by_raw_token(raw_token)
        if invite is None:
            raise PilotInviteError("invalid_token")

        view = await self._public_status(invite)
        if view.state == InvitePublicState.EXPIRED:
            raise PilotInviteError("invite_expired")
        if view.state == InvitePublicState.REVOKED:
            raise PilotInviteError("invite_revoked")
        if view.state == InvitePublicState.ALREADY_USED:
            raise PilotInviteError("invite_used")
        if view.state == InvitePublicState.ACCOUNT_EXISTS:
            raise PilotInviteError("account_exists")
        if view.state != InvitePublicState.VALID:
            raise PilotInviteError("invalid_token")

        existing = await self._find_user_by_email(invite.email_normalized)
        if existing is not None:
            raise PilotInviteError("account_exists")

        try:
            pw_hash = hash_password(password)
        except ValueError as exc:
            raise PilotInviteError(str(exc)) from exc

        now = ensure_naive_utc(utc_now())
        role = UserRole.MEMBER
        if (invite.grant_role or "").lower() == UserRole.OWNER.value:
            role = UserRole.OWNER
        user = UserTable(
            email=invite.email_normalized,
            display_name=name,
            role=role,
            is_active=True,
            beta_access_status=BetaAccessStatus.APPROVED,
            password_hash=pw_hash,
            email_verified_at=now,
            last_login_at=now,
        )
        self._session.add(user)
        await self._session.flush()

        invite.status = InviteStatus.ACCEPTED.value
        invite.accepted_at = now
        invite.accepted_by_user_id = user.id
        invite.updated_at = now
        self._session.add(invite)

        settings = get_settings()
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
            created_by="invite_accept",
        )
        await self._sessions.add(row)

        await self._session.commit()
        await self._session.refresh(user)
        await self._session.refresh(row)
        await self._session.refresh(invite)

        log.info(
            "pilot_invite_accepted",
            invite_id=str(invite.id),
            user_id=str(user.id),
            session_id=str(row.id),
        )
        return AcceptInviteResult(
            user=user, session=row, plain_token=plain, invite=invite
        )

    async def revoke_pending_for_email(self, email: str) -> int:
        """Revoke all pending invites for email (compromised-token recovery)."""
        email_n = normalize_email(email)
        result = await self._session.execute(
            select(PilotInviteTable).where(
                PilotInviteTable.email_normalized == email_n,
                PilotInviteTable.status == InviteStatus.PENDING.value,
            )
        )
        rows = list(result.scalars().all())
        now = ensure_naive_utc(utc_now())
        for invite in rows:
            invite.status = InviteStatus.REVOKED.value
            invite.revoked_at = now
            invite.updated_at = now
            self._session.add(invite)
        if rows:
            await self._session.commit()
            log.info(
                "pilot_invites_revoked_for_email",
                email=email_n,
                count=len(rows),
            )
        return len(rows)

    async def revoke(
        self, invite_id: UUID, *, actor_user_id: UUID
    ) -> PilotInviteTable | None:
        invite = await self._session.get(PilotInviteTable, invite_id)
        if invite is None:
            return None
        if invite.status != InviteStatus.PENDING.value:
            raise PilotInviteError("invite_not_pending")
        now = ensure_naive_utc(utc_now())
        invite.status = InviteStatus.REVOKED.value
        invite.revoked_at = now
        invite.updated_at = now
        self._session.add(invite)
        await self._session.commit()
        await self._session.refresh(invite)
        log.info(
            "pilot_invite_revoked",
            invite_id=str(invite.id),
            actor_user_id=str(actor_user_id),
        )
        return invite

    async def _public_status(self, invite: PilotInviteTable) -> InviteStatusView:
        now = ensure_naive_utc(utc_now())
        if invite.status == InviteStatus.REVOKED.value:
            return InviteStatusView(state=InvitePublicState.REVOKED, invite_id=invite.id)
        if invite.status == InviteStatus.ACCEPTED.value:
            return InviteStatusView(
                state=InvitePublicState.ALREADY_USED, invite_id=invite.id
            )
        if invite.status == InviteStatus.EXPIRED.value or ensure_naive_utc(
            invite.expires_at
        ) <= now:
            if invite.status == InviteStatus.PENDING.value:
                invite.status = InviteStatus.EXPIRED.value
                invite.updated_at = now
                self._session.add(invite)
                await self._session.commit()
            return InviteStatusView(state=InvitePublicState.EXPIRED, invite_id=invite.id)

        existing = await self._find_user_by_email(invite.email_normalized)
        if existing is not None:
            return InviteStatusView(
                state=InvitePublicState.ACCOUNT_EXISTS,
                email=invite.email_normalized,
                invite_id=invite.id,
            )

        return InviteStatusView(
            state=InvitePublicState.VALID,
            email=invite.email_normalized,
            expires_at=invite.expires_at,
            invite_id=invite.id,
        )

    async def _get_by_raw_token(self, raw_token: str) -> PilotInviteTable | None:
        token = (raw_token or "").strip()
        if not token.startswith("mpi_") or len(token) < 20:
            return None
        token_hash = hash_invite_token(token)
        result = await self._session.execute(
            select(PilotInviteTable).where(PilotInviteTable.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def _find_user_by_email(self, email_n: str) -> UserTable | None:
        result = await self._session.execute(
            select(UserTable).where(UserTable.email == email_n)
        )
        return result.scalar_one_or_none()

    async def _pending_for_email(self, email_n: str) -> PilotInviteTable | None:
        result = await self._session.execute(
            select(PilotInviteTable).where(
                PilotInviteTable.email_normalized == email_n,
                PilotInviteTable.status == InviteStatus.PENDING.value,
            )
        )
        return result.scalar_one_or_none()
