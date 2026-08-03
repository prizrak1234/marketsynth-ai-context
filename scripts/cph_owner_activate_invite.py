"""Secure owner invite bootstrap + activation (no token/password printed)."""

from __future__ import annotations

import json
import os
import secrets
import sys
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from http.cookiejar import CookieJar
from urllib.request import HTTPCookieProcessor, build_opener

OWNER_EMAIL = "joker.sam90@gmail.com"
ORIGIN = "http://localhost:3000"
API = os.environ.get("CPH2_BACKEND_URL", "http://localhost:8000").rstrip("/")
URL_FILE = Path(os.environ.get("TEMP") or os.environ.get("TMP") or ".") / "ms_pilot_invite.url"


def _req(opener, method: str, url: str, body: dict | None = None) -> tuple[int, dict | str]:
    from urllib.error import HTTPError

    data = None
    headers = {"Origin": ORIGIN, "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with opener.open(request, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            try:
                parsed = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                parsed = raw
            return resp.status, parsed
    except HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = raw
        return exc.code, parsed


def main() -> int:
    if not URL_FILE.is_file():
        print("error: url_file missing — run create_pilot_invite first", file=sys.stderr)
        return 2
    url = URL_FILE.read_text(encoding="utf-8").strip()
    parsed = urlparse(url)
    if parsed.hostname not in {"localhost", "127.0.0.1"}:
        print("error: non-local activation URL refused", file=sys.stderr)
        return 3
    token = ""
    for part in parsed.query.split("&"):
        if part.startswith("token="):
            token = part[len("token=") :]
            break
    if not token.startswith("mpi_"):
        print("error: activation URL missing token query", file=sys.stderr)
        return 4

    password = os.environ.get("OWNER_PILOT_PASSWORD") or secrets.token_urlsafe(18)
    if len(password) < 10:
        print("error: password too short", file=sys.stderr)
        return 5

    jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))

    status, body = _req(opener, "GET", f"{API}/auth/invitations/{token}/status")
    if status != 200 or not isinstance(body, dict) or body.get("state") != "valid":
        print(f"error: invite status not valid status={status} state={getattr(body, 'get', lambda k: None)('state') if isinstance(body, dict) else body}", file=sys.stderr)
        return 6
    if body.get("email") != OWNER_EMAIL:
        print("error: invite email mismatch", file=sys.stderr)
        return 7

    status, body = _req(
        opener,
        "POST",
        f"{API}/auth/invitations/{token}/accept",
        {
            "display_name": "Sarbast",
            "password": password,
            "password_confirm": password,
            "accept_pilot_notice": True,
        },
    )
    if status != 200:
        print(f"error: accept failed status={status}", file=sys.stderr)
        return 8

    status, me = _req(opener, "GET", f"{API}/auth/me")
    if status != 200 or not isinstance(me, dict) or me.get("email") != OWNER_EMAIL:
        print(f"error: session after accept failed status={status}", file=sys.stderr)
        return 9

    role = me.get("role")
    _req(opener, "POST", f"{API}/auth/logout")

    jar2 = CookieJar()
    opener2 = build_opener(HTTPCookieProcessor(jar2))
    status, _ = _req(
        opener2,
        "POST",
        f"{API}/auth/login",
        {"email": OWNER_EMAIL, "password": password},
    )
    if status != 200:
        print(f"error: subsequent login failed status={status}", file=sys.stderr)
        return 10
    status, me2 = _req(opener2, "GET", f"{API}/auth/me")
    if status != 200:
        print("error: me after login failed", file=sys.stderr)
        return 11

    # Reuse must fail
    status_reuse, _ = _req(
        opener2,
        "POST",
        f"{API}/auth/invitations/{token}/accept",
        {
            "display_name": "X",
            "password": password,
            "password_confirm": password,
            "accept_pilot_notice": True,
        },
    )

    try:
        URL_FILE.unlink(missing_ok=True)
    except OSError:
        pass

    print("ok owner_activation=passed")
    print(f"email={OWNER_EMAIL}")
    print(f"role={role}")
    print(f"login_after_activation=passed")
    print(f"invite_reuse_status={status_reuse}")
    print("password: (not printed)")
    print("token: (not printed)")
    print("manual_browser_login_required=yes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
