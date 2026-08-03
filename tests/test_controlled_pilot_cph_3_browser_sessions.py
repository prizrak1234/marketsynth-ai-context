"""CPH.3 — browser session login, logout, revocation, expiry."""

from __future__ import annotations

import asyncio
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, select

from app.db.base import ensure_naive_utc, utc_now
from app.db.models.browser_session import BrowserSessionTable
from app.db.models.user import UserTable
from app.schemas.contracts import BetaAccessStatus, UserRole
from app.security.browser_sessions import generate_session_token
from app.security.passwords import hash_password
from tests.conftest import _create_user_with_api_key

ORIGIN = {"Origin": "http://127.0.0.1:3000"}


def _provision_password_user(
    database_url: str, email: str, password: str, *, active: bool = True
) -> str:
    """Sync SQLite/PG provision — visible to TestClient connections."""
    sync_url = database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    engine = create_engine(sync_url)
    with Session(engine) as session:
        user = UserTable(
            email=email.lower(),
            display_name=email.split("@")[0],
            role=UserRole.OWNER,
            is_active=active,
            beta_access_status=BetaAccessStatus.APPROVED,
            password_hash=hash_password(password),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        assert user.password_hash
        return str(user.id)


def test_login_logout_me(client: TestClient, database_url: str) -> None:
    email = "pilot.a@marketsynth.local"
    password = "pilot-pass-a1"
    _provision_password_user(database_url, email, password)

    bad = client.post(
        "/auth/login",
        json={"email": email, "password": "wrong-password-xx"},
        headers=ORIGIN,
    )
    assert bad.status_code == 401
    bad_body = bad.json()
    assert (
        bad_body.get("detail") == "invalid_credentials"
        or bad_body.get("safe_message") == "invalid_credentials"
    )

    login = client.post(
        "/auth/login",
        json={"email": email, "password": password},
        headers=ORIGIN,
    )
    assert login.status_code == 200, login.text
    body = login.json()
    assert body["user"]["email"] == email
    assert "api_key" not in body
    assert client.cookies.get("ms_pilot_session")
    assert "mss_" not in login.text

    me = client.get("/auth/me", headers=ORIGIN)
    assert me.status_code == 200
    assert me.json()["email"] == email

    logout = client.post("/auth/logout", headers=ORIGIN)
    assert logout.status_code == 204

    me2 = client.get("/auth/me", headers=ORIGIN)
    assert me2.status_code == 401


def test_api_key_auth_still_works(client: TestClient) -> None:
    plain_key, _user = asyncio.run(_create_user_with_api_key(telegram_id=9100311))
    res = client.get("/auth/me", headers={"Authorization": f"Bearer {plain_key}"})
    assert res.status_code == 200


def test_disabled_user_cannot_login(client: TestClient, database_url: str) -> None:
    email = "disabled@marketsynth.local"
    password = "disabled-pass-1"
    _provision_password_user(database_url, email, password, active=False)
    res = client.post(
        "/auth/login",
        json={"email": email, "password": password},
        headers=ORIGIN,
    )
    assert res.status_code == 401


def test_expired_session_rejected(client: TestClient, database_url: str) -> None:
    email = "expire@marketsynth.local"
    password = "expire-pass-12"
    user_id = _provision_password_user(database_url, email, password)
    plain, th = generate_session_token()
    sync_url = database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    engine = create_engine(sync_url)
    with Session(engine) as session:
        user = session.exec(select(UserTable).where(UserTable.email == email)).one()
        now = ensure_naive_utc(utc_now())
        row = BrowserSessionTable(
            user_id=user.id,
            token_hash=th,
            status="active",
            purpose="pilot_browser",
            created_at=now - timedelta(hours=9),
            expires_at=now - timedelta(minutes=1),
            created_by="test",
        )
        session.add(row)
        session.commit()
    client.cookies.set("ms_pilot_session", plain)
    res = client.get("/auth/me", headers=ORIGIN)
    assert res.status_code == 401
    void = user_id
    assert void


def test_revoke_other_session(client: TestClient, database_url: str) -> None:
    email = "revoker@marketsynth.local"
    password = "revoker-pass1"
    _provision_password_user(database_url, email, password)
    login = client.post(
        "/auth/login",
        json={"email": email, "password": password},
        headers=ORIGIN,
    )
    assert login.status_code == 200, login.text
    sessions = client.get("/auth/sessions", headers=ORIGIN)
    assert sessions.status_code == 200
    sid = sessions.json()[0]["id"]
    rev = client.post(f"/auth/sessions/{sid}/revoke", headers=ORIGIN)
    assert rev.status_code == 204
    me = client.get("/auth/me", headers=ORIGIN)
    assert me.status_code == 401
