"""CPH.5 — validate pilot configuration (no secrets printed)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.domain.pilot_config_validation import validate_pilot_configuration


def main() -> int:
    parser = argparse.ArgumentParser(description="CPH.5 config validation")
    parser.add_argument("--require-pilot-like", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    print("app_env=", settings.app_env)
    print("debug=", settings.debug)
    print("cookie_secure=", settings.browser_session_cookie_secure)
    print("origins=", settings.browser_allowed_origins)
    result = validate_pilot_configuration(settings)
    payload = {
        "ok": result.ok,
        "errors": [{"code": i.code, "message": i.message} for i in result.errors],
        "warnings": [{"code": i.code, "message": i.message} for i in result.warnings],
    }
    print(json.dumps(payload, indent=2))
    if args.require_pilot_like and settings.app_env not in {"pilot", "staging", "production"}:
        print("error=not_pilot_like")
        return 3
    return 0 if result.ok or settings.app_env in {"development", "test"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
