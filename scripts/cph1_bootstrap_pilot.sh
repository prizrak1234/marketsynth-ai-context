#!/usr/bin/env bash
# CPH.1 — bootstrap pilot DB to Commercial MVP head (requires empty disposable DB).
# Usage (PowerShell):
#   $env:DATABASE_URL = "postgresql+asyncpg://botfazer:***@localhost:5432/botfazer_cph1"
#   ./scripts/cph1_bootstrap_pilot.sh
set -euo pipefail
echo "target DATABASE_URL must already point to disposable DB (not botfazer)"
python - <<'PY'
from app.core.config import get_settings
from scripts.cph1_db_tools import FORBIDDEN_TARGETS, parse_db_name
name = parse_db_name(get_settings().database_url)
if name in FORBIDDEN_TARGETS:
    raise SystemExit(f"refused: DATABASE_URL points to forbidden db={name}")
print("bootstrap_db=", name)
PY
uv run alembic upgrade head
uv run python scripts/cph1_db_tools.py check-revision
uv run python scripts/cph1_db_tools.py schema-parity
echo "bootstrap_ok"
