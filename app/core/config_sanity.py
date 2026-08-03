"""Runtime configuration sanity checks (Phase 3.16)."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings


@dataclass(frozen=True)
class ConfigWarning:
    code: str
    message: str

    def compact(self) -> str:
        return self.code


def validate_runtime_config(
    settings: Settings,
    *,
    redis_available: bool | None = None,
    database_available: bool | None = None,
) -> list[ConfigWarning]:
    warnings: list[ConfigWarning] = []

    if settings.agent_execution_force_classic and settings.agent_execution_engine == "langgraph":
        warnings.append(
            ConfigWarning(
                code="force_classic_overrides_langgraph_engine",
                message=(
                    "AGENT_EXECUTION_FORCE_CLASSIC=true while "
                    "AGENT_EXECUTION_ENGINE=langgraph; all runs use classic."
                ),
            ),
        )

    if not settings.agent_execution_langgraph_enabled:
        warnings.append(
            ConfigWarning(
                code="langgraph_globally_disabled",
                message=(
                    "AGENT_EXECUTION_LANGGRAPH_ENABLED=false; "
                    "project.config.execution_engine=langgraph falls back to classic."
                ),
            ),
        )

    if settings.graph_handoff_scheduler_enabled and redis_available is False:
        warnings.append(
            ConfigWarning(
                code="handoff_scheduler_without_redis",
                message="GRAPH_HANDOFF_SCHEDULER_ENABLED=true but Redis is unavailable.",
            ),
        )

    if settings.event_outbox_dispatcher_enabled:
        timeout = settings.event_outbox_webhook_timeout_seconds
        if timeout < 1 or timeout > 120:
            warnings.append(
                ConfigWarning(
                    code="outbox_webhook_timeout_out_of_range",
                    message=f"EVENT_OUTBOX_WEBHOOK_TIMEOUT_SECONDS={timeout} (expected 1–120).",
                ),
            )

    if settings.event_outbox_dispatch_max_attempts < 1:
        warnings.append(
            ConfigWarning(
                code="outbox_dispatch_max_attempts_invalid",
                message=(
                    f"EVENT_OUTBOX_DISPATCH_MAX_ATTEMPTS="
                    f"{settings.event_outbox_dispatch_max_attempts} (must be >= 1)."
                ),
            ),
        )

    if settings.graph_handoff_max_attempts < 1:
        warnings.append(
            ConfigWarning(
                code="handoff_max_attempts_invalid",
                message=(
                    f"GRAPH_HANDOFF_MAX_ATTEMPTS={settings.graph_handoff_max_attempts} "
                    "(must be >= 1)."
                ),
            ),
        )

    if settings.publication_worker_enabled and database_available is False:
        warnings.append(
            ConfigWarning(
                code="publication_worker_enabled_without_database",
                message=(
                    "PUBLICATION_WORKER_ENABLED=true but database is unavailable; "
                    "worker cannot drain jobs."
                ),
            ),
        )

    if settings.publication_job_max_attempts < 1:
        warnings.append(
            ConfigWarning(
                code="publication_job_max_attempts_lt_1",
                message=(
                    f"PUBLICATION_JOB_MAX_ATTEMPTS={settings.publication_job_max_attempts} "
                    "(must be >= 1)."
                ),
            ),
        )

    timeout = settings.publication_delivery_timeout_seconds
    if timeout < 1 or timeout > 120:
        warnings.append(
            ConfigWarning(
                code="publication_delivery_timeout_invalid",
                message=(
                    f"PUBLICATION_DELIVERY_TIMEOUT_SECONDS={timeout} "
                    "(expected 1–120)."
                ),
            ),
        )

    if settings.publication_worker_interval_seconds < 5:
        warnings.append(
            ConfigWarning(
                code="publication_worker_interval_too_low",
                message=(
                    f"PUBLICATION_WORKER_INTERVAL_SECONDS="
                    f"{settings.publication_worker_interval_seconds} "
                    "(expected >= 5)."
                ),
            ),
        )

    if settings.telegram_publication_enabled and (
        settings.telegram_publication_bot_token is None
        or not settings.telegram_publication_bot_token.get_secret_value().strip()
    ):
        warnings.append(
            ConfigWarning(
                code="telegram_publication_enabled_without_token",
                message=(
                    "TELEGRAM_PUBLICATION_ENABLED=true but "
                    "TELEGRAM_PUBLICATION_BOT_TOKEN is missing or empty."
                ),
            ),
        )

    telegram_timeout = settings.telegram_publication_timeout_seconds
    if telegram_timeout <= 0 or telegram_timeout > 120:
        warnings.append(
            ConfigWarning(
                code="telegram_publication_timeout_invalid",
                message=(
                    f"TELEGRAM_PUBLICATION_TIMEOUT_SECONDS={telegram_timeout} "
                    "(expected 1–120)."
                ),
            ),
        )

    if settings.telegram_publication_enabled and not settings.publication_worker_enabled:
        warnings.append(
            ConfigWarning(
                code="telegram_publication_enabled_without_worker",
                message=(
                    "TELEGRAM_PUBLICATION_ENABLED=true while "
                    "PUBLICATION_WORKER_ENABLED=false; jobs will not be drained."
                ),
            ),
        )

    return warnings
