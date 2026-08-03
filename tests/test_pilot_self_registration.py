"""Pilot self-registration v1 — member only, signup flag, no owner via register."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, select

from app.db.models.user import UserTable
from app.schemas.contracts import UserRole
from app.security.passwords import verify_password
from tests.test_controlled_pilot_cph_3_browser_sessions import ORIGIN

OWNER_EMAIL = "joker.sam90@gmail.com"


def _sync_engine(database_url: str):
    return create_engine(database_url.replace("+aiosqlite", "").replace("+asyncpg", ""))


def test_signup_status_enabled_in_development(client: TestClient) -> None:
    res = client.get("/auth/signup-status", headers=ORIGIN)
    assert res.status_code == 200
    assert res.json()["signup_enabled"] is True


def test_register_creates_member_and_session(
    client: TestClient, database_url: str, monkeypatch
) -> None:
    monkeypatch.setenv("PUBLIC_SIGNUP_ENABLED", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()
    email = f"member.{uuid4().hex[:8]}@marketsynth.local"
    password = f"member-pass-{uuid4().hex[:6]}"
    res = client.post(
        "/auth/register",
        json={
            "email": email,
            "display_name": "Member",
            "password": password,
            "password_confirmation": password,
            "accepted_pilot_notice": True,
            "role": "owner",  # ignored / not in schema
        },
        headers=ORIGIN,
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["user"]["email"] == email
    assert body["user"]["role"] == "member"
    assert client.cookies.get("ms_pilot_session")
    assert password not in res.text.lower()

    me = client.get("/auth/me", headers=ORIGIN)
    assert me.status_code == 200
    assert me.json()["role"] == "member"

    engine = _sync_engine(database_url)
    with Session(engine) as session:
        users = session.exec(select(UserTable).where(UserTable.email == email)).all()
        assert len(users) == 1
        assert users[0].role == UserRole.MEMBER
        assert verify_password(password, users[0].password_hash or "")

    client.post("/auth/logout", headers=ORIGIN)
    login = client.post(
        "/auth/login",
        json={"email": email.upper(), "password": password},
        headers=ORIGIN,
    )
    assert login.status_code == 200


def test_register_duplicate_email(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_SIGNUP_ENABLED", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()
    email = f"dupe.{uuid4().hex[:8]}@marketsynth.local"
    password = "dupe-pass-99x"
    first = client.post(
        "/auth/register",
        json={
            "email": email,
            "display_name": "A",
            "password": password,
            "password_confirmation": password,
            "accepted_pilot_notice": True,
        },
        headers=ORIGIN,
    )
    assert first.status_code == 201
    client.cookies.clear()
    second = client.post(
        "/auth/register",
        json={
            "email": email,
            "display_name": "B",
            "password": password,
            "password_confirmation": password,
            "accepted_pilot_notice": True,
        },
        headers=ORIGIN,
    )
    assert second.status_code == 409


def test_register_rejects_incomplete_email(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_SIGNUP_ENABLED", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()
    res = client.post(
        "/auth/register",
        json={
            "email": "joker.sam90",
            "display_name": "X",
            "password": "valid-pass-12",
            "password_confirmation": "valid-pass-12",
            "accepted_pilot_notice": True,
        },
        headers=ORIGIN,
    )
    assert res.status_code == 400


def test_register_disabled(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_SIGNUP_ENABLED", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()
    res = client.post(
        "/auth/register",
        json={
            "email": f"x.{uuid4().hex[:6]}@marketsynth.local",
            "display_name": "X",
            "password": "valid-pass-12",
            "password_confirmation": "valid-pass-12",
            "accepted_pilot_notice": True,
        },
        headers=ORIGIN,
    )
    assert res.status_code == 403
    assert (
        res.json().get("detail") == "signup_disabled"
        or res.json().get("safe_message") == "signup_disabled"
    )


def test_register_does_not_duplicate_owner(client: TestClient, monkeypatch, database_url: str) -> None:
    monkeypatch.setenv("PUBLIC_SIGNUP_ENABLED", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()
    engine = _sync_engine(database_url)
    with Session(engine) as session:
        # Only assert when owner exists in this DB (pilot); tests use temp sqlite so seed if missing
        from app.schemas.contracts import BetaAccessStatus
        from app.security.passwords import hash_password
        from app.db.base import utc_now

        existing = session.exec(
            select(UserTable).where(UserTable.email == OWNER_EMAIL)
        ).one_or_none()
        if existing is None:
            session.add(
                UserTable(
                    email=OWNER_EMAIL,
                    display_name="Owner",
                    role=UserRole.OWNER,
                    is_active=True,
                    beta_access_status=BetaAccessStatus.APPROVED,
                    password_hash=hash_password("owner-seed-pass"),
                    email_verified_at=utc_now(),
                )
            )
            session.commit()

    res = client.post(
        "/auth/register",
        json={
            "email": OWNER_EMAIL,
            "display_name": "Hacker",
            "password": "hacker-pass-1",
            "password_confirmation": "hacker-pass-1",
            "accepted_pilot_notice": True,
        },
        headers=ORIGIN,
    )
    assert res.status_code == 409
    with Session(engine) as session:
        rows = session.exec(select(UserTable).where(UserTable.email == OWNER_EMAIL)).all()
        assert len(rows) == 1
        assert rows[0].role == UserRole.OWNER


def test_change_password(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_SIGNUP_ENABLED", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()
    email = f"chg.{uuid4().hex[:8]}@marketsynth.local"
    old = f"old-pass-{uuid4().hex[:6]}"
    new = f"new-pass-{uuid4().hex[:6]}"
    client.post(
        "/auth/register",
        json={
            "email": email,
            "display_name": "Chg",
            "password": old,
            "password_confirmation": old,
            "accepted_pilot_notice": True,
        },
        headers=ORIGIN,
    )
    chg = client.post(
        "/auth/change-password",
        json={
            "current_password": old,
            "new_password": new,
            "new_password_confirmation": new,
        },
        headers=ORIGIN,
    )
    assert chg.status_code == 200, chg.text
    client.post("/auth/logout", headers=ORIGIN)
    bad = client.post(
        "/auth/login",
        json={"email": email, "password": old},
        headers=ORIGIN,
    )
    assert bad.status_code == 401
    good = client.post(
        "/auth/login",
        json={"email": email, "password": new},
        headers=ORIGIN,
    )
    assert good.status_code == 200
