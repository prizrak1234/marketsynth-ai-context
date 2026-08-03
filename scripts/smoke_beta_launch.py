"""Beta launch smoke checks (Phase AI.99).

Runs locally without external APIs. Exit code 1 on any failure.

Usage:
    uv run python scripts/smoke_beta_launch.py
    uv run python scripts/smoke_beta_launch.py --skip-alembic
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path

from sqlmodel import SQLModel

import app.db.models  # noqa: F401
from app.core.config import get_settings
from app.db.session import close_db, get_engine, get_session_factory, init_db, reset_db_state
from app.services.beta_access_service import BetaAccessService
from app.services.beta_admin_service import BetaAdminService
from app.services.beta_guide_service import BetaGuideService
from app.services.demo_flow_status_service import DemoFlowStatusService
from app.services.e2e_demo_seed_service import E2eDemoSeedService
from app.services.publication_package_job_service import PublicationPackageJobService


_FAILURES: list[str] = []


def _record(name: str, exc: Exception | None = None) -> None:
    if exc is None:
        print(f"OK  {name}")
    else:
        print(f"FAIL {name}: {exc}", file=sys.stderr)
        _FAILURES.append(name)


def check_alembic_head() -> None:
    try:
        result = subprocess.run(
            ["uv", "run", "alembic", "current"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[1],
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "alembic current failed")
        head = subprocess.run(
            ["uv", "run", "alembic", "heads"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[1],
        )
        if head.returncode != 0:
            raise RuntimeError(head.stderr.strip() or "alembic heads failed")
        if "20260603_0021" not in head.stdout and "(head)" not in head.stdout:
            raise RuntimeError(f"unexpected alembic heads: {head.stdout.strip()}")
    except Exception as exc:
        _record("alembic_head", exc)
        return
    _record("alembic_head")


async def _ensure_schema() -> None:
    reset_db_state()
    await init_db()
    settings = get_settings()
    if not settings.database_url.startswith("sqlite"):
        # PostgreSQL schema comes from Alembic; create_all uses VARCHAR for enums.
        return
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def run_smoke(*, skip_alembic: bool) -> None:
    if skip_alembic:
        _record("alembic_head (skipped)")
    else:
        check_alembic_head()

    await _ensure_schema()

    try:
        from fastapi.testclient import TestClient

        from app.main import app

        with TestClient(app) as http_client:
            health = http_client.get("/health")
            if health.status_code != 200:
                raise RuntimeError(f"health status {health.status_code}")
        _record("health")
    except Exception as exc:
        _record("health", exc)

    factory = get_session_factory()

    async with factory() as session:
        try:
            seed = await E2eDemoSeedService(session).seed()
            await session.commit()
            _record("seed_e2e_demo")
        except Exception as exc:
            _record("seed_e2e_demo", exc)
            return

        try:
            status = await DemoFlowStatusService(session).get_status(
                seed.user_id,
                seed.project_id,
            )
            if status is None or status.publication_job_status != "queued":
                raise RuntimeError(f"unexpected demo status: {status}")
            _record("demo_flow_status")
        except Exception as exc:
            _record("demo_flow_status", exc)

        try:
            export = await BetaAdminService(session).get_qa_export()
            blob = json.dumps(export.model_dump(mode="json")).lower()
            for forbidden in ("bot_token", "prompt", "payload_snapshot", "description"):
                if forbidden in blob:
                    raise RuntimeError(f"qa export leaked {forbidden}")
            _record("qa_export_safe")
        except Exception as exc:
            _record("qa_export_safe", exc)

        try:
            job_service = PublicationPackageJobService(session)
            row = await job_service.execute_dry_run(
                seed.user_id,
                seed.project_id,
                seed.publication_package_job_id,
            )
            if row is None:
                raise RuntimeError("dry-run dispatch returned None")
            await session.commit()
            _record("dry_run_dispatch")
        except Exception as exc:
            _record("dry_run_dispatch", exc)

    try:
        guide = BetaGuideService.get_guide()
        if not guide.expected_path or not guide.feedback_instructions:
            raise RuntimeError("beta guide incomplete")
        _record("beta_guide_content")
    except Exception as exc:
        _record("beta_guide_content", exc)

    try:
        settings = get_settings()
        if not hasattr(settings, "beta_access_gate_enabled"):
            raise RuntimeError("beta_access_gate_enabled missing from settings")
        _record("beta_access_config")
    except Exception as exc:
        _record("beta_access_config", exc)

def main() -> None:
    parser = argparse.ArgumentParser(description="Beta launch smoke checks")
    parser.add_argument(
        "--skip-alembic",
        action="store_true",
        help="Skip alembic head verification (e.g. CI without migration DB)",
    )
    args = parser.parse_args()
    _FAILURES.clear()
    try:
        asyncio.run(run_smoke(skip_alembic=args.skip_alembic))
    finally:
        asyncio.run(close_db())
    if _FAILURES:
        print(f"\n{len(_FAILURES)} check(s) failed.", file=sys.stderr)
        raise SystemExit(1)
    print("\nAll beta launch smoke checks passed.")


if __name__ == "__main__":
    main()
