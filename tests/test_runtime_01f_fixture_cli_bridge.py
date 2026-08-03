"""RUNTIME-01F — CLI fixture bridge boundary (scripts/e2e_biv_set_fixture.py)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest

from app.business_idea_validation.e2e_deterministic_fixture import (
    E2eDeterministicFixtureService,
    E2eDeterministicOutcome,
)
from app.core.config import get_settings
from scripts.e2e_biv_set_fixture import build_credentials
from tests.conftest import _create_user_with_api_key

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def biv_fixture_cli_env(monkeypatch: pytest.MonkeyPatch, database_url: str) -> str:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("BIV_E2E_DETERMINISTIC_ENABLED", "true")
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    return database_url


def _cli_env(database_url: str) -> dict[str, str]:
    import os

    env = os.environ.copy()
    env["APP_ENV"] = "test"
    env["BIV_E2E_DETERMINISTIC_ENABLED"] = "true"
    env["DATABASE_URL"] = database_url
    return env


def _run_cli(database_url: str, *args: str, expect_code: int = 0) -> dict:
    cmd = [sys.executable, "scripts/e2e_biv_set_fixture.py", *args]
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=_cli_env(database_url),
    )
    assert proc.returncode == expect_code, proc.stderr or proc.stdout
    if not proc.stdout.strip():
        return {}
    return json.loads(proc.stdout.strip())


@pytest.mark.asyncio
async def test_runtime_01f_cli_bind_and_clear_roundtrip(
    db_session,
    biv_fixture_cli_env: str,
) -> None:
    run_id = f"cli-bridge-{uuid4().hex[:8]}"
    email, _password = build_credentials(run_id)
    _api_key, user = await _create_user_with_api_key()
    user.email = email
    db_session.add(user)
    await db_session.commit()

    bound = _run_cli(biv_fixture_cli_env, "bind", "--run-id", run_id, "--outcome", "verdict")
    assert bound["action"] == "bind_fixture"
    assert bound["owner_id"] == str(user.id)
    assert "password" not in json.dumps(bound).lower()

    svc = E2eDeterministicFixtureService(db_session, get_settings())
    assert await svc.resolve_for_owner(user.id) == E2eDeterministicOutcome.VERDICT

    cleared = _run_cli(biv_fixture_cli_env, "clear", "--run-id", run_id)
    assert cleared["action"] == "clear_fixture"
    assert cleared["deleted"] >= 1

    cleared_again = _run_cli(biv_fixture_cli_env, "clear", "--run-id", run_id)
    assert cleared_again["deleted"] == 0


@pytest.mark.asyncio
async def test_runtime_01f_cli_bind_rejects_missing_user(
    db_session,
    biv_fixture_cli_env: str,
) -> None:
    run_id = f"missing-user-{uuid4().hex[:8]}"
    cmd = [
        sys.executable,
        "scripts/e2e_biv_set_fixture.py",
        "bind",
        "--run-id",
        run_id,
        "--outcome",
        "partial",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=_cli_env(biv_fixture_cli_env),
    )
    assert proc.returncode != 0
    assert "user not found" in (proc.stderr + proc.stdout).lower()


def test_runtime_01f_cli_bind_rejects_invalid_outcome(
    biv_fixture_cli_env: str,
) -> None:
    cmd = [
        sys.executable,
        "scripts/e2e_biv_set_fixture.py",
        "bind",
        "--run-id",
        "invalid-outcome-run",
        "--outcome",
        "not-a-valid-outcome",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=_cli_env(biv_fixture_cli_env),
    )
    assert proc.returncode != 0


@pytest.mark.asyncio
async def test_runtime_01f_cli_fixture_owner_isolation(
    db_session,
    biv_fixture_cli_env: str,
) -> None:
    run_a = f"owner-a-{uuid4().hex[:8]}"
    run_b = f"owner-b-{uuid4().hex[:8]}"
    email_a, _ = build_credentials(run_a)
    email_b, _ = build_credentials(run_b)
    _key_a, user_a = await _create_user_with_api_key()
    _key_b, user_b = await _create_user_with_api_key()
    user_a.email = email_a
    user_b.email = email_b
    db_session.add(user_a)
    db_session.add(user_b)
    await db_session.commit()

    _run_cli(biv_fixture_cli_env, "bind", "--run-id", run_a, "--outcome", "verdict")
    _run_cli(biv_fixture_cli_env, "bind", "--run-id", run_b, "--outcome", "partial")

    svc = E2eDeterministicFixtureService(db_session, get_settings())
    assert await svc.resolve_for_owner(user_a.id) == E2eDeterministicOutcome.VERDICT
    assert await svc.resolve_for_owner(user_b.id) == E2eDeterministicOutcome.PARTIAL
