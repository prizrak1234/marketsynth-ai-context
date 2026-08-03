"""Provision (or verify) the BIV Playwright dev user against a running backend."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_EMAIL = "biv-e2e-dev@marketsynth.test"
DEFAULT_PASSWORD = "BivE2EDev2026!"
BACKEND = os.environ.get("CPH2_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")


def _post(path: str, payload: dict) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BACKEND}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"detail": raw}
        return exc.code, parsed


def main() -> int:
    email = os.environ.get("CPH3_E2E_EMAIL", DEFAULT_EMAIL)
    password = os.environ.get("CPH3_E2E_PASSWORD", DEFAULT_PASSWORD)

    status, body = _post(
        "/auth/register",
        {
            "email": email,
            "password": password,
            "password_confirmation": password,
            "display_name": "BIV E2E Dev",
            "accepted_pilot_notice": True,
        },
    )
    if status in {201, 409}:
        print(json.dumps({"email": email, "status": status, "registered": status == 201}))
        return 0

    login_status, login_body = _post(
        "/auth/login",
        {"email": email, "password": password},
    )
    if login_status == 200:
        print(json.dumps({"email": email, "status": login_status, "login": "ok"}))
        return 0

    print(json.dumps({"register": body, "login": login_body}), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
