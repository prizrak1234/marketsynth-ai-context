#!/usr/bin/env python3
"""Dev-only BIV browser smoke seed — creates repeatable pilot user for E2E."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

DEV_EMAIL = "biv-smoke@marketsynth.local"
DEV_PASSWORD = "BivSmoke!2026"


async def _provision() -> None:
    from app.core.config import get_settings
    from app.db.session import async_session_factory
    from app.services.auth_service import AuthService

    settings = get_settings()
    async with async_session_factory() as session:
        auth = AuthService(session, settings)
        user = await auth.get_user_by_email(DEV_EMAIL)
        if user is None:
            user = await auth.register_user(email=DEV_EMAIL, password=DEV_PASSWORD)
            print(f"created user {DEV_EMAIL}")
        else:
            await auth.set_password(user.id, DEV_PASSWORD)
            print(f"reset password for {DEV_EMAIL}")
        await session.commit()
    env_path = os.path.join(os.path.dirname(__file__), "..", "web", ".env.local.e2e")
    with open(env_path, "w", encoding="utf-8") as fh:
        fh.write(f"CPH3_E2E_EMAIL={DEV_EMAIL}\n")
        fh.write(f"CPH3_E2E_PASSWORD={DEV_PASSWORD}\n")
    print(f"wrote {env_path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provision", action="store_true")
    args = parser.parse_args()
    if not args.provision:
        print("Usage: uv run python scripts/biv_dev_smoke_seed.py --provision")
        return 1
    if os.getenv("ENVIRONMENT", "development") == "production":
        print("Refusing to provision dev smoke user in production", file=sys.stderr)
        return 2
    asyncio.run(_provision())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
