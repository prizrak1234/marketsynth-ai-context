#!/usr/bin/env python
"""Owner-only Higgsfield MCP sandbox handshake (CONN-HF-01.1).

Performs initialize + tools/list and writes sanitized artifacts under
packages/connectors/higgsfield/sandbox/.

Requires HIGGSFIELD_MCP_ENABLED=true and HIGGSFIELD_OAUTH_ACCESS_TOKEN in env.
Does not print access tokens.
"""

from __future__ import annotations

import asyncio
import json

from app.connectors.higgsfield.sandbox.handshake import HiggsfieldSandboxHandshake
from app.core.config import get_settings


async def _main() -> int:
    settings = get_settings()
    if not settings.higgsfield_mcp_enabled:
        print(json.dumps({"error": "higgsfield_mcp_disabled"}))
        return 1
    if not settings.higgsfield_mcp_configured:
        print(json.dumps({"error": "higgsfield_oauth_token_missing"}))
        return 1

    handshake = HiggsfieldSandboxHandshake(settings)
    try:
        result = await handshake.run()
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": type(exc).__name__, "code": str(exc)}))
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
