"""Idempotent E2E MVP demo seed (Phase AI.80).

Usage:
    uv run python scripts/seed_e2e_demo.py
    uv run python scripts/seed_e2e_demo.py --refresh-api-key
    uv run python scripts/seed_e2e_demo.py --reset-db
    uv run python scripts/seed_e2e_demo.py --include-v2-marketing
    uv run python scripts/seed_e2e_demo.py --scenario dental_clinic_lead_gen
    uv run python scripts/seed_e2e_demo.py --wizard --scenario dental_clinic_lead_gen
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from sqlmodel import SQLModel

import app.db.models  # noqa: F401
from app.core.config import get_settings
from app.db.session import close_db, get_engine, get_session_factory, init_db, reset_db_state
from app.services.e2e_demo_seed_service import E2eDemoSeedService


def _sqlite_path_from_url(database_url: str) -> Path | None:
    prefix = "sqlite+aiosqlite:///"
    if database_url.startswith(prefix):
        raw = database_url.removeprefix(prefix)
        return Path(raw) if raw != ":memory:" else None
    return None


def _reset_sqlite_database() -> None:
    settings = get_settings()
    db_path = _sqlite_path_from_url(settings.database_url)
    if db_path is None:
        raise RuntimeError("--reset-db only supports local sqlite+aiosqlite file databases")
    reset_db_state()
    if db_path.exists():
        db_path.unlink()
        print(f"Removed database file {db_path}")


async def _ensure_schema(*, reset_db: bool) -> None:
    if reset_db:
        await asyncio.to_thread(_reset_sqlite_database)
    await init_db()
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def run_seed(
    *,
    refresh_api_key: bool,
    reset_db: bool,
    include_v2_marketing: bool,
    scenario: str | None,
    wizard: bool,
) -> None:
    await _ensure_schema(reset_db=reset_db)
    factory = get_session_factory()
    async with factory() as session:
        result = await E2eDemoSeedService(session).seed(
            refresh_api_key=refresh_api_key,
            include_v2_marketing=include_v2_marketing,
            scenario=scenario,
            wizard=wizard,
        )
        await session.commit()

    print("E2E demo seed complete.")
    print(f"  project_id={result.project_id}")
    print(f"  marketing_plan_id={result.marketing_plan_id}")
    print(f"  execution_run_id={result.execution_run_id}")
    print(f"  copywriter_output_id={result.copywriter_output_id}")
    print(f"  content_asset_id={result.content_asset_id}")
    print(f"  media_brief_id={result.media_brief_id}")
    print(f"  media_asset_id={result.media_asset_id}")
    print(f"  publication_package_id={result.publication_package_id}")
    print(f"  foundation_channel_id={result.foundation_channel_id}")
    print(f"  publication_package_job_id={result.publication_package_job_id}")
    if result.api_key_plain:
        print(f"  api_key={result.api_key_plain}")
    if result.scenario_plan_id:
        print(f"  scenario_plan_id={result.scenario_plan_id}")
    if result.wizard_run_id:
        print(f"  wizard_run_id={result.wizard_run_id}")
    print()
    print("UI env:")
    print(f"  NEXT_PUBLIC_BOTFAZER_PROJECT_ID={result.project_id}")
    if result.api_key_plain:
        print(f"  NEXT_PUBLIC_BOTFAZER_API_KEY={result.api_key_plain}")
    print()
    print("Smoke:")
    print(f"  GET /projects/{result.project_id}/demo-flow/status")
    print(
        f"  GET /projects/{result.project_id}/provenance/content-production/"
        f"{result.publication_package_job_id}",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed E2E MVP demo data")
    parser.add_argument(
        "--refresh-api-key",
        action="store_true",
        help="Revoke and mint a new demo API key",
    )
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Reset local sqlite database before seeding",
    )
    parser.add_argument(
        "--include-v2-marketing",
        action="store_true",
        help="Also seed v2 marketing specialist outputs (offer through ad creative)",
    )
    parser.add_argument(
        "--scenario",
        metavar="SCENARIO_ID",
        default=None,
        help="Also create a draft marketing plan from a product scenario (e.g. dental_clinic_lead_gen)",
    )
    parser.add_argument(
        "--wizard",
        action="store_true",
        help="With --scenario: create wizard run and advance to queued dry-run job (seed only)",
    )
    args = parser.parse_args()
    try:
        asyncio.run(
            run_seed(
                refresh_api_key=args.refresh_api_key,
                reset_db=args.reset_db,
                include_v2_marketing=args.include_v2_marketing,
                scenario=args.scenario,
                wizard=args.wizard,
            ),
        )
    except Exception as exc:
        print(f"Seed failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    finally:
        asyncio.run(close_db())


if __name__ == "__main__":
    main()
