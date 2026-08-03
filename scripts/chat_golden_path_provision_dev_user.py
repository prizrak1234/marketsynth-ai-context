#!/usr/bin/env python3
"""Provision idempotent chat golden path dev/test user (development/test only).

Wraps cph3_provision_pilot_user with CHAT_GOLDEN_PATH_* env vars.
Never prints password. Production DB names are refused by default.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Chat golden path dev user provision")
    parser.add_argument("--email", default=os.environ.get("CHAT_GOLDEN_PATH_E2E_EMAIL"))
    parser.add_argument("--password", default=os.environ.get("CHAT_GOLDEN_PATH_E2E_PASSWORD"))
    parser.add_argument("--update", action="store_true", help="Update password if user exists")
    parser.add_argument(
        "--require-db",
        default=os.environ.get("CHAT_GOLDEN_PATH_REQUIRE_DB", "botfazer"),
    )
    args = parser.parse_args()

    if not args.email or not args.password:
        print(
            "CHAT_GOLDEN_PATH_E2E_EMAIL and CHAT_GOLDEN_PATH_E2E_PASSWORD required",
            file=sys.stderr,
        )
        raise SystemExit(4)

    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "cph3_provision_pilot_user.py"
    env = os.environ.copy()
    env["CPH3_PILOT_PASSWORD"] = args.password

    cmd = [
        sys.executable,
        str(script),
        "--email",
        args.email.strip().lower(),
        "--require-db",
        args.require_db,
        "--allow-owner-env-password",
    ]
    if args.update:
        cmd.append("--update")

    result = subprocess.run(cmd, env=env, cwd=root)
    if result.returncode != 0:
        raise SystemExit(result.returncode)

    e2e_env = root / "web" / ".env.local.chat-golden-path"
    e2e_env.write_text(
        "\n".join(
            [
                f"CPH3_E2E_EMAIL={args.email.strip().lower()}",
                "CPH3_E2E_PASSWORD=(set via CHAT_GOLDEN_PATH_E2E_PASSWORD — not written to disk)",
                f"CHAT_GOLDEN_PATH_E2E_EMAIL={args.email.strip().lower()}",
                "CPH2_BACKEND_URL=http://localhost:8000",
                "CPH2_FRONTEND_URL=http://localhost:3000",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"ok e2e_env_template={e2e_env}")
    print("export CPH3_E2E_EMAIL and CPH3_E2E_PASSWORD before Playwright")


if __name__ == "__main__":
    main()
