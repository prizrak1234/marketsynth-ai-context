"""Pilot invite registration — create/accept/revoke, one-time tokens, no plaintext."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, select

from app.db.base import ensure_naive_utc, utc_now
from app.db.models.browser_session import BrowserSessionTable
from app.db.models.pilot_invite import PilotInviteTable
from app.db.models.user import UserTable
from app.schemas.contracts import BetaAccessStatus
from app.security.invite_tokens import generate_invite_token, hash_invite_token
from app.security.passwords import verify_password
from tests.test_controlled_pilot_cph_3_browser_sessions import (
    ORIGIN,
    _provision_password_user,
)


def _sync_engine(database_url: str):
    sync_url = database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    return create_engine(sync_url)


def _admin_cookie(client: TestClient, database_url: str) -> None:
    email = f"invite.admin.{uuid4().hex[:10]}@marketsynth.local"
    password = "invite-admin-pass"
    _provision_password_user(database_url, email, password)
    res = client.post(
        "/auth/login",
        json={"email": email, "password": password},
        headers=ORIGIN,
    )
    assert res.status_code == 200, res.text


def test_create_and_accept_invite(client: TestClient, database_url: str) -> None:
    _admin_cookie(client, database_url)
    email = f"invitee.{uuid4().hex[:8]}@marketsynth.local"
    create = client.post(
        "/auth/invitations",
        json={"email": email, "ttl_hours": 24},
        headers=ORIGIN,
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["email"] == email
    assert body["token"].startswith("mpi_")
    assert "activate-invite?token=" in body["activation_url"]
    token = body["token"]
    invite_id = UUID(body["invite_id"])

    engine = _sync_engine(database_url)
    with Session(engine) as session:
        row = session.exec(
            select(PilotInviteTable).where(PilotInviteTable.id == invite_id)
        ).one()
        assert row.token_hash == hash_invite_token(token)
        assert token not in row.token_hash
        assert row.status == "pending"

    client.cookies.clear()
    status = client.get(f"/auth/invitations/{token}/status", headers=ORIGIN)
    assert status.status_code == 200
    assert status.json()["state"] == "valid"
    assert status.json()["email"] == email

    accept = client.post(
        f"/auth/invitations/{token}/accept",
        json={
            "display_name": "Invitee",
            "password": "invitee-pass-99",
            "password_confirm": "invitee-pass-99",
            "accept_pilot_notice": True,
        },
        headers=ORIGIN,
    )
    assert accept.status_code == 200, accept.text
    assert accept.json()["user"]["email"] == email
    assert client.cookies.get("ms_pilot_session")
    assert "mpi_" not in accept.text
    assert "invitee-pass" not in accept.text.lower()

    me = client.get("/auth/me", headers=ORIGIN)
    assert me.status_code == 200
    assert me.json()["email"] == email

    with Session(engine) as session:
        user = session.exec(select(UserTable).where(UserTable.email == email)).one()
        assert user.password_hash
        assert "invitee-pass" not in user.password_hash
        assert verify_password("invitee-pass-99", user.password_hash)
        assert user.beta_access_status == BetaAccessStatus.APPROVED
        assert user.email_verified_at is not None
        invite = session.exec(
            select(PilotInviteTable).where(PilotInviteTable.id == invite_id)
        ).one()
        assert invite.status == "accepted"
        assert invite.accepted_by_user_id == user.id
        sessions = session.exec(
            select(BrowserSessionTable).where(BrowserSessionTable.user_id == user.id)
        ).all()
        assert len(sessions) >= 1

    reuse = client.post(
        f"/auth/invitations/{token}/accept",
        json={
            "display_name": "X",
            "password": "invitee-pass-99",
            "password_confirm": "invitee-pass-99",
            "accept_pilot_notice": True,
        },
        headers=ORIGIN,
    )
    assert reuse.status_code == 400

    client.cookies.clear()
    login = client.post(
        "/auth/login",
        json={"email": email, "password": "invitee-pass-99"},
        headers=ORIGIN,
    )
    assert login.status_code == 200


def test_expired_invite_rejected(client: TestClient, database_url: str) -> None:
    plain, th = generate_invite_token()
    engine = _sync_engine(database_url)
    now = ensure_naive_utc(utc_now())
    with Session(engine) as session:
        invite = PilotInviteTable(
            email_normalized="expired@marketsynth.local",
            token_hash=th,
            status="pending",
            expires_at=now - timedelta(minutes=1),
            created_at=now - timedelta(hours=2),
            updated_at=now - timedelta(hours=2),
        )
        session.add(invite)
        session.commit()

    status = client.get(f"/auth/invitations/{plain}/status", headers=ORIGIN)
    assert status.json()["state"] == "expired"
    accept = client.post(
        f"/auth/invitations/{plain}/accept",
        json={
            "display_name": "E",
            "password": "expired-pass1",
            "password_confirm": "expired-pass1",
            "accept_pilot_notice": True,
        },
        headers=ORIGIN,
    )
    assert accept.status_code == 400
    detail = accept.json().get("detail") or accept.json().get("safe_message") or ""
    assert "expired" in str(detail).lower()


def test_revoked_invite_rejected(client: TestClient, database_url: str) -> None:
    _admin_cookie(client, database_url)
    create = client.post(
        "/auth/invitations",
        json={"email": f"revoke.{uuid4().hex[:8]}@marketsynth.local", "ttl_hours": 24},
        headers=ORIGIN,
    )
    assert create.status_code == 201
    invite_id = create.json()["invite_id"]
    token = create.json()["token"]
    revoke = client.post(f"/auth/invitations/{invite_id}/revoke", headers=ORIGIN)
    assert revoke.status_code == 204
    client.cookies.clear()
    status = client.get(f"/auth/invitations/{token}/status", headers=ORIGIN)
    assert status.json()["state"] == "revoked"


def test_invalid_token_rejected(client: TestClient) -> None:
    status = client.get("/auth/invitations/mpi_notreal_token_xxxxx/status", headers=ORIGIN)
    assert status.status_code == 200
    assert status.json()["state"] == "invalid"


def test_duplicate_account_prevented(client: TestClient, database_url: str) -> None:
    email = f"dupe.{uuid4().hex[:8]}@marketsynth.local"
    _provision_password_user(database_url, email, "dupe-pass-12")
    _admin_cookie(client, database_url)
    create = client.post(
        "/auth/invitations",
        json={"email": email, "ttl_hours": 24},
        headers=ORIGIN,
    )
    assert create.status_code == 409
    body = create.json()
    assert body.get("detail") == "account_exists" or body.get("safe_message") == "account_exists"


def test_password_mismatch_rejected(client: TestClient, database_url: str) -> None:
    _admin_cookie(client, database_url)
    create = client.post(
        "/auth/invitations",
        json={"email": f"mismatch.{uuid4().hex[:8]}@marketsynth.local", "ttl_hours": 24},
        headers=ORIGIN,
    )
    token = create.json()["token"]
    client.cookies.clear()
    accept = client.post(
        f"/auth/invitations/{token}/accept",
        json={
            "display_name": "M",
            "password": "mismatch-pass",
            "password_confirm": "different-pass",
            "accept_pilot_notice": True,
        },
        headers=ORIGIN,
    )
    assert accept.status_code == 400


def test_pending_replace(client: TestClient, database_url: str) -> None:
    _admin_cookie(client, database_url)
    email = f"replace.{uuid4().hex[:8]}@marketsynth.local"
    first = client.post(
        "/auth/invitations",
        json={"email": email, "ttl_hours": 24},
        headers=ORIGIN,
    )
    assert first.status_code == 201
    second = client.post(
        "/auth/invitations",
        json={"email": email, "ttl_hours": 24},
        headers=ORIGIN,
    )
    assert second.status_code == 409
    third = client.post(
        "/auth/invitations",
        json={"email": email, "ttl_hours": 24, "replace_pending": True},
        headers=ORIGIN,
    )
    assert third.status_code == 201, third.text
