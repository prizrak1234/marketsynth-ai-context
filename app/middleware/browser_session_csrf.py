"""Cookie CSRF guard — Origin/Referer check when session cookie authenticates mutations."""

from __future__ import annotations

from collections.abc import Callable
from typing import Awaitable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)

_UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


class BrowserSessionCsrfMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        settings = get_settings()
        cookie_name = settings.browser_session_cookie_name
        if request.method in _UNSAFE and request.cookies.get(cookie_name):
            # Login sets the cookie on the response, not the request — skip if absent.
            # Refresh/logout with existing cookie must pass Origin.
            path = request.url.path
            invite_accept = path.startswith("/auth/invitations/") and path.endswith(
                "/accept"
            )
            password_reset = path.startswith("/auth/password-reset/")
            # Unauthenticated signup/login/reset: cookie may be stale; Origin still
            # applied by CORS. Skip cookie-CSRF block for these endpoints.
            if (
                path not in ("/auth/login", "/auth/register", "/auth/password-reset/request")
                and not invite_accept
                and not password_reset
            ):
                if not _origin_allowed(request, settings.browser_allowed_origins):
                    if settings.browser_csrf_allow_missing_origin and settings.is_development:
                        pass
                    else:
                        log.info("csrf_failed", path=path)
                        return JSONResponse(
                            status_code=403,
                            content={"detail": "csrf_failed"},
                        )
        return await call_next(request)


def _origin_allowed(request: Request, allowed: list[str]) -> bool:
    origin = request.headers.get("origin")
    if origin and origin in allowed:
        return True
    referer = request.headers.get("referer")
    if referer:
        for base in allowed:
            if referer.startswith(base.rstrip("/") + "/") or referer.rstrip("/") == base.rstrip(
                "/"
            ):
                return True
    # Same-site cross-port browser fetches (e.g. :3000 → :8000) may omit Origin.
    sec_fetch_site = (request.headers.get("sec-fetch-site") or "").lower()
    if sec_fetch_site in {"same-site", "same-origin"}:
        return True
    return False
