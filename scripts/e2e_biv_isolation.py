"""Provision and cleanup isolated BIV Playwright E2E users/projects."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

BACKEND = os.environ.get("CPH2_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
E2E_DOMAIN = os.environ.get("BIV_E2E_EMAIL_DOMAIN", "marketsynth.test")
MARKER_PREFIX = "E2E-BIV-"


class HttpClient:
    def __init__(self) -> None:
        self._jar = CookieJar()
        self._opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self._jar))

    def request(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
    ) -> tuple[int, dict | list | str]:
        data = None
        headers = {"Content-Type": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(f"{BACKEND}{path}", data=data, headers=headers, method=method)
        try:
            with self._opener.open(req, timeout=60) as resp:
                body = resp.read().decode("utf-8")
                if not body:
                    return resp.status, {}
                parsed = json.loads(body)
                return resp.status, parsed
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8")
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = {"detail": raw}
            return exc.code, parsed


def build_credentials(run_id: str) -> tuple[str, str]:
    safe_run_id = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in run_id)
    email = f"biv-e2e-{safe_run_id}@{E2E_DOMAIN}"
    password = f"BivE2E_{safe_run_id}!26"
    return email, password


def is_test_project(name: str, description: str | None, run_id: str | None) -> bool:
    if not name.startswith(MARKER_PREFIX):
        return False
    if run_id and f"run={run_id}" not in (description or ""):
        return False
    return True


def provision(run_id: str) -> dict:
    email, password = build_credentials(run_id)
    client = HttpClient()
    register_status, register_body = client.request(
        "POST",
        "/auth/register",
        {
            "email": email,
            "password": password,
            "password_confirmation": password,
            "display_name": f"BIV E2E {run_id}",
            "accepted_pilot_notice": True,
        },
    )
    login_status, login_body = client.request(
        "POST",
        "/auth/login",
        {"email": email, "password": password},
    )
    if login_status != 200:
        raise RuntimeError(json.dumps({"register": register_body, "login": login_body}))

    projects_before_status, projects_before = client.request("GET", "/projects")
    projects_before_count = len(projects_before) if isinstance(projects_before, list) else 0

    return {
        "action": "provision",
        "run_id": run_id,
        "email": email,
        "password": password,
        "register_status": register_status,
        "login_status": login_status,
        "projects_before": projects_before_count,
        "projects_created": 0,
        "projects_archived": 0,
        "projects_deleted": 0,
        "projects_skipped": 0,
    }


def cleanup(run_id: str, *, dry_run: bool) -> dict:
    email, password = build_credentials(run_id)
    client = HttpClient()
    login_status, login_body = client.request(
        "POST",
        "/auth/login",
        {"email": email, "password": password},
    )
    if login_status != 200:
        return {
            "action": "cleanup",
            "run_id": run_id,
            "email": email,
            "dry_run": dry_run,
            "login_status": login_status,
            "projects_before": 0,
            "projects_created": 0,
            "projects_archived": 0,
            "projects_deleted": 0,
            "projects_skipped": 0,
            "note": "user_not_found_or_login_failed",
        }

    list_status, projects = client.request("GET", "/projects")
    if list_status != 200 or not isinstance(projects, list):
        raise RuntimeError(f"Failed to list projects: {list_status} {projects}")

    deleted = 0
    skipped = 0
    for project in projects:
        name = str(project.get("name", ""))
        description = project.get("description")
        if not is_test_project(name, description, run_id):
            skipped += 1
            continue
        project_id = project["id"]
        if dry_run:
            deleted += 1
            continue
        delete_status, _ = client.request("DELETE", f"/projects/{project_id}")
        if delete_status == 204:
            deleted += 1
        else:
            skipped += 1

    list_status_after, projects_after = client.request("GET", "/projects")
    projects_after_count = len(projects_after) if isinstance(projects_after, list) else 0

    fixture_deleted = 0
    if not dry_run:
        try:
            import asyncio

            from app.business_idea_validation.e2e_deterministic_fixture import E2eDeterministicFixtureService
            from app.core.config import get_settings
            from app.db.session import get_session_factory

            async def _clear_fixture() -> int:
                factory = get_session_factory()
                async with factory() as session:
                    svc = E2eDeterministicFixtureService(session, get_settings())
                    deleted = await svc.clear_for_e2e_run(run_id)
                    await session.commit()
                    return deleted

            fixture_deleted = asyncio.run(_clear_fixture())
        except Exception:
            fixture_deleted = 0

    return {
        "action": "cleanup",
        "run_id": run_id,
        "email": email,
        "dry_run": dry_run,
        "projects_before": len(projects),
        "projects_created": 0,
        "projects_archived": 0,
        "projects_deleted": deleted,
        "projects_skipped": skipped,
        "projects_after": projects_after_count,
        "fixtures_deleted": fixture_deleted,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="BIV E2E isolation helper")
    parser.add_argument("command", choices=["provision", "cleanup"])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.command == "provision":
        result = provision(args.run_id)
    else:
        result = cleanup(args.run_id, dry_run=args.dry_run)

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
