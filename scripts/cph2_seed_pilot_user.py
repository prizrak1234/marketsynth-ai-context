"""CPH.2 — seed disposable pilot API user on botfazer_cph1 (no create_all).

Writes API key to stdout and optionally web/.env.local.e2e (gitignored pattern).
Refuses drifted legacy DB name `botfazer`.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.db.repositories.user_repo import UserRepository
from app.db.session import close_db, get_session_factory, init_db, reset_db_state
from app.schemas.contracts import UserRole
from app.schemas.crud import UserCreate
from app.services.auth import AuthService
from app.services.users_service import UserService

E2E_TELEGRAM_ID = 9_100_042
E2E_EMAIL = "cph2.pilot@marketsynth.local"
E2E_NAME = "CPH2 Pilot E2E User"
E2E_KEY_NAME = "cph2-pilot-e2e"


def _db_name(url: str) -> str:
    raw = url.replace("+asyncpg", "").replace("+psycopg", "")
    return (urlparse(raw).path or "").lstrip("/")


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-env", action="store_true")
    parser.add_argument("--refresh-api-key", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    name = _db_name(settings.database_url)
    if name in {"botfazer", "postgres", "template0", "template1"}:
        print(f"refused: DATABASE_URL targets non-pilot db={name}")
        return 3
    if "cph1" not in name and "pilot" not in name and not name.startswith("botfazer_cph"):
        print(f"refused: expected pilot/cph disposable db, got={name}")
        return 3

    print(f"database={name}")
    reset_db_state()
    get_settings.cache_clear()
    await init_db(settings)
    factory = get_session_factory()
    plain: str | None = None
    async with factory() as session:
        users = UserService(session)
        auth = AuthService(session)
        repo = UserRepository(session)
        user = await repo.get_by_telegram_id(E2E_TELEGRAM_ID)
        if user is None:
            user = await users.create(
                UserCreate(
                    telegram_id=E2E_TELEGRAM_ID,
                    email=E2E_EMAIL,
                    display_name=E2E_NAME,
                    role=UserRole.OWNER,
                    is_active=True,
                ),
            )
            print(f"user_created={user.id}")
        else:
            print(f"user_existing={user.id}")

        if args.refresh_api_key or True:
            created = await auth.create_api_key(user.id, E2E_KEY_NAME)
            plain = created.plain_key
            print(f"api_key_name={E2E_KEY_NAME}")
            print(f"api_key_prefix={plain[:8]}…")
            # full key only once for local e2e wiring — caller stores in env
            print(f"NEXT_PUBLIC_BOTFAZER_API_KEY={plain}")

    await close_db()

    if args.write_env and plain:
        out = ROOT / "web" / ".env.local.e2e"
        out.write_text(
            "\n".join(
                [
                    "NEXT_PUBLIC_BOTFAZER_API_BASE_URL=http://127.0.0.1:8000",
                    f"NEXT_PUBLIC_BOTFAZER_API_KEY={plain}",
                    "NEXT_PUBLIC_MARKETSYNTH_INTEGRATION_MODE=backend",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"wrote={out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
