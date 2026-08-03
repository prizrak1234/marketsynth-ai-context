"""CPH.4 shared guards, errors, and PostgreSQL helpers.

Never print passwords, raw session tokens, or Brief/Evidence payloads.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXPECTED_REVISION = "20260715_0037"
SOURCE_DB_REQUIRED = "botfazer_cph1"
PROTECTED_SOURCE_DBS = frozenset({"botfazer_cph1", "botfazer", "postgres", "template0", "template1"})
RESTORE_PREFIX = "botfazer_cph4_restore_"

CPH4_ERRORS = frozenset(
    {
        "backup_source_database_mismatch",
        "backup_revision_mismatch",
        "backup_checksum_failed",
        "backup_file_missing",
        "backup_manifest_missing",
        "restore_target_unsafe",
        "restore_failed",
        "restored_revision_unknown",
        "schema_parity_failed",
        "row_count_mismatch",
        "lineage_integrity_failed",
        "session_invalidation_failed",
        "authenticated_smoke_failed",
        "cleanup_failed",
        "owner_approval_required",
    }
)

COMMERCIAL_TABLES = [
    "users",
    "browser_sessions",
    "projects",
    "project_briefs",
    "investigations",
    "sources",
    "investigation_source_links",
    "investigation_evidence",
    "evidence_source_links",
    "business_verdicts",
    "business_verdict_evidence_snapshots",
    "business_verdict_evidence_links",
    "marketing_strategies",
    "implementation_plans",
    "implementation_marketing_plan_handoffs",
    "marketing_plans",
]

FIREWALL_TABLES = [
    "marketing_plan_execution_runs",
    "marketing_specialist_outputs",
    "campaigns",
    "execution_approvals",
    "publication_jobs",
]


class Cph4Error(SystemExit):
    def __init__(self, code: str, detail: str = "") -> None:
        if code not in CPH4_ERRORS:
            code = "restore_failed"
        msg = f"error={code}" + (f" detail={detail}" if detail else "")
        super().__init__(msg)
        self.code = code


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_url(url: str) -> str:
    return re.sub(r"://([^:/]+):([^@]+)@", r"://\1:***@", url)


def to_dsn(url: str) -> str:
    for p in (
        "postgresql+asyncpg://",
        "postgresql+psycopg://",
        "postgresql+psycopg2://",
    ):
        if url.startswith(p):
            return "postgresql://" + url[len(p) :]
    return url


def parse_db_name(url: str) -> str:
    u = urlparse(to_dsn(url))
    return (u.path or "").lstrip("/")


def admin_dsn(url: str) -> str:
    dsn = to_dsn(url)
    u = urlparse(dsn)
    return f"{u.scheme}://{u.netloc}/postgres"


def replace_db(url: str, db_name: str) -> str:
    dsn = to_dsn(url)
    u = urlparse(dsn)
    return f"{u.scheme}://{u.netloc}/{db_name}"


def default_backup_root() -> Path:
    return Path.home() / "botfazer_backups" / "cph4"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def find_pg_bin(tool: str) -> Path:
    candidates = [
        Path(rf"C:\Program Files\PostgreSQL\17\bin\{tool}.exe"),
        Path(rf"C:\Program Files\PostgreSQL\16\bin\{tool}.exe"),
        Path(rf"C:\Program Files\PostgreSQL\15\bin\{tool}.exe"),
    ]
    for c in candidates:
        if c.exists():
            return c
    which = shutil.which(tool)
    if which:
        return Path(which)
    raise Cph4Error("restore_failed", f"{tool}_not_found")


def pg_env_from_url(url: str) -> dict[str, str]:
    env = os.environ.copy()
    u = urlparse(to_dsn(url))
    if u.password and "PGPASSWORD" not in env:
        env["PGPASSWORD"] = u.password
    return env


def assert_source_db(db_name: str) -> None:
    if db_name != SOURCE_DB_REQUIRED:
        raise Cph4Error(
            "backup_source_database_mismatch",
            f"expected={SOURCE_DB_REQUIRED} got={db_name}",
        )


def assert_restore_target(db_name: str, *, allow_recreate: bool = False) -> None:
    """Refuse pilot source, legacy, and system DBs. Require cph4 restore prefix."""
    if db_name in PROTECTED_SOURCE_DBS:
        raise Cph4Error("restore_target_unsafe", f"protected={db_name}")
    if not db_name.startswith(RESTORE_PREFIX):
        raise Cph4Error(
            "restore_target_unsafe",
            f"must_start_with={RESTORE_PREFIX} got={db_name}",
        )
    if not re.fullmatch(r"botfazer_cph4_restore_[a-zA-Z0-9_]+", db_name):
        raise Cph4Error("restore_target_unsafe", f"bad_pattern={db_name}")
    if not allow_recreate:
        # Caller still may recreate with explicit flag; this documents the gate.
        pass


def require_owner_approval() -> None:
    if os.environ.get("CPH4_CONFIRM_RESTORE", "").strip() != "1":
        raise Cph4Error(
            "owner_approval_required",
            "set CPH4_CONFIRM_RESTORE=1 to recreate disposable restore DB",
        )


def run_pg(
    args: list[str],
    *,
    url: str,
    timeout: int = 600,
) -> subprocess.CompletedProcess[str]:
    env = pg_env_from_url(url)
    return subprocess.run(
        args,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
