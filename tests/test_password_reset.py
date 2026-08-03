"""Password recovery v1 — request/status/complete, token lifecycle, session revoke."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, select

from app.db.base import ensure_naive_utc, utc_now
from app.db.models.browser_session import BrowserSessionTable
from app.db.models.password_reset_token import PasswordResetTokenTable
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.schemas.contracts import BetaAccessStatus, BrowserSessionStatus, UserRole
from app.security.passwords import verify_password
from app.security.reset_tokens import generate_reset_token
from tests.test_controlled_pilot_cph_3_browser_sessions import (
    ORIGIN,
    _provision_password_user,
)

GENERIC = "If an account exists, password reset instructions have been created."
OWNER_EMAIL = "joker.sam90@gmail.com"


def _sync_engine(database_url: str):
    return create_engine(database_url.replace("+aiosqlite", "").replace("+asyncpg", ""))


def _insert_pending_token(
    database_url: str,
    user_id: str,
    *,
    expires_delta: timedelta = timedelta(minutes=45),
    status: str = "pending",
) -> tuple[str, str]:
    plain, token_hash = generate_reset_token()
    engine = _sync_engine(database_url)
    now = ensure_naive_utc(utc_now())
    with Session(engine) as session:
        row = PasswordResetTokenTable(
            user_id=UUID(user_id),
            token_hash=token_hash,
            status=status,
            expires_at=now + expires_delta,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return plain, str(row.id)


def test_reset_request_generic_for_existing_and_unknown(
    client: TestClient, database_url: str
) -> None:
    email = f"reset.exist.{uuid4().hex[:8]}@marketsynth.local"
    password = f"old-pass-{uuid4().hex[:8]}"
    _provision_password_user(database_url, email, password)

    for target in (email, f"unknown.{uuid4().hex[:8]}@marketsynth.local"):
        res = client.post(
            "/auth/password-reset/request",
            json={"email": target},
            headers=ORIGIN,
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["message"] == GENERIC
        assert "mpr_" not in res.text
        assert password not in res.text


def test_reset_link_created_only_for_existing_user(
    client: TestClient, database_url: str
) -> None:
    email = f"reset.link.{uuid4().hex[:8]}@marketsynth.local"
    password = f"old-pass-{uuid4().hex[:8]}"
    user_id = _provision_password_user(database_url, email, password)

    client.post(
        "/auth/password-reset/request",
        json={"email": email},
        headers=ORIGIN,
    )
    client.post(
        "/auth/password-reset/request",
        json={"email": f"missing.{uuid4().hex[:8]}@marketsynth.local"},
        headers=ORIGIN,
    )

    engine = _sync_engine(database_url)
    with Session(engine) as session:
        rows = session.exec(select(PasswordResetTokenTable)).all()
        user_rows = [r for r in rows if str(r.user_id) == user_id]
        assert len(user_rows) >= 1
        for row in user_rows:
            assert not row.token_hash.startswith("mpr_")
            assert len(row.token_hash) == 64


def test_token_expiry_one_time_revoke_and_password_update(
    client: TestClient, database_url: str
) -> None:
    email = f"reset.flow.{uuid4().hex[:8]}@marketsynth.local"
    old_password = f"old-pass-{uuid4().hex[:8]}"
    new_password = f"new-pass-{uuid4().hex[:8]}"
    user_id = _provision_password_user(database_url, email, old_password)

    # Project ownership retained
    engine = _sync_engine(database_url)
    with Session(engine) as session:
        session.add(
            ProjectTable(
                name="Owned",
                owner_id=UUID(user_id),
            )
        )
        session.commit()

    # Active session before reset
    login = client.post(
        "/auth/login",
        json={"email": email, "password": old_password},
        headers=ORIGIN,
    )
    assert login.status_code == 200
    assert client.cookies.get("ms_pilot_session")

    plain, _ = _insert_pending_token(database_url, user_id)

    status = client.get(f"/auth/password-reset/{plain}/status", headers=ORIGIN)
    assert status.status_code == 200
    assert status.json()["state"] == "valid"

    complete = client.post(
        f"/auth/password-reset/{plain}/complete",
        json={
            "password": new_password,
            "password_confirmation": new_password,
        },
        headers=ORIGIN,
    )
    assert complete.status_code == 200, complete.text
    assert new_password not in complete.text
    assert "mpr_" not in complete.text

    # One-time: reuse fails
    reuse = client.post(
        f"/auth/password-reset/{plain}/complete",
        json={
            "password": new_password + "x",
            "password_confirmation": new_password + "x",
        },
        headers=ORIGIN,
    )
    assert reuse.status_code == 400
    reuse_body = reuse.json()
    assert (
        reuse_body.get("detail") in {"token_used", "invalid_token"}
        or reuse_body.get("safe_message") in {"token_used", "invalid_token"}
        or "token_used" in str(reuse_body)
        or "invalid_token" in str(reuse_body)
    )

    # Old session rejected
    me = client.get("/auth/me", headers=ORIGIN)
    assert me.status_code == 401

    engine = _sync_engine(database_url)
    with Session(engine) as session:
        sessions_after_reset = session.exec(
            select(BrowserSessionTable).where(
                BrowserSessionTable.user_id == UUID(user_id)
            )
        ).all()
        assert sessions_after_reset
        assert all(
            s.status != BrowserSessionStatus.ACTIVE.value for s in sessions_after_reset
        )

    # Old password rejected, new accepted
    bad = client.post(
        "/auth/login",
        json={"email": email, "password": old_password},
        headers=ORIGIN,
    )
    assert bad.status_code == 401
    good = client.post(
        "/auth/login",
        json={"email": email, "password": new_password},
        headers=ORIGIN,
    )
    assert good.status_code == 200

    with Session(engine) as session:
        user = session.get(UserTable, UUID(user_id))
        assert user is not None
        assert user.role == UserRole.OWNER
        assert verify_password(new_password, user.password_hash or "")
        assert not verify_password(old_password, user.password_hash or "")
        projects = session.exec(
            select(ProjectTable).where(ProjectTable.owner_id == UUID(user_id))
        ).all()
        assert len(projects) == 1


def test_new_request_revokes_prior_pending(
    client: TestClient, database_url: str
) -> None:
    email = f"reset.revoke.{uuid4().hex[:8]}@marketsynth.local"
    password = f"old-pass-{uuid4().hex[:8]}"
    user_id = _provision_password_user(database_url, email, password)
    plain1, id1 = _insert_pending_token(database_url, user_id)

    client.post(
        "/auth/password-reset/request",
        json={"email": email},
        headers=ORIGIN,
    )

    engine = _sync_engine(database_url)
    with Session(engine) as session:
        row = session.get(PasswordResetTokenTable, UUID(id1))
        assert row is not None
        assert row.status == "revoked"
        assert row.revoked_at is not None

    status = client.get(f"/auth/password-reset/{plain1}/status", headers=ORIGIN)
    assert status.json()["state"] == "revoked"


def test_expired_token_rejected(client: TestClient, database_url: str) -> None:
    email = f"reset.exp.{uuid4().hex[:8]}@marketsynth.local"
    password = f"old-pass-{uuid4().hex[:8]}"
    user_id = _provision_password_user(database_url, email, password)
    plain, _ = _insert_pending_token(
        database_url, user_id, expires_delta=timedelta(minutes=-5)
    )
    status = client.get(f"/auth/password-reset/{plain}/status", headers=ORIGIN)
    assert status.json()["state"] == "expired"
    complete = client.post(
        f"/auth/password-reset/{plain}/complete",
        json={"password": "brand-new-pass1", "password_confirmation": "brand-new-pass1"},
        headers=ORIGIN,
    )
    assert complete.status_code == 400
    body = complete.json()
    assert (
        body.get("detail") == "token_expired"
        or body.get("safe_message") == "token_expired"
        or body.get("error_code") == "token_expired"
        or "token_expired" in str(body)
    )


def test_owner_identity_preserved_on_reset(
    client: TestClient, database_url: str
) -> None:
    """Same User ID + role=owner; no duplicate for known owner email pattern."""
    password = f"owner-old-{uuid4().hex[:8]}"
    new_password = f"owner-new-{uuid4().hex[:8]}"
    # Unique email in tests — production owner is recovered manually.
    email = f"owner.reset.{uuid4().hex[:8]}@marketsynth.local"
    user_id = _provision_password_user(database_url, email, password)
    engine = _sync_engine(database_url)
    with Session(engine) as session:
        user = session.get(UserTable, UUID(user_id))
        assert user is not None
        user.role = UserRole.OWNER
        user.beta_access_status = BetaAccessStatus.APPROVED
        session.add(user)
        session.commit()

    plain, _ = _insert_pending_token(database_url, user_id)
    complete = client.post(
        f"/auth/password-reset/{plain}/complete",
        json={
            "password": new_password,
            "password_confirmation": new_password,
        },
        headers=ORIGIN,
    )
    assert complete.status_code == 200

    with Session(engine) as session:
        users = session.exec(select(UserTable).where(UserTable.email == email)).all()
        assert len(users) == 1
        assert str(users[0].id) == user_id
        assert users[0].role == UserRole.OWNER

    # Ensure raw token never stored
    with Session(engine) as session:
        tokens = session.exec(select(PasswordResetTokenTable)).all()
        for t in tokens:
            assert plain not in (t.token_hash or "")
            assert not t.token_hash.startswith("mpr_")


def test_no_secrets_in_reset_api_bodies(client: TestClient, database_url: str) -> None:
    email = f"reset.secret.{uuid4().hex[:8]}@marketsynth.local"
    password = f"old-pass-{uuid4().hex[:8]}"
    user_id = _provision_password_user(database_url, email, password)
    plain, _ = _insert_pending_token(database_url, user_id)
    new_password = f"new-pass-{uuid4().hex[:8]}"
    res = client.post(
        f"/auth/password-reset/{plain}/complete",
        json={
            "password": new_password,
            "password_confirmation": new_password,
        },
        headers=ORIGIN,
    )
    assert res.status_code == 200
    text = res.text.lower()
    assert "scrypt$" not in text
    assert new_password.lower() not in text
    assert plain.lower() not in text
    assert "postgresql" not in text
