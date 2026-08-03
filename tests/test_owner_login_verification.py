"""Owner login verification — password reset without duplicate user/invite."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, select

from app.db.base import utc_now
from app.db.models.user import UserTable
from app.schemas.contracts import BetaAccessStatus, UserRole
from app.security.passwords import hash_password
from app.services.browser_session_service import BrowserSessionService
from tests.test_controlled_pilot_cph_3_browser_sessions import ORIGIN, _provision_password_user


def _sync_engine(database_url: str):
    sync_url = database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    return create_engine(sync_url)


def _provision_owner(database_url: str, email: str, password: str) -> UUID:
    sync_url = database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    engine = create_engine(sync_url)
    with Session(engine) as session:
        user = UserTable(
            email=email.lower(),
            display_name="Owner",
            role=UserRole.OWNER,
            is_active=True,
            beta_access_status=BetaAccessStatus.APPROVED,
            password_hash=hash_password(password),
            email_verified_at=utc_now(),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.id


def test_owner_password_reset_no_duplicate_user(
    client: TestClient, database_url: str
) -> None:
    email = f"owner.{uuid4().hex[:8]}@marketsynth.local"
    initial = f"owner-init-{uuid4().hex[:8]}"
    _provision_owner(database_url, email, initial)

    engine = _sync_engine(database_url)
    with Session(engine) as session:
        users = session.exec(select(UserTable).where(UserTable.email == email)).all()
        assert len(users) == 1
        user_id = users[0].id
        assert users[0].role == UserRole.OWNER

    login = client.post(
        "/auth/login",
        json={"email": email, "password": initial},
        headers=ORIGIN,
    )
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "owner"

    import asyncio

    from app.core.config import get_settings
    from app.db.session import get_session_factory, init_db, reset_db_state

    async def revoke() -> int:
        reset_db_state()
        await init_db(get_settings())
        factory = get_session_factory()
        async with factory() as s:
            return await BrowserSessionService(s).revoke_all_for_user(
                user_id, reason="test_reset"
            )

    assert asyncio.run(revoke()) >= 1

    newer = f"owner-new-{uuid4().hex[:8]}"
    with Session(engine) as session:
        user = session.exec(select(UserTable).where(UserTable.email == email)).one()
        user.password_hash = hash_password(newer)
        session.add(user)
        session.commit()
        dup = session.exec(select(UserTable).where(UserTable.email == email)).all()
        assert len(dup) == 1
        assert dup[0].id == user_id

    ok = client.post(
        "/auth/login",
        json={"email": email.upper(), "password": newer},
        headers=ORIGIN,
    )
    assert ok.status_code == 200
    assert ok.json()["user"]["role"] == "owner"
    assert client.get("/auth/me", headers=ORIGIN).status_code == 200
    assert client.post("/auth/logout", headers=ORIGIN).status_code == 204
    assert client.get("/auth/me", headers=ORIGIN).status_code == 401


def test_incomplete_email_rejected_by_backend(client: TestClient) -> None:
    res = client.post(
        "/auth/login",
        json={"email": "joker.sam90", "password": "some-password-x"},
        headers=ORIGIN,
    )
    assert res.status_code == 401


def test_full_email_login_with_provisioned_user(
    client: TestClient, database_url: str
) -> None:
    email = f"pilot.{uuid4().hex[:8]}@marketsynth.local"
    password = f"pilot-pass-{uuid4().hex[:6]}"
    _provision_password_user(database_url, email, password)
    res = client.post(
        "/auth/login",
        json={"email": f"  {email.upper()}  ", "password": password},
        headers=ORIGIN,
    )
    assert res.status_code == 200
