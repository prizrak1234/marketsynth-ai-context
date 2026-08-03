"""PRODUCT-01.2 — PostgreSQL Alembic migration verification (optional live DB)."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

PRODUCT_01_REVISION = "20260724_0059"
MIGRATION_FILE = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20260724_0059_offer_builder_product_01.py"
)


def test_migration_file_revision_chain() -> None:
    assert MIGRATION_FILE.is_file()
    spec = importlib.util.spec_from_file_location("offer_migration", MIGRATION_FILE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == PRODUCT_01_REVISION
    assert module.down_revision == "20260723_0058"


@pytest.mark.integration
def test_postgres_alembic_upgrade_head() -> None:
    """Runs scripts/verify_product_01_postgres_migration.py when DATABASE_URL is PostgreSQL."""
    url = os.environ.get("DATABASE_URL", "")
    if not url or "postgres" not in url:
        pytest.skip("blocked_by_missing_postgres_database_url")

    result = subprocess.run(
        ["uv", "run", "python", "scripts/verify_product_01_postgres_migration.py"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "DATABASE_URL": url},
    )
    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "passed"
    assert payload["final_revision"] == PRODUCT_01_REVISION
