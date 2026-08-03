"""CPH.5 — rollback dry-run (non-destructive). Does not mutate botfazer_cph1."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    steps = []
    # Identify current commit
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    steps.append(
        {
            "step": "identify_release",
            "commit": commit.stdout.strip() if commit.returncode == 0 else "unknown",
            "action": "document_only",
        }
    )
    steps.append(
        {
            "step": "stop_traffic",
            "action": "operator_stops_uvicorn_and_next",
            "automated": False,
        }
    )
    steps.append(
        {
            "step": "retain_database",
            "action": "do_not_drop botfazer_cph1",
            "database": "botfazer_cph1",
        }
    )
    steps.append(
        {
            "step": "migration_check",
            "policy": "forward_only; if schema migrated, prefer DB restore from CPH.4 backup",
            "auto_migrate": False,
            "auto_stamp": False,
        }
    )
    steps.append(
        {
            "step": "restore_previous_app_version",
            "action": "git checkout <previous_commit> locally (manual; no remote)",
            "note": "CPH.5 dry-run does not switch branches",
        }
    )
    steps.append(
        {
            "step": "verify_revision_compatibility",
            "command": "uv run python scripts/cph1_db_tools.py check-revision",
        }
    )
    steps.append(
        {
            "step": "health_checks",
            "endpoints": ["/health/live", "/health/ready"],
        }
    )
    steps.append(
        {
            "step": "authenticated_smoke",
            "command": "uv run python -m scripts.cph5_post_deploy_smoke",
        }
    )
    result = {
        "ok": True,
        "dry_run": True,
        "destructive": False,
        "completed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "steps": steps,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
