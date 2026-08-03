"""Create a one-time pilot invitation — secure operator UX."""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

from app.core.config import get_settings
from app.db.session import get_session_factory, init_db, reset_db_state
from app.schemas.contracts import UserRole
from app.services.pilot_invite_service import PilotInviteError, PilotInviteService

BLOCKED_DB_NAMES = frozenset({"botfazer", "postgres", "template0", "template1"})
CANONICAL_FRONTEND = "http://localhost:3000"


def _db_name(url: str) -> str:
    return (urlparse(url.replace("+asyncpg", "")).path or "/").lstrip("/") or "unknown"


def _activation_base(frontend_url: str | None, allowed: list[str]) -> str:
    # Prefer canonical local host for cookie/CSRF alignment.
    if frontend_url:
        return frontend_url.rstrip("/")
    if CANONICAL_FRONTEND in (allowed or []):
        return CANONICAL_FRONTEND
    for preferred in (CANONICAL_FRONTEND, "http://127.0.0.1:3000"):
        if preferred in (allowed or []):
            return preferred
    if allowed:
        return allowed[0].rstrip("/")
    return CANONICAL_FRONTEND


def _copy_clipboard(text: str) -> bool:
    try:
        if sys.platform == "win32":
            proc = subprocess.run(
                ["clip"],
                input=text,
                text=True,
                check=False,
                capture_output=True,
            )
            return proc.returncode == 0
        if sys.platform == "darwin":
            proc = subprocess.run(
                ["pbcopy"],
                input=text,
                text=True,
                check=False,
                capture_output=True,
            )
            return proc.returncode == 0
        proc = subprocess.run(
            ["xclip", "-selection", "clipboard"],
            input=text,
            text=True,
            check=False,
            capture_output=True,
        )
        return proc.returncode == 0
    except OSError:
        return False


def _write_url_file(url: str) -> Path:
    path = Path(os.environ.get("TEMP") or os.environ.get("TMP") or ".") / "ms_pilot_invite.url"
    path.write_text(url + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


async def _run(args: argparse.Namespace) -> int:
    settings = get_settings()
    db_name = _db_name(settings.database_url)
    if args.require_db and db_name != args.require_db:
        print(f"Refusing: database is {db_name!r}, required {args.require_db!r}", file=sys.stderr)
        return 3
    if db_name in BLOCKED_DB_NAMES and not args.allow_legacy_db:
        print(
            f"Refusing drifted/legacy database name {db_name!r}. "
            "Use --require-db botfazer_cph1 (or pass --allow-legacy-db only with owner approval).",
            file=sys.stderr,
        )
        return 4
    if settings.app_env in {"production", "staging"} and not args.allow_remote_like:
        print(
            f"Refusing app_env={settings.app_env!r} without --allow-remote-like",
            file=sys.stderr,
        )
        return 5

    grant_role = UserRole.OWNER if args.grant_owner else UserRole.MEMBER

    reset_db_state()
    await init_db(settings)
    factory = get_session_factory()
    async with factory() as session:
        service = PilotInviteService(session)
        if args.revoke_pending_only:
            count = await service.revoke_pending_for_email(args.email)
            print(f"ok revoked_pending={count} email={args.email.strip().lower()} database={db_name}")
            return 0
        try:
            result = await service.create_invite(
                email=args.email,
                created_by_user_id=None,
                ttl_hours=args.ttl_hours,
                replace_pending=args.replace,
                grant_role=grant_role,
            )
        except PilotInviteError as exc:
            print(f"error: {exc.code}", file=sys.stderr)
            return 6

    base = _activation_base(settings.public_frontend_url, list(settings.browser_allowed_origins))
    if not base.startswith(CANONICAL_FRONTEND) and "localhost" not in base and "127.0.0.1" not in base:
        # Keep operator-visible note without leaking token.
        print(f"warning: non-canonical frontend base {base}", file=sys.stderr)
    url = f"{base.rstrip('/')}/activate-invite?token={result.plain_token}"
    if "?token=" not in url or "mpi_" not in url:
        print("error: activation URL missing token", file=sys.stderr)
        return 7

    url_file = _write_url_file(url)
    clipped = _copy_clipboard(url) if args.clipboard or args.open_browser else _copy_clipboard(url)

    print(f"ok database={db_name} invite_id={result.invite.id}")
    print(f"email={result.invite.email_normalized}")
    print(f"expires_at={result.invite.expires_at.isoformat()}")
    print(f"grant_role={grant_role.value}")
    print(f"canonical_host={CANONICAL_FRONTEND}")
    print(f"url_file={url_file}")
    print(f"clipboard={'yes' if clipped else 'no'}")
    print("activation_url: (not printed — open url_file or paste from clipboard)")
    print("token: (not stored in plaintext; not printed)")

    if args.open_browser:
        opened = webbrowser.open(url)
        print(f"browser_opened={'yes' if opened else 'no'}")

    # Clear local reference ASAP
    del url
    del result
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create one-time pilot invite (operator command — no public signup)"
    )
    parser.add_argument("--email", required=True)
    parser.add_argument(
        "--ttl-hours",
        type=int,
        default=48,
        help="Invitation lifetime (default 48, max 168)",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Revoke existing pending invite for the same email",
    )
    parser.add_argument(
        "--revoke-pending-only",
        action="store_true",
        help="Only revoke pending invites for email (no new invite)",
    )
    parser.add_argument(
        "--grant-owner",
        action="store_true",
        help="Bootstrap: accept assigns OWNER role (operator-only first admin)",
    )
    parser.add_argument(
        "--clipboard",
        action="store_true",
        help="Copy full activation URL to clipboard (also default when using --open-browser)",
    )
    parser.add_argument(
        "--open-browser",
        action="store_true",
        help="Open activation URL in the local default browser",
    )
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
    parser.add_argument(
        "--allow-remote-like",
        action="store_true",
        help="Allow when APP_ENV is production/staging",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
