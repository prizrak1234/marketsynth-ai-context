"""Reset password for an existing pilot user — interactive only, no auto-generation."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
from urllib.parse import urlparse

from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models.user import UserTable
from app.db.session import get_session_factory, init_db, reset_db_state
from app.security.passwords import hash_password
from app.services.browser_session_service import BrowserSessionService

log = get_logger(__name__)

BLOCKED_DB_NAMES = frozenset({"botfazer", "postgres", "template0", "template1"})


def _db_name(url: str) -> str:
    return (urlparse(url.replace("+asyncpg", "")).path or "/").lstrip("/") or "unknown"


def _prompt_new_password() -> str:
    p1 = getpass.getpass("New password: ")
    p2 = getpass.getpass("Confirm password: ")
    if p1 != p2:
        raise ValueError("password_mismatch")
    if len(p1) < 10:
        raise ValueError("password_too_short")
    if p1.strip() == "":
        raise ValueError("password_empty")
    return p1


async def _run(args: argparse.Namespace) -> int:
    settings = get_settings()
    db_name = _db_name(settings.database_url)
    if args.require_db and db_name != args.require_db:
        print(f"Refusing: database is {db_name!r}, required {args.require_db!r}", file=sys.stderr)
        return 3
    if db_name in BLOCKED_DB_NAMES and not args.allow_legacy_db:
        print(f"Refusing legacy database {db_name!r}", file=sys.stderr)
        return 4

    email = args.email.strip().lower()
    if "@" not in email:
        print("error: invalid email", file=sys.stderr)
        return 5

    try:
        new_password = _prompt_new_password()
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 6

    reset_db_state()
    await init_db(settings)
    factory = get_session_factory()
    async with factory() as session:
        user = (
            await session.execute(select(UserTable).where(UserTable.email == email))
        ).scalar_one_or_none()
        if user is None:
            print("error: user_not_found — use invite flow for new accounts", file=sys.stderr)
            return 7

        before_count = (
            await session.execute(
                select(func.count()).select_from(UserTable).where(UserTable.email == email)
            )
        ).scalar_one()
        if before_count != 1:
            print("error: duplicate_email_rows", file=sys.stderr)
            return 8

        preserved_role = user.role
        preserved_verified = user.email_verified_at
        preserved_active = user.is_active
        preserved_beta = user.beta_access_status

        user.password_hash = hash_password(new_password)
        session.add(user)
        await session.commit()
        await session.refresh(user)

        after_count = (
            await session.execute(
                select(func.count()).select_from(UserTable).where(UserTable.email == email)
            )
        ).scalar_one()
        if after_count != 1 or user.id is None:
            print("error: user_row_changed_unexpectedly", file=sys.stderr)
            return 9

        if user.role != preserved_role:
            print("error: role_changed", file=sys.stderr)
            return 10
        if user.email_verified_at != preserved_verified:
            print("error: email_verified_at_changed", file=sys.stderr)
            return 11

        revoked = await BrowserSessionService(session).revoke_all_for_user(
            user.id, reason="pilot_password_reset"
        )

    # Never log password or hash
    log.info(
        "pilot_password_reset",
        user_id=str(user.id),
        email=email,
        role=str(preserved_role),
        revoked_sessions=revoked,
        database=db_name,
    )
    print(f"ok database={db_name} user_id={user.id} email={email}")
    print(f"role={preserved_role} is_active={preserved_active} beta={preserved_beta}")
    print(f"email_verified_at_preserved={preserved_verified is not None}")
    print(f"revoked_sessions={revoked}")
    print("password: (not printed)")
    print("next: open http://localhost:3000/login and sign in with the new password")
    print("manual_browser_login_required=yes")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reset password for existing pilot user (interactive — owner sets password)"
    )
    parser.add_argument("--email", required=True)
    parser.add_argument(
        "--require-db",
        default="botfazer_cph1",
        help="Refuse unless DATABASE_URL database name matches",
    )
    parser.add_argument(
        "--allow-legacy-db",
        action="store_true",
        help="Owner override for blocked DB names (dangerous)",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
