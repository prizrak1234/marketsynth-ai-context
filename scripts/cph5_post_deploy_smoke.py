"""CPH.5 — post-deploy authenticated smoke against a running (or TestClient) API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


ORIGIN = os.environ.get("CPH5_ORIGIN", "http://localhost:3000")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_smoke(base_url: str, email: str, password: str) -> dict:
    t0 = time.perf_counter()
    correlation_ids: list[str] = []
    with httpx.Client(base_url=base_url, timeout=30.0, follow_redirects=True) as client:
        live = client.get("/health/live")
        correlation_ids.append(live.headers.get("X-Request-ID", ""))
        if live.status_code != 200:
            raise SystemExit(f"error=authenticated_smoke_failed detail=live_{live.status_code}")

        ready = client.get("/health/ready")
        correlation_ids.append(ready.headers.get("X-Request-ID", ""))
        if ready.status_code != 200 or not ready.json().get("ready"):
            raise SystemExit(
                f"error=authenticated_smoke_failed detail=ready_{ready.status_code}"
            )

        login = client.post(
            "/auth/login",
            json={"email": email, "password": password},
            headers={"Origin": ORIGIN},
        )
        correlation_ids.append(login.headers.get("X-Request-ID", ""))
        if login.status_code != 200:
            raise SystemExit(f"error=authenticated_smoke_failed detail=login_{login.status_code}")

        me = client.get("/auth/me")
        if me.status_code != 200:
            raise SystemExit("error=authenticated_smoke_failed detail=me")

        projects = client.get("/projects")
        if projects.status_code != 200:
            raise SystemExit("error=authenticated_smoke_failed detail=projects")
        items = projects.json()
        if not items:
            raise SystemExit("error=authenticated_smoke_failed detail=no_projects")
        project_id = items[0]["id"]
        project = client.get(f"/projects/{project_id}")
        if project.status_code != 200:
            raise SystemExit("error=authenticated_smoke_failed detail=project_get")

        mp = client.get(f"/projects/{project_id}/marketing-plans")
        mp_statuses = []
        if mp.status_code == 200:
            body = mp.json()
            plans = body if isinstance(body, list) else body.get("items", [])
            mp_statuses = [p.get("status") for p in plans if isinstance(p, dict)]
            if any(s not in (None, "draft") for s in mp_statuses):
                raise SystemExit(f"error=lineage_integrity_failed detail={mp_statuses}")

        label = f"CPH5-SMOKE-{_now().replace(':', '')}"
        created = client.post(
            "/projects",
            json={"name": label, "description": "cph5 post-deploy smoke"},
            headers={"Origin": ORIGIN},
        )
        if created.status_code not in (200, 201):
            raise SystemExit(f"error=authenticated_smoke_failed detail=write_{created.status_code}")

        logout = client.post("/auth/logout", headers={"Origin": ORIGIN})
        if logout.status_code not in (200, 204):
            raise SystemExit(f"error=authenticated_smoke_failed detail=logout_{logout.status_code}")
        after = client.get("/auth/me")
        if after.status_code == 200:
            raise SystemExit("error=authenticated_smoke_failed detail=logout_did_not_invalidate")

        ready_after = client.get("/health/ready").json()

    return {
        "ok": True,
        "base_url_host": urlparse(base_url).hostname,
        "project_id_seen": project_id,
        "marketing_plan_statuses": mp_statuses,
        "write_label": label,
        "correlation_ids": [c for c in correlation_ids if c],
        "ready_revision": ready_after.get("actual_revisions"),
        "database_name": ready_after.get("database_name"),
        "duration_seconds": round(time.perf_counter() - t0, 3),
        "completed_at": _now(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="CPH.5 post-deploy smoke")
    parser.add_argument("--base-url", default=os.environ.get("CPH5_API_BASE", "http://127.0.0.1:8000"))
    parser.add_argument("--email", default=os.environ.get("CPH3_E2E_EMAIL") or os.environ.get("CPH5_SMOKE_EMAIL"))
    parser.add_argument(
        "--password",
        default=os.environ.get("CPH3_E2E_PASSWORD") or os.environ.get("CPH5_SMOKE_PASSWORD"),
    )
    args = parser.parse_args()
    if not args.email or not args.password:
        print("error=authenticated_smoke_failed detail=missing_credentials")
        return 2
    result = run_smoke(args.base_url.rstrip("/"), args.email, args.password)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
