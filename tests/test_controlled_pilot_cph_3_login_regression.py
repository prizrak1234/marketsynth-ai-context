"""CPH.3 login regression — auth error envelope codes."""

from __future__ import annotations

from fastapi.testclient import TestClient


ORIGIN = {"Origin": "http://localhost:3000"}


def test_anonymous_me_returns_authentication_required_code(client: TestClient) -> None:
    res = client.get("/auth/me")
    assert res.status_code == 401
    body = res.json()
    assert body.get("error_code") == "authentication_required"
    assert body.get("safe_message") == "authentication_required"


def test_login_invalid_password_code_not_generic_http_error(
    client: TestClient, database_url: str
) -> None:
    from tests.test_controlled_pilot_cph_3_browser_sessions import _provision_password_user

    email = "login.reg@marketsynth.local"
    password = "pilot-pass-ok1"
    _provision_password_user(database_url, email, password)

    bad = client.post(
        "/auth/login",
        json={"email": email, "password": "wrong-password-xx"},
        headers=ORIGIN,
    )
    assert bad.status_code == 401
    body = bad.json()
    assert body.get("error_code") == "invalid_credentials"
    assert body.get("safe_message") == "invalid_credentials"


def test_login_success_sets_session_cookie(client: TestClient, database_url: str) -> None:
    from tests.test_controlled_pilot_cph_3_browser_sessions import _provision_password_user

    email = "login.ok@marketsynth.local"
    password = "pilot-pass-ok2"
    _provision_password_user(database_url, email, password)

    ok = client.post(
        "/auth/login",
        json={"email": email, "password": password},
        headers=ORIGIN,
    )
    assert ok.status_code == 200
    assert "ms_pilot_session" in ok.headers.get("set-cookie", "")
    me = client.get("/auth/me")
    assert me.status_code == 200
