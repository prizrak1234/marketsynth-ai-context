"""Create a one-time password-reset link for an existing user (local operator).

Does not change role, projects, or create a new User. Never prints passwords.
Raw token appears once in the reset URL only.
"""

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
from app.services.password_reset_service import PasswordResetService

BLOCKED_DB_NAMES = frozenset({"botfazer", "postgres", "template0", "template1"})
CANONICAL_FRONTEND = "http://localhost:3000"


def _db_name(url: str) -> str:
    return (urlparse(url.replace("+asyncpg", "")).path or "/").lstrip("/") or "unknown"


def _frontend_base(frontend_url: str | None, allowed: list[str]) -> str:
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
    path = (
        Path(os.environ.get("TEMP") or os.environ.get("TMP") or ".")
        / "ms_password_reset.url"
    )
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
        print(
            f"Refusing: database is {db_name!r}, required {args.require_db!r}",
            file=sys.stderr,
        )
        return 3
    if db_name in BLOCKED_DB_NAMES and not args.allow_legacy_db:
        print(
            f"Refusing drifted/legacy database name {db_name!r}. "
            "Use --require-db botfazer_cph1.",
            file=sys.stderr,
        )
        return 4

    reset_db_state()
    await init_db(settings)
    factory = get_session_factory()
    async with factory() as session:
        service = PasswordResetService(session)
        result = await service.request_reset(
            email=args.email,
            client_ip="operator-script",
            user_agent="create_password_reset_link.py",
            ttl_minutes=args.ttl_minutes,
        )
        if result is None:
            print(
                "No active password user found for that email "
                "(or email invalid). No token emitted.",
                file=sys.stderr,
            )
            return 6

        base = _frontend_base(args.frontend_url, settings.browser_allowed_origins)
        reset_url = f"{base}/reset-password?token={result.plain_token}"
        # Never log raw token via structured logger — stdout once for the operator.
        print(f"ok database={db_name} user_id={result.user.id} email={result.user.email}")
        print(f"role={result.user.role} reset_id={result.token_row.id}")
        print("reset_url (shown once):")
        print(reset_url)
        url_file = _write_url_file(reset_url)
        print(f"url_file={url_file}")
        if args.copy_url:
            copied = _copy_clipboard(reset_url)
            print(f"clipboard={'yes' if copied else 'no'} (URL only, never password)")
        if args.open_browser:
            webbrowser.open(reset_url)
            print("browser=opened")
        print("password: (not generated — owner chooses in browser)")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Operator: create one-time password reset URL for existing user"
    )
    parser.add_argument("--email", required=True)
    parser.add_argument(
        "--require-db",
        default="botfazer_cph1",
        help="Refuse unless DATABASE_URL database name matches",
    )
    parser.add_argument("--ttl-minutes", type=int, default=45)
    parser.add_argument(
        "--frontend-url",
        default=None,
        help=f"Override frontend base (default canonical {CANONICAL_FRONTEND})",
    )
    parser.add_argument(
        "--open-browser",
        action="store_true",
        help="Open the reset URL in the default browser once",
    )
    parser.add_argument(
        "--copy-url",
        action="store_true",
        help="Copy reset URL (never password) to clipboard",
    )
    parser.add_argument(
        "--allow-legacy-db",
        action="store_true",
        help="Dangerous: allow blocked legacy DB names",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
