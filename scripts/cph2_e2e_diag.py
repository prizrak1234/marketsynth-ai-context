"""CPH.2 safe environment diagnostic — no secrets printed."""

from __future__ import annotations

import asyncio
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def safe_url(url: str) -> str:
    return re.sub(r"://([^:/]+):([^@]+)@", r"://\1:***@", url)


def db_name(url: str) -> str:
    raw = url.replace("+asyncpg", "").replace("+psycopg", "")
    return (urlparse(raw).path or "").lstrip("/")


async def main() -> int:
    from app.core.config import get_settings
    from app.domain.alembic_revision_guard import classify_revision
    from scripts.cph1_db_tools import to_dsn
    import asyncpg

    settings = get_settings()
    frontend = os.environ.get("CPH2_FRONTEND_URL", "http://localhost:3000")
    backend = os.environ.get("CPH2_BACKEND_URL", "http://127.0.0.1:8000")
    mode = os.environ.get(
        "NEXT_PUBLIC_MARKETSYNTH_INTEGRATION_MODE",
        os.environ.get("CPH2_INTEGRATION_MODE", ""),
    ).strip().lower()

    name = db_name(settings.database_url)
    print("frontend_url=", frontend)
    print("backend_url=", backend)
    print("database_name=", name)
    print("database_url_safe=", safe_url(settings.database_url))
    print("integration_mode=", mode or "(unset)")
    print("real_execution_expansion=", getattr(settings, "real_execution_expansion_enabled", None))
    print("workflow_n8n_enabled=", getattr(settings, "workflow_n8n_enabled", None))
    print("telegram_publishing_enabled=", getattr(settings, "telegram_publishing_enabled", None))

    key = os.environ.get("NEXT_PUBLIC_BOTFAZER_API_KEY") or os.environ.get("CPH2_API_KEY") or ""
    print("test_user_key_sanitized=", (key[:6] + "…" + key[-4:]) if len(key) > 12 else "(missing)")

    if mode == "mock":
        print("FAIL=integration mode is mock")
        return 4
    if name in {"botfazer", "postgres"}:
        print("FAIL=legacy or system database")
        return 3

    conn = await asyncpg.connect(to_dsn(settings.database_url))
    try:
        revs = [r["version_num"] for r in await conn.fetch("select version_num from alembic_version")]
    finally:
        await conn.close()
    diag = classify_revision(database_revisions=revs)
    print("alembic_revisions=", list(diag.database_revisions))
    print("alembic_state=", diag.state.value)
    if diag.state.value != "current" or "20260614_0036" not in diag.database_revisions:
        print("FAIL=pilot revision must be 20260614_0036 current")
        return 5
    if not mode or mode not in {"backend", "hybrid"}:
        print("WARN=set NEXT_PUBLIC_MARKETSYNTH_INTEGRATION_MODE=backend for full happy path")
    print("ok=True")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
