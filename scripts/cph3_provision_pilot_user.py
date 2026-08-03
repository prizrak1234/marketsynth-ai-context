"""Provision pilot user with password (CPH.3). Never prints the password."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from urllib.parse import urlparse

from sqlalchemy import select

from app.core.config import get_settings
from app.db.models.user import UserTable
from app.db.session import get_session_factory, init_db, reset_db_state
from app.schemas.contracts import BetaAccessStatus, UserRole
from app.security.passwords import hash_password


def _db_name(url: str) -> str:
    return (urlparse(url.replace("+asyncpg", "")).path or "/").lstrip("/") or "unknown"


OWNER_PROTECTED_EMAILS = frozenset({"joker.sam90@gmail.com"})


async def _run(args: argparse.Namespace) -> int:
    settings = get_settings()
    db_name = _db_name(settings.database_url)
    if args.require_db and db_name != args.require_db:
        print(f"Refusing: database is {db_name!r}, required {args.require_db!r}", file=sys.stderr)
        return 3

    email = args.email.strip().lower()
    if email in OWNER_PROTECTED_EMAILS and not args.allow_owner_env_password:
        if args.password or os.environ.get("CPH3_PILOT_PASSWORD"):
            print(
                f"Refusing auto/env password for protected owner email {email!r}. "
                "Use scripts/reset_pilot_user_password.py (interactive owner input).",
                file=sys.stderr,
            )
            return 8

    password = args.password or os.environ.get("CPH3_PILOT_PASSWORD")
    if not password:
        print("Password required via --password or CPH3_PILOT_PASSWORD", file=sys.stderr)
        return 4
    if len(password) < 10:
        print("Password must be at least 10 characters", file=sys.stderr)
        return 5

    reset_db_state()
    await init_db(settings)
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(select(UserTable).where(UserTable.email == email))
        user = result.scalar_one_or_none()
        if user and not args.update:
            print(f"User already exists id={user.id} (pass --update to set password)", file=sys.stderr)
            return 6
        pw_hash = hash_password(password)
        if user is None:
            user = UserTable(
                email=email,
                display_name=args.display_name or email.split("@")[0],
                role=UserRole.OWNER,
                is_active=True,
                beta_access_status=BetaAccessStatus.APPROVED,
                password_hash=pw_hash,
                telegram_id=args.telegram_id,
            )
            session.add(user)
        else:
            user.password_hash = pw_hash
            user.is_active = True
            user.beta_access_status = BetaAccessStatus.APPROVED
            if args.display_name:
                user.display_name = args.display_name
            session.add(user)
        await session.commit()
        await session.refresh(user)
        print(f"ok database={db_name} user_id={user.id} email={email} role={user.role}")
        print("password: (not printed)")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="CPH.3 provision pilot password user")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", default=None, help="Prefer CPH3_PILOT_PASSWORD env")
    parser.add_argument("--display-name", default=None)
    parser.add_argument("--telegram-id", type=int, default=None)
    parser.add_argument("--update", action="store_true")
    parser.add_argument(
        "--require-db",
        default="botfazer_cph1",
        help="Refuse unless DATABASE_URL database name matches (default botfazer_cph1)",
    )
    parser.add_argument(
        "--allow-owner-env-password",
        action="store_true",
        help="Dangerous: allow env/--password for protected owner emails (E2E only)",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
