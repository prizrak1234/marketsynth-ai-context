"""Reset password for existing pilot user — preserves role, no secrets in output."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, select

from app.db.base import utc_now
from app.db.models.browser_session import BrowserSessionTable
from app.db.models.user import UserTable
from app.schemas.contracts import BetaAccessStatus, UserRole
from app.security.passwords import hash_password, verify_password
from app.services.browser_session_service import BrowserSessionService
from tests.test_controlled_pilot_cph_3_browser_sessions import ORIGIN

OWNER_EMAIL = "joker.sam90@gmail.com"


def _sync_engine(database_url: str):
    sync_url = database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    return create_engine(sync_url)


def _provision_owner(database_url: str, email: str, password: str) -> UserTable:
    engine = _sync_engine(database_url)
    verified = utc_now()
    with Session(engine) as session:
        user = UserTable(
            email=email.lower(),
            display_name="Owner",
            role=UserRole.OWNER,
            is_active=True,
            beta_access_status=BetaAccessStatus.APPROVED,
            password_hash=hash_password(password),
            email_verified_at=verified,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


def test_reset_existing_user_password(
    client: TestClient, database_url: str
) -> None:
    email = f"reset.{uuid4().hex[:8]}@marketsynth.local"
    old_pw = f"old-pass-{uuid4().hex[:8]}"
    new_pw = f"new-pass-{uuid4().hex[:8]}"
    user = _provision_owner(database_url, email, old_pw)
    verified_at = user.email_verified_at

    login_old = client.post(
        "/auth/login",
        json={"email": email, "password": old_pw},
        headers=ORIGIN,
    )
    assert login_old.status_code == 200

    engine = _sync_engine(database_url)
    with Session(engine) as session:
        row = session.exec(select(UserTable).where(UserTable.email == email)).one()
        row.password_hash = hash_password(new_pw)
        session.add(row)
        session.commit()

    import asyncio

    from app.core.config import get_settings
    from app.db.session import get_session_factory, init_db, reset_db_state

    async def revoke() -> int:
        reset_db_state()
        await init_db(get_settings())
        async with get_session_factory()() as s:
            return await BrowserSessionService(s).revoke_all_for_user(
                user.id, reason="test_reset"
            )

    assert asyncio.run(revoke()) >= 1

    bad = client.post(
        "/auth/login",
        json={"email": email, "password": old_pw},
        headers=ORIGIN,
    )
    assert bad.status_code == 401

    good = client.post(
        "/auth/login",
        json={"email": email, "password": new_pw},
        headers=ORIGIN,
    )
    assert good.status_code == 200
    assert good.json()["user"]["role"] == "owner"

    with Session(engine) as session:
        rows = session.exec(select(UserTable).where(UserTable.email == email)).all()
        assert len(rows) == 1
        assert rows[0].role == UserRole.OWNER
        assert rows[0].email_verified_at == verified_at
        assert verify_password(new_pw, rows[0].password_hash)
        sessions = session.exec(
            select(BrowserSessionTable).where(BrowserSessionTable.user_id == user.id)
        ).all()
        assert sessions
