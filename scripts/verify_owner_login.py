"""Verify existing owner login or reset password — no new invite/user."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import sys
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from sqlalchemy import func, select

from app.core.config import get_settings
from app.db.models.pilot_invite import PilotInviteTable
from app.db.models.user import UserTable
from app.db.session import get_session_factory, init_db, reset_db_state

OWNER_EMAIL = "joker.sam90@gmail.com"
ORIGIN = "http://localhost:3000"
DEFAULT_API = "http://localhost:8000"


def _db_name(url: str) -> str:
    return (urlparse(url.replace("+asyncpg", "")).path or "/").lstrip("/") or "unknown"


def probe_login(api: str, email: str, password: str) -> tuple[int, str | None]:
    body = json.dumps({"email": email, "password": password}).encode("utf-8")
    req = Request(
        f"{api.rstrip('/')}/auth/login",
        data=body,
        headers={"Content-Type": "application/json", "Origin": ORIGIN},
        method="POST",
    )
    try:
        with urlopen(req, timeout=30) as resp:
            return resp.status, None
    except HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {}
        code = parsed.get("error_code") or parsed.get("detail") or parsed.get("safe_message")
        return exc.code, str(code) if code else "http_error"


async def _audit_user(email: str) -> UserTable | None:
    reset_db_state()
    await init_db(get_settings())
    factory = get_session_factory()
    async with factory() as session:
        user = (
            await session.execute(select(UserTable).where(UserTable.email == email))
        ).scalar_one_or_none()
        if user is None:
            print("user_exists=no")
            return None
        dup = (
            await session.execute(
                select(func.count()).select_from(UserTable).where(UserTable.email == email)
            )
        ).scalar_one()
        invites = list(
            (
                await session.execute(
                    select(PilotInviteTable).where(
                        PilotInviteTable.email_normalized == email
                    )
                )
            ).scalars().all()
        )
        print("user_exists=yes")
        print(f"user_id={user.id}")
        print(f"email_normalized={user.email}")
        print(f"is_active={user.is_active}")
        print(f"beta_access_status={user.beta_access_status}")
        print(f"role={user.role}")
        print(f"has_password_hash={bool(user.password_hash)}")
        print(f"email_verified_at={user.email_verified_at}")
        print(f"duplicate_email_rows={dup}")
        print(f"invite_count={len(invites)}")
        for inv in invites:
            print(f"invite_status={inv.status}")
        return user


async def _run(args: argparse.Namespace) -> int:
    settings = get_settings()
    db_name = _db_name(settings.database_url)
    if args.require_db and db_name != args.require_db:
        print(f"Refusing: database is {db_name!r}, required {args.require_db!r}", file=sys.stderr)
        return 3

    email = args.email.strip().lower()
    user = await _audit_user(email)
    if user is None:
        return 4

    api = args.api.rstrip("/")

    if args.probe_only:
        status, code = probe_login(api, email, "probe-invalid-credentials-xx")
        print(f"login_probe_status={status}")
        print(f"login_probe_error_code={code}")
        print("manual_browser_login_required=yes")
        print("hint: use scripts/reset_pilot_user_password.py to set a new password interactively")
        return 0

    password = getpass.getpass(f"Password for {email}: ")
    status, code = probe_login(api, email, password)
    print(f"login_status={status}")
    print(f"login_error_code={code}")
    if status == 200:
        print("owner_login=passed_manual_credential")
        print("note: browser login still required for full verification")
        return 0

    print("owner_login=failed")
    print("hint: run scripts/reset_pilot_user_password.py --email", email, file=sys.stderr)
    return 7


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit owner account and probe login (no auto-reset)")
    parser.add_argument("--email", default=OWNER_EMAIL)
    parser.add_argument("--api", default=DEFAULT_API)
    parser.add_argument("--require-db", default="botfazer_cph1")
    parser.add_argument(
        "--probe-only",
        action="store_true",
        help="Probe login with invalid password to capture error shape (default audit mode)",
    )
    args = parser.parse_args()
    if not any(a in sys.argv for a in ("--probe-only",)):
        # Default to probe-only unless owner explicitly passes password attempt
        if "-h" not in sys.argv and "--help" not in sys.argv:
            args.probe_only = True
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
