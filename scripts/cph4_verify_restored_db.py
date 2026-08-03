"""CPH.4 — verify restored disposable DB: schema, counts, lineage, sessions, smoke."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

from scripts.cph4_backup_pilot_db import collect_baseline
from scripts.cph4_common import (
    COMMERCIAL_TABLES,
    EXPECTED_REVISION,
    Cph4Error,
    assert_restore_target,
    now_iso,
    replace_db,
    safe_url,
    to_dsn,
)


async def revoke_all_sessions(conn) -> int:
    """Policy A: revoke every restored session before opening the environment."""
    result = await conn.execute(
        "update browser_sessions set status='revoked', revoked_at=now() "
        "where revoked_at is null or status='active'"
    )
    # asyncpg returns 'UPDATE N'
    try:
        return int(str(result).split()[-1])
    except (ValueError, IndexError):
        return 0


async def check_orphans(conn) -> list[str]:
    problems: list[str] = []
    n = await conn.fetchval(
        "select count(*) from project_briefs b "
        "left join projects p on p.id=b.project_id where p.id is null"
    )
    if n:
        problems.append(f"orphan_project_briefs={n}")
    n = await conn.fetchval(
        "select count(*) from investigations i "
        "left join projects p on p.id=i.project_id where p.id is null"
    )
    if n:
        problems.append(f"orphan_investigations={n}")
    n = await conn.fetchval(
        "select count(*) from investigation_source_links l "
        "left join sources s on s.id=l.source_id where s.id is null"
    )
    if n:
        problems.append(f"orphan_investigation_source_links={n}")
    n = await conn.fetchval(
        "select count(*) from evidence_source_links l "
        "left join sources s on s.id=l.source_id where s.id is null"
    )
    if n:
        problems.append(f"orphan_evidence_source_links={n}")
    n = await conn.fetchval(
        """
        select count(*) from investigation_source_links l
        join sources s on s.id = l.source_id
        join investigations i on i.id = l.investigation_id
        where s.project_id <> i.project_id
        """
    )
    if n:
        problems.append(f"cross_project_source_links={n}")
    return problems


def compare_counts(expected: dict, actual: dict) -> list[str]:
    mismatches = []
    for k, v in expected.items():
        if actual.get(k) != v:
            mismatches.append(f"{k}: expected={v} actual={actual.get(k)}")
    return mismatches


def compare_lineage(expected: dict, actual: dict) -> list[str]:
    keys = [
        "project_id",
        "brief_id",
        "brief_version",
        "investigation_id",
        "investigation_version",
        "verdict_id",
        "verdict_version",
        "evidence_snapshot_hash",
        "strategy_id",
        "strategy_version",
        "impl_plan_id",
        "impl_plan_version",
        "handoff_id",
        "handoff_fingerprint",
        "marketing_plan_id",
        "marketing_plan_version",
        "marketing_plan_status",
    ]
    problems = []
    for k in keys:
        if k in expected and expected[k] != actual.get(k):
            problems.append(f"{k}: expected={expected[k]!r} actual={actual.get(k)!r}")
    return problems


async def authenticated_smoke(
    target_async_url: str,
    email: str,
    password: str,
    *,
    preferred_project_id: str | None = None,
) -> dict:
    """Login + /auth/me + project open + write smoke against restored DB."""
    from app.core.config import get_settings
    from app.db.session import reset_db_state
    from app.main import app
    from fastapi.testclient import TestClient

    os.environ["DATABASE_URL"] = target_async_url
    get_settings.cache_clear()
    reset_db_state()

    origin = {"Origin": "http://localhost:3000"}
    timings: dict[str, float] = {}
    t0 = time.perf_counter()
    try:
        with TestClient(app) as client:
            bad = client.get("/auth/me")
            if bad.status_code == 200:
                raise Cph4Error("session_invalidation_failed", "anonymous_me_succeeded")

            login = client.post(
                "/auth/login",
                json={"email": email, "password": password},
                headers=origin,
            )
            if login.status_code != 200:
                raise Cph4Error(
                    "authenticated_smoke_failed",
                    f"login_status={login.status_code} body={login.text[:200]}",
                )

            me = client.get("/auth/me")
            if me.status_code != 200:
                raise Cph4Error("authenticated_smoke_failed", "me_failed")
            me_body = me.json()

            projects = client.get("/projects")
            if projects.status_code != 200:
                raise Cph4Error("authenticated_smoke_failed", f"projects={projects.status_code}")
            items = projects.json()
            if not isinstance(items, list) or not items:
                raise Cph4Error("authenticated_smoke_failed", "no_projects")
            ids = {str(p["id"]) for p in items}
            if preferred_project_id and preferred_project_id in ids:
                project_id = preferred_project_id
            else:
                project_id = items[0]["id"]

            project_get = client.get(f"/projects/{project_id}")
            if project_get.status_code != 200:
                raise Cph4Error(
                    "authenticated_smoke_failed",
                    f"project_get={project_get.status_code}",
                )

            # Confirm restored MarketingPlan remains draft when present
            mp = client.get(f"/projects/{project_id}/marketing-plans")
            mp_statuses = []
            if mp.status_code == 200:
                body = mp.json()
                plans = body if isinstance(body, list) else body.get("items", [])
                mp_statuses = [p.get("status") for p in plans if isinstance(p, dict)]
                if mp_statuses and any(s not in (None, "draft") for s in mp_statuses):
                    raise Cph4Error(
                        "lineage_integrity_failed",
                        f"non_draft_plans={mp_statuses}",
                    )

            label = f"CPH4-RESTORE-SMOKE-{now_iso().replace(':', '')}"
            created = client.post(
                "/projects",
                json={"name": label, "description": "cph4 restore write smoke"},
                headers=origin,
            )
            write_ok = created.status_code in (200, 201)
            if not write_ok:
                raise Cph4Error(
                    "authenticated_smoke_failed",
                    f"write_status={created.status_code}",
                )

            logout = client.post("/auth/logout", headers=origin)
            if logout.status_code not in (200, 204):
                raise Cph4Error("authenticated_smoke_failed", f"logout={logout.status_code}")
            after = client.get("/auth/me")
            if after.status_code == 200:
                raise Cph4Error("authenticated_smoke_failed", "logout_did_not_invalidate")

            timings["smoke"] = round(time.perf_counter() - t0, 3)
            return {
                "login_ok": True,
                "user_id": me_body.get("id") or me_body.get("user", {}).get("id"),
                "project_id_seen": project_id,
                "marketing_plan_statuses": mp_statuses,
                "write_smoke_ok": write_ok,
                "write_status": created.status_code,
                "logout_invalidated": True,
                "timings_seconds": timings,
            }
    finally:
        reset_db_state()
        get_settings.cache_clear()


async def main_async(args: argparse.Namespace) -> dict:
    import asyncpg
    from app.core.config import get_settings

    assert_restore_target(args.target)
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    settings = get_settings()
    target_url = replace_db(settings.database_url, args.target)
    print("verify_target=", args.target)
    print("target_url_safe=", safe_url(target_url))

    t_schema = time.perf_counter()
    conn = await asyncpg.connect(to_dsn(target_url))
    try:
        rev = await conn.fetchval("select version_num from alembic_version")
        if rev != EXPECTED_REVISION:
            raise Cph4Error("backup_revision_mismatch", f"restored={rev}")

        missing = []
        for t in COMMERCIAL_TABLES:
            ok = await conn.fetchval(
                "select exists(select 1 from information_schema.tables "
                "where table_schema='public' and table_name=$1)",
                t,
            )
            if not ok:
                missing.append(t)
        if missing:
            raise Cph4Error("schema_parity_failed", f"missing={missing}")

        # password hashes: reject trivial plaintext values only
        plain = await conn.fetchval(
            "select count(*) from users where password_hash in ('password','admin','test')"
        )
        if plain:
            raise Cph4Error("lineage_integrity_failed", "plaintext_password_detected")

        baseline = await collect_baseline(conn)
        schema_secs = round(time.perf_counter() - t_schema, 3)

        count_mismatches = compare_counts(
            manifest.get("table_counts", {}), baseline["table_counts"]
        )
        # After write smoke we may add a project — compare BEFORE smoke and note separately
        lineage_problems = compare_lineage(
            manifest.get("commercial_lineage_sample", {}),
            baseline["commercial_lineage_sample"],
        )
        orphans = await check_orphans(conn)
        if orphans:
            raise Cph4Error("lineage_integrity_failed", ";".join(orphans))
        if count_mismatches:
            raise Cph4Error("row_count_mismatch", "; ".join(count_mismatches[:12]))
        if lineage_problems:
            raise Cph4Error("lineage_integrity_failed", "; ".join(lineage_problems[:12]))

        mp_status = baseline["commercial_lineage_sample"].get("marketing_plan_status")
        if mp_status and mp_status != "draft":
            raise Cph4Error(
                "lineage_integrity_failed",
                f"marketing_plan_not_draft={mp_status}",
            )

        revoked_n = await revoke_all_sessions(conn)
        active_after = await conn.fetchval(
            "select count(*) from browser_sessions "
            "where status='active' and revoked_at is null"
        )
        if active_after:
            raise Cph4Error(
                "session_invalidation_failed",
                f"active_remaining={active_after}",
            )

        firewall_before = baseline.get("firewall_counts", {})
    finally:
        await conn.close()

    email = os.environ.get("CPH3_E2E_EMAIL") or os.environ.get("CPH4_SMOKE_EMAIL")
    password = os.environ.get("CPH3_E2E_PASSWORD") or os.environ.get("CPH4_SMOKE_PASSWORD")
    smoke = None
    if email and password and not args.skip_smoke:
        # Ensure asyncpg scheme for SQLAlchemy
        async_url = target_url
        if async_url.startswith("postgresql://"):
            async_url = async_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif "+asyncpg" not in async_url and async_url.startswith("postgresql+"):
            pass
        preferred = manifest.get("commercial_lineage_sample", {}).get("project_id")
        smoke = await authenticated_smoke(
            async_url, email, password, preferred_project_id=preferred
        )
        # Re-check firewall after smoke
        conn2 = await asyncpg.connect(to_dsn(target_url))
        try:
            from scripts.cph4_common import FIREWALL_TABLES

            firewall_after = {}
            for t in FIREWALL_TABLES:
                exists = await conn2.fetchval(
                    "select exists(select 1 from information_schema.tables "
                    "where table_schema='public' and table_name=$1)",
                    t,
                )
                if exists:
                    firewall_after[t] = int(await conn2.fetchval(f'select count(*) from "{t}"'))
            for t, n in firewall_before.items():
                if firewall_after.get(t, n) != n:
                    raise Cph4Error(
                        "authenticated_smoke_failed",
                        f"firewall_delta {t}: {n}->{firewall_after.get(t)}",
                    )
        finally:
            await conn2.close()
    elif not args.skip_smoke:
        raise Cph4Error(
            "authenticated_smoke_failed",
            "set CPH3_E2E_EMAIL and CPH3_E2E_PASSWORD (or CPH4_SMOKE_*)",
        )

    return {
        "ok": True,
        "restore_database": args.target,
        "restored_revision": rev,
        "schema_parity": "pass",
        "row_counts": "pass",
        "lineage": "pass",
        "sessions_revoked": revoked_n,
        "active_sessions_after_policy": 0,
        "marketing_plan_status": mp_status,
        "authenticated_smoke": smoke,
        "firewall": "pass",
        "timings_seconds": {"schema_and_integrity": schema_secs},
        "verified_at": now_iso(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="CPH.4 verify restored DB")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--skip-smoke", action="store_true")
    args = parser.parse_args()
    try:
        result = asyncio.run(main_async(args))
        print(json.dumps(result, indent=2, default=str))
        return 0
    except Cph4Error as exc:
        print(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
