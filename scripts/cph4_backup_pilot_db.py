"""CPH.4 — create logical backup of botfazer_cph1 with checksum + manifest."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from scripts.cph4_common import (
    COMMERCIAL_TABLES,
    EXPECTED_REVISION,
    Cph4Error,
    assert_source_db,
    default_backup_root,
    find_pg_bin,
    now_iso,
    parse_db_name,
    run_pg,
    safe_url,
    sha256_file,
    to_dsn,
    utc_stamp,
)


async def collect_baseline(conn) -> dict:
    rev = await conn.fetchval("select version_num from alembic_version")
    if rev != EXPECTED_REVISION:
        raise Cph4Error("backup_revision_mismatch", f"got={rev} expected={EXPECTED_REVISION}")

    counts: dict[str, int] = {}
    for t in COMMERCIAL_TABLES:
        exists = await conn.fetchval(
            "select exists(select 1 from information_schema.tables "
            "where table_schema='public' and table_name=$1)",
            t,
        )
        counts[t] = int(await conn.fetchval(f'select count(*) from "{t}"')) if exists else -1

    firewall: dict[str, int] = {}
    from scripts.cph4_common import FIREWALL_TABLES

    for t in FIREWALL_TABLES:
        exists = await conn.fetchval(
            "select exists(select 1 from information_schema.tables "
            "where table_schema='public' and table_name=$1)",
            t,
        )
        if exists:
            firewall[t] = int(await conn.fetchval(f'select count(*) from "{t}"'))

    # Prefer a project with full commercial handoff lineage (IDs only).
    lineage: dict = {}
    project = await conn.fetchrow(
        """
        select p.id::text as id, p.owner_id::text as owner_id
        from projects p
        join implementation_marketing_plan_handoffs h on h.project_id = p.id
        join marketing_plans mp on mp.id = h.marketing_plan_id
        where mp.status = 'draft'
        order by h.created_at desc nulls last
        limit 1
        """
    )
    if project is None:
        project = await conn.fetchrow(
            "select id::text as id, owner_id::text as owner_id "
            "from projects order by created_at desc nulls last limit 1"
        )
    if project:
        pid = project["id"]
        lineage["project_id"] = pid
        lineage["project_owner_id"] = project["owner_id"]

        brief = await conn.fetchrow(
            "select id::text as id, version from project_briefs "
            "where project_id=$1::uuid order by version desc limit 1",
            pid,
        )
        if brief:
            lineage["brief_id"] = brief["id"]
            lineage["brief_version"] = brief["version"]

        inv = await conn.fetchrow(
            "select id::text as id, version from investigations "
            "where project_id=$1::uuid order by version desc limit 1",
            pid,
        )
        if inv:
            lineage["investigation_id"] = inv["id"]
            lineage["investigation_version"] = inv["version"]

        sources = await conn.fetch(
            "select id::text as id, version from sources "
            "where project_id=$1::uuid order by created_at desc nulls last limit 5",
            pid,
        )
        lineage["source_ids"] = [{"id": r["id"], "version": r["version"]} for r in sources]

        evidence = await conn.fetch(
            "select id::text as id, version, lifecycle_status "
            "from investigation_evidence where project_id=$1::uuid "
            "order by version desc limit 5",
            pid,
        )
        lineage["evidence"] = [
            {"id": r["id"], "version": r["version"], "lifecycle_status": r["lifecycle_status"]}
            for r in evidence
        ]

        verdict = await conn.fetchrow(
            "select id::text as id, version, evidence_snapshot_hash, lifecycle_status "
            "from business_verdicts where project_id=$1::uuid "
            "and lifecycle_status='approved' order by version desc limit 1",
            pid,
        )
        if verdict:
            lineage["verdict_id"] = verdict["id"]
            lineage["verdict_version"] = verdict["version"]
            lineage["evidence_snapshot_hash"] = verdict["evidence_snapshot_hash"]

        strategy = await conn.fetchrow(
            "select id::text as id, version, business_verdict_id::text as vid, "
            "lifecycle_status from marketing_strategies where project_id=$1::uuid "
            "and lifecycle_status='approved' order by version desc limit 1",
            pid,
        )
        if strategy:
            lineage["strategy_id"] = strategy["id"]
            lineage["strategy_version"] = strategy["version"]
            lineage["strategy_verdict_id"] = strategy["vid"]

        impl = await conn.fetchrow(
            "select id::text as id, version, marketing_strategy_id::text as sid, "
            "lifecycle_status from implementation_plans where project_id=$1::uuid "
            "and lifecycle_status='approved' order by version desc limit 1",
            pid,
        )
        if impl:
            lineage["impl_plan_id"] = impl["id"]
            lineage["impl_plan_version"] = impl["version"]
            lineage["impl_strategy_id"] = impl["sid"]

            handoff = await conn.fetchrow(
                "select id::text as id, mapping_fingerprint, marketing_plan_id::text as mpid "
                "from implementation_marketing_plan_handoffs "
                "where implementation_plan_id=$1::uuid order by created_at desc limit 1",
                impl["id"],
            )
            if handoff:
                lineage["handoff_id"] = handoff["id"]
                lineage["handoff_fingerprint"] = handoff["mapping_fingerprint"]
                lineage["handoff_marketing_plan_id"] = handoff["mpid"]

        mp = await conn.fetchrow(
            "select id::text as id, current_version_number, status from marketing_plans "
            "where project_id=$1::uuid order by current_version_number desc nulls last limit 1",
            pid,
        )
        if mp:
            lineage["marketing_plan_id"] = mp["id"]
            lineage["marketing_plan_version"] = mp["current_version_number"]
            lineage["marketing_plan_status"] = mp["status"]

    users = await conn.fetch(
        "select id::text as id, email, is_active, "
        "(password_hash is not null) as has_password_hash "
        "from users order by created_at nulls last limit 20"
    )
    lineage["users"] = [
        {
            "id": r["id"],
            "email_redacted": _redact_email(r["email"]),
            "is_active": r["is_active"],
            "has_password_hash": r["has_password_hash"],
        }
        for r in users
    ]

    sess = await conn.fetchrow(
        "select "
        "count(*) filter (where status='active' and revoked_at is null) as active_n, "
        "count(*) filter (where revoked_at is not null or status='revoked') as revoked_n, "
        "count(*) as total_n "
        "from browser_sessions"
    )
    lineage["sessions"] = {
        "active": int(sess["active_n"] or 0),
        "revoked": int(sess["revoked_n"] or 0),
        "total": int(sess["total_n"] or 0),
    }

    pg_ver = await conn.fetchval("select version()")
    return {
        "source_revision": rev,
        "postgres_version": str(pg_ver).split(",")[0][:120],
        "table_counts": counts,
        "firewall_counts": firewall,
        "commercial_lineage_sample": lineage,
    }


def _redact_email(email: str | None) -> str:
    if not email or "@" not in email:
        return "[redacted]"
    local, _, domain = email.partition("@")
    return f"{local[:2]}***@{domain}"


async def main_async(out_dir: Path, require_source: str) -> int:
    import asyncpg
    from app.core.config import get_settings

    settings = get_settings()
    db_name = parse_db_name(settings.database_url)
    assert_source_db(db_name)
    if require_source and db_name != require_source:
        raise Cph4Error("backup_source_database_mismatch", db_name)

    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp()
    backup_id = f"cph4_{db_name}_{stamp}"
    dump_path = out_dir / f"{backup_id}.dump"
    manifest_path = out_dir / f"{backup_id}.manifest.json"

    print("source_database=", db_name)
    print("database_url_safe=", safe_url(settings.database_url))
    print("backup_id=", backup_id)

    created_at = now_iso()
    t0 = time.perf_counter()

    conn = await asyncpg.connect(to_dsn(settings.database_url))
    try:
        baseline = await collect_baseline(conn)
    finally:
        await conn.close()

    baseline_path = out_dir / f"{backup_id}.baseline.json"
    baseline_path.write_text(
        json.dumps(baseline, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    pg_dump = find_pg_bin("pg_dump")
    u = __import__("urllib.parse", fromlist=["urlparse"]).urlparse(to_dsn(settings.database_url))
    dump_start = time.perf_counter()
    proc = run_pg(
        [
            str(pg_dump),
            "-h",
            u.hostname or "localhost",
            "-p",
            str(u.port or 5432),
            "-U",
            u.username or "botfazer",
            "-d",
            db_name,
            "-Fc",
            "--no-owner",
            "--no-acl",
            "-f",
            str(dump_path),
        ],
        url=settings.database_url,
    )
    dump_secs = round(time.perf_counter() - dump_start, 3)
    if proc.returncode != 0 or not dump_path.is_file():
        raise Cph4Error("restore_failed", (proc.stderr or proc.stdout or "")[:400])

    checksum_start = time.perf_counter()
    digest = sha256_file(dump_path)
    checksum_secs = round(time.perf_counter() - checksum_start, 3)
    completed_at = now_iso()

    # Prefer git commit if available
    app_commit = "unknown"
    try:
        import subprocess

        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(Path(__file__).resolve().parents[1]),
            capture_output=True,
            text=True,
            check=False,
        )
        if r.returncode == 0:
            app_commit = r.stdout.strip()
    except OSError:
        pass

    manifest = {
        "backup_id": backup_id,
        "source_database": db_name,
        "source_host_sanitized": f"{u.hostname or 'localhost'}:{u.port or 5432}",
        "source_revision": baseline["source_revision"],
        "postgres_version": baseline["postgres_version"],
        "application_commit": app_commit,
        "created_at": created_at,
        "completed_at": completed_at,
        "backup_format": "custom",
        "filename": dump_path.name,
        "file_size": dump_path.stat().st_size,
        "sha256": digest,
        "table_counts": baseline["table_counts"],
        "firewall_counts": baseline.get("firewall_counts", {}),
        "commercial_lineage_sample": baseline["commercial_lineage_sample"],
        "session_policy": "A_revoke_all_after_restore",
        "restore_test_status": "pending",
        "restore_database": None,
        "restore_verified_at": None,
        "timings_seconds": {
            "dump": dump_secs,
            "checksum": checksum_secs,
            "total_backup": round(time.perf_counter() - t0, 3),
        },
        "baseline_file": baseline_path.name,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print("manifest=", str(manifest_path))
    print("backup_file=", str(dump_path))
    print("sha256=", digest)
    print("file_size=", dump_path.stat().st_size)
    print("source_revision=", baseline["source_revision"])
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="CPH.4 backup pilot DB")
    parser.add_argument("--out", default=str(default_backup_root()))
    parser.add_argument("--require-db", default="botfazer_cph1")
    args = parser.parse_args()
    try:
        return asyncio.run(main_async(Path(args.out), args.require_db))
    except Cph4Error as exc:
        print(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
