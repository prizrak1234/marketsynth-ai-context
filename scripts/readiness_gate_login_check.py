"""Controlled Pilot Readiness Gate — browser login characterization (Playwright).

Canonical host: http://localhost:3000
Also characterizes http://127.0.0.1:3000 (same cookie-aligned API host rewrite).
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    from playwright.sync_api import sync_playwright

    email = os.environ.get("CPH3_E2E_EMAIL") or os.environ.get("CPH5_SMOKE_EMAIL")
    password = os.environ.get("CPH3_E2E_PASSWORD") or os.environ.get("CPH5_SMOKE_PASSWORD")
    if not email or not password:
        print("error=missing_pilot_credentials")
        return 2

    results = []
    hosts = [
        ("canonical", "http://localhost:3000"),
        ("loopback_alias", "http://127.0.0.1:3000"),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for label, origin in hosts:
            entry: dict = {"label": label, "origin": origin}
            context = browser.new_context(base_url=origin)
            page = context.new_page()
            try:
                page.goto(f"{origin}/login?next=%2Fworkspace", wait_until="networkidle")
                page.wait_for_timeout(1200)
                err_before = page.locator('[data-testid="login-error"]').count()
                cred_text = page.get_by_text("Неверный логин или пароль").count()
                entry["error_before_submit"] = err_before
                entry["invalid_creds_text_before"] = cred_text

                # invalid submit
                page.get_by_label("Email").fill("nobody@marketsynth.local")
                page.get_by_label("Пароль").fill("wrong-password-xx")
                page.get_by_test_id("login-submit").click()
                page.wait_for_timeout(1500)
                entry["error_after_invalid"] = page.locator('[data-testid="login-error"]').count()
                kind = None
                if entry["error_after_invalid"]:
                    kind = page.locator('[data-testid="login-error"]').get_attribute(
                        "data-error-kind"
                    )
                entry["invalid_error_kind"] = kind

                # valid login
                page.goto(f"{origin}/login", wait_until="networkidle")
                page.wait_for_timeout(800)
                page.get_by_label("Email").fill(email)
                page.get_by_label("Пароль").fill(password)
                cookies_before = context.cookies()
                page.get_by_test_id("login-submit").click()
                page.wait_for_url("**/workspace**", timeout=60_000)
                cookies_after = context.cookies()
                session_cookies = [
                    c
                    for c in cookies_after
                    if c.get("name") == "ms_pilot_session"
                ]
                entry["login_ok"] = "/workspace" in page.url
                entry["session_cookie_present"] = len(session_cookies) > 0
                if session_cookies:
                    sc = session_cookies[0]
                    entry["cookie"] = {
                        "httpOnly": sc.get("httpOnly"),
                        "secure": sc.get("secure"),
                        "sameSite": sc.get("sameSite"),
                        "path": sc.get("path"),
                        "domain": sc.get("domain"),
                    }

                page.reload(wait_until="networkidle")
                page.wait_for_timeout(1000)
                entry["session_survives_refresh"] = page.locator(
                    '[data-testid="logout-button"]'
                ).count() > 0 or ("/workspace" in page.url and "/login" not in page.url)

                # logout
                if page.locator('[data-testid="logout-button"]').count():
                    page.get_by_test_id("logout-button").click()
                else:
                    # fallback: call logout via UI if different selector
                    page.goto(f"{origin}/workspace")
                page.wait_for_timeout(1500)
                page.goto(f"{origin}/workspace", wait_until="networkidle")
                page.wait_for_timeout(1500)
                entry["workspace_requires_login_after_logout"] = "/login" in page.url
                entry["ok"] = (
                    entry["error_before_submit"] == 0
                    and entry["invalid_creds_text_before"] == 0
                    and entry["error_after_invalid"] > 0
                    and entry["invalid_error_kind"] == "invalid_credentials"
                    and entry["login_ok"] is True
                    and entry["session_cookie_present"] is True
                    and entry["session_survives_refresh"] is True
                    and entry["workspace_requires_login_after_logout"] is True
                )
            except Exception as exc:  # noqa: BLE001
                entry["ok"] = False
                entry["error"] = f"{type(exc).__name__}:{str(exc)[:240]}"
            finally:
                context.close()
            results.append(entry)
        browser.close()

    out = {
        "completed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "canonical_host": "http://localhost:3000",
        "results": results,
        "canonical_pass": next((r["ok"] for r in results if r["label"] == "canonical"), False),
        "alias_pass": next((r["ok"] for r in results if r["label"] == "loopback_alias"), False),
    }
    print(json.dumps(out, indent=2))
    path = Path.home() / "botfazer_backups" / "cph4" / "readiness_gate_login_check.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("wrote=", path)
    return 0 if out["canonical_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
