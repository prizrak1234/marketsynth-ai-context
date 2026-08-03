"""CPH.5 — pilot/production configuration validation (fail-fast, no silent repair)."""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse

from app.core.config import Settings


@dataclass
class ConfigIssue:
    code: str
    message: str
    severity: str  # "error" | "warning"


@dataclass
class ConfigValidationResult:
    ok: bool
    issues: list[ConfigIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ConfigIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ConfigIssue]:
        return [i for i in self.issues if i.severity == "warning"]


_DEFAULT_TEST_DB_MARKERS = (
    "botfazer:botfazer@",
    "postgres:postgres@",
    "password@",
    ":password@",
)


def _is_pilot_like(settings: Settings) -> bool:
    return settings.app_env in {"pilot", "staging", "production"}


def validate_pilot_configuration(settings: Settings) -> ConfigValidationResult:
    """Validate settings for the active environment.

    Development: warnings preferred.
    Pilot/staging/production: errors refuse startup.
    """
    issues: list[ConfigIssue] = []
    pilot_like = _is_pilot_like(settings)

    def err(code: str, message: str) -> None:
        issues.append(ConfigIssue(code=code, message=message, severity="error"))

    def warn(code: str, message: str) -> None:
        issues.append(ConfigIssue(code=code, message=message, severity="warning"))

    db = (settings.database_url or "").strip()
    if not db:
        err("database_url_missing", "DATABASE_URL is required")
    else:
        normalized = db.replace("postgresql+asyncpg://", "postgresql://", 1)
        if normalized.startswith("sqlite"):
            # Dev/test SQLite is allowed outside pilot-like modes.
            if pilot_like:
                err("database_url_invalid", "SQLite is not allowed for pilot/staging/production")
        else:
            try:
                parsed = urlparse(normalized)
                if not parsed.hostname or not parsed.path or parsed.path == "/":
                    err(
                        "database_url_invalid",
                        "DATABASE_URL must include host and database name",
                    )
            except Exception:  # noqa: BLE001
                err("database_url_invalid", "DATABASE_URL could not be parsed")


    if settings.debug and pilot_like:
        err("debug_enabled_in_pilot", "DEBUG must be false in pilot/staging/production")

    if settings.app_env not in {"development", "test", "pilot", "staging", "production"}:
        err("unknown_environment", f"Unsupported APP_ENV={settings.app_env}")

    origins = list(settings.browser_allowed_origins or [])
    if "*" in origins:
        err("wildcard_cors", "Wildcard CORS origin is forbidden with credentialed sessions")
    if pilot_like and not origins:
        err("pilot_origins_missing", "BROWSER_ALLOWED_ORIGINS must list the pilot frontend origin(s)")

    public_https = any(o.startswith("https://") for o in origins)
    if public_https and not settings.browser_session_cookie_secure:
        msg = "BROWSER_SESSION_COOKIE_SECURE must be true when origins use HTTPS"
        if pilot_like:
            err("insecure_cookie_under_https", msg)
        else:
            warn("insecure_cookie_under_https", msg)

    if (
        settings.browser_session_cookie_samesite == "none"
        and not settings.browser_session_cookie_secure
    ):
        err(
            "samesite_none_requires_secure",
            "SameSite=None requires Secure cookies",
        )

    if settings.browser_csrf_allow_missing_origin and pilot_like:
        err(
            "csrf_missing_origin_allowed",
            "BROWSER_CSRF_ALLOW_MISSING_ORIGIN must be false in pilot/staging/production",
        )

    if pilot_like and not settings.alembic_revision_check_enabled:
        err("revision_check_disabled", "ALEMBIC_REVISION_CHECK_ENABLED must be true for pilot")
    if pilot_like and not settings.alembic_revision_fail_fast:
        err(
            "revision_fail_fast_disabled",
            "ALEMBIC_REVISION_FAIL_FAST must be true for pilot/staging/production",
        )

    dangerous_flags = [
        ("tools_provider_enabled", settings.tools_provider_enabled),
        ("publication_worker_enabled", settings.publication_worker_enabled),
        ("telegram_publication_enabled", getattr(settings, "telegram_publication_enabled", False)),
        ("media_generation_enabled", settings.media_generation_enabled),
        ("graph_handoff_execute_child", settings.graph_handoff_execute_child),
        ("event_outbox_dispatcher_enabled", settings.event_outbox_dispatcher_enabled),
        ("demo_flow_endpoints_enabled", settings.demo_flow_endpoints_enabled),
    ]
    for name, enabled in dangerous_flags:
        if enabled and settings.app_env in {"pilot", "production"}:
            err(
                "execution_feature_enabled",
                f"{name} must be false for controlled pilot/production unless explicitly approved",
            )
        elif enabled and settings.app_env == "staging":
            warn(
                "execution_feature_enabled",
                f"{name} is enabled in staging — confirm this is intentional",
            )

    lowered = db.lower()
    if any(m in lowered for m in _DEFAULT_TEST_DB_MARKERS):
        if settings.is_production:
            err(
                "default_test_credentials",
                "Default/local database credentials detected in production",
            )
        elif settings.app_env == "pilot":
            warn(
                "default_test_credentials",
                "Local-style DB credentials in pilot — acceptable only for isolated local pilot",
            )

    if pilot_like:
        for o in origins:
            if "example.com" in o or "change-me" in o.lower():
                err("invalid_public_url", f"Placeholder origin not allowed: {o}")

    errors = [i for i in issues if i.severity == "error"]
    return ConfigValidationResult(ok=len(errors) == 0, issues=issues)


def assert_pilot_configuration(settings: Settings) -> ConfigValidationResult:
    """Raise RuntimeError on blocking errors for pilot-like envs."""
    result = validate_pilot_configuration(settings)
    if result.errors and _is_pilot_like(settings):
        codes = ", ".join(i.code for i in result.errors)
        raise RuntimeError(f"pilot_config_invalid: {codes}")
    return result
