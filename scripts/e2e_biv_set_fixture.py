"""Bind server-side deterministic BIV fixture for Playwright E2E (no HTTP test controls)."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from sqlmodel import select

from app.business_idea_validation.e2e_deterministic_fixture import (
    E2eDeterministicFixtureService,
    E2eDeterministicOutcome,
)
from app.core.config import get_settings
from app.db.models.user import UserTable
from app.db.session import get_session_factory

E2E_DOMAIN = os.environ.get("BIV_E2E_EMAIL_DOMAIN", "marketsynth.test")


def build_credentials(run_id: str) -> tuple[str, str]:
    safe_run_id = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in run_id)
    email = f"biv-e2e-{safe_run_id}@{E2E_DOMAIN}"
    password = f"BivE2E_{safe_run_id}!26"
    return email, password


async def _bind_fixture(run_id: str, outcome: str) -> dict:
    settings = get_settings()
    if not settings.biv_e2e_deterministic_allowed:
        raise RuntimeError("BIV_E2E_DETERMINISTIC_ENABLED requires APP_ENV development/test")

    email, _password = build_credentials(run_id)
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(select(UserTable).where(UserTable.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            raise RuntimeError(f"e2e user not found for run_id={run_id}; run provision first")

        svc = E2eDeterministicFixtureService(session, settings)
        await svc.bind_for_owner(
            user.id,
            E2eDeterministicOutcome(outcome),
            e2e_run_id=run_id,
        )
        await session.commit()
        return {
            "action": "bind_fixture",
            "run_id": run_id,
            "email": email,
            "owner_id": str(user.id),
            "outcome": outcome,
        }


async def _clear_fixture(run_id: str) -> dict:
    settings = get_settings()
    factory = get_session_factory()
    async with factory() as session:
        svc = E2eDeterministicFixtureService(session, settings)
        deleted = await svc.clear_for_e2e_run(run_id)
        await session.commit()
        return {"action": "clear_fixture", "run_id": run_id, "deleted": deleted}


def main() -> int:
    parser = argparse.ArgumentParser(description="Bind internal BIV E2E deterministic fixture")
    parser.add_argument("command", choices=["bind", "clear"])
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--outcome",
        choices=[item.value for item in E2eDeterministicOutcome],
        help="Required for bind",
    )
    args = parser.parse_args()

    if args.command == "bind":
        if not args.outcome:
            parser.error("--outcome is required for bind")
        result = asyncio.run(_bind_fixture(args.run_id, args.outcome))
    else:
        result = asyncio.run(_clear_fixture(args.run_id))

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
