"""FastAPI application entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, me, memory, projects, tasks, users, webhooks
from app.api.routes import agent_chat as agent_chat_routes
from app.api.routes import chat as chat_routes
from app.api.routes import agent_runs as agent_runs_routes
from app.api.routes import agents as agents_routes
from app.api.routes import auth as auth_routes
from app.api.routes import content_assets as content_assets_routes
from app.api.routes import content_director as content_director_routes
from app.api.routes import visual_director as visual_director_routes
from app.api.routes import project_command_center as project_command_center_routes
from app.api.routes import product_skills as product_skills_routes
from app.api.routes import media_assets as media_assets_routes
from app.api.routes import media_briefs as media_briefs_routes
from app.api.routes import media_renderer as media_renderer_routes
from app.api.routes import media_generation as media_generation_routes
from app.api.routes import publication_packages as publication_packages_routes
from app.api.routes import llm_requests as llm_requests_routes
from app.api.routes import marketing_briefs as marketing_briefs_routes
from app.api.routes import marketing_plan_execution_runs as marketing_plan_execution_runs_routes
from app.api.routes import marketing_specialist_outputs as marketing_specialist_outputs_routes
from app.api.routes import marketing_plans as marketing_plans_routes
from app.api.routes import marketing_scenarios as marketing_scenarios_routes
from app.api.routes import marketing_campaigns as marketing_campaigns_routes
from app.api.routes import marketing_funnels as marketing_funnels_routes
from app.api.routes import project_briefs as project_briefs_routes
from app.api.routes import investigations as investigations_routes
from app.api.routes import sources as sources_routes
from app.api.routes import evidence as evidence_routes
from app.api.routes import business_verdicts as business_verdicts_routes
from app.api.routes import marketing_strategies as marketing_strategies_routes
from app.api.routes import implementation_plans as implementation_plans_routes
from app.api.routes import publishing as publishing_routes
from app.api.routes import publishing_foundation as publishing_foundation_routes
from app.api.routes import demo_flow as demo_flow_routes
from app.api.routes import marketing_skills as marketing_skills_routes
from app.api.routes import marketing_tools as marketing_tools_routes
from app.api.routes import business_campaigns as business_campaigns_routes
from app.api.routes import business_operator as business_operator_routes
from app.api.routes import scenario_wizard_runs as scenario_wizard_runs_routes
from app.api.routes import user_requests as user_requests_routes
from app.api.routes import knowledge_foundation as knowledge_foundation_routes
from app.api.routes import knowledge_governance as knowledge_governance_routes
from app.api.routes import specialist_skills as specialist_skills_routes
from app.api.routes import signed_media as signed_media_routes
from app.api.routes import video_smoke_preview as video_smoke_preview_routes
from app.api.routes import video_smoke_execute as video_smoke_execute_routes
from app.api.routes import video_studio as video_studio_routes
from app.api.routes import video_clips as video_clips_routes
from app.api.routes import commercial_research as commercial_research_routes
from app.api.routes import analysis_contexts as analysis_contexts_routes
from app.api.routes import business_idea_validation as business_idea_validation_routes
from app.api.routes import offers as offers_routes
from app.api.routes import launch_pack as launch_pack_routes
from app.api.routes import content_factory as content_factory_routes
from app.api.routes import generated_visual_assets as generated_visual_assets_routes
from app.api.routes import reference_visuals as reference_visuals_routes
from app.api.routes import identity_generation as identity_generation_routes
from app.core.api_errors import RequestIdMiddleware, register_api_exception_handlers
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.redis import close_redis, init_redis
from app.db.session import close_db, init_db
from app.middleware.telegram import TelegramWebhookMiddleware
from app.middleware.browser_session_csrf import BrowserSessionCsrfMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.workers.biv_run_dispatcher import get_biv_run_dispatcher
from app.workers.handoff_scheduler import get_handoff_scheduler
from app.workers.outbox_dispatcher_scheduler import get_outbox_dispatcher_scheduler
from app.workers.publication_worker import get_publication_worker_scheduler

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings)
    from app.domain.pilot_config_validation import assert_pilot_configuration

    cfg = assert_pilot_configuration(settings)
    for issue in cfg.warnings:
        log.warning("pilot_config_warning", code=issue.code, detail=issue.message)
    await init_db(settings)
    await init_redis(settings)
    if settings.alembic_revision_check_enabled:
        from app.db.session import get_engine
        from app.services.alembic_revision_startup import log_revision_diagnostic

        try:
            await log_revision_diagnostic(get_engine(), settings)
        except RuntimeError:
            raise
        except Exception as exc:  # noqa: BLE001 Р Р†Р вЂљРІР‚Сњ diagnostic must not crash soft-dev unexpectedly
            if settings.is_pilot_like:
                raise RuntimeError(f"alembic_revision_check_failed: {type(exc).__name__}") from exc
            log.warning(
                "alembic_revision_check_failed",
                error=str(exc)[:240],
                auto_stamp_allowed=False,
                auto_migrate_allowed=False,
            )
    from app.db.session import get_engine
    from app.services.analysis_context_subsystem_readiness import (
        inspect_analysis_context_subsystem,
    )

    try:
        ac_ready = await inspect_analysis_context_subsystem(get_engine())
        if ac_ready.ready:
            log.info("analysis_context_subsystem_ready", **ac_ready.as_dict())
        else:
            log.warning(
                "analysis_context_subsystem_not_ready",
                repair_hint="uv run python scripts/repair_product_01_3a_dev_db.py --fresh",
                **ac_ready.as_dict(),
            )
    except Exception as exc:  # noqa: BLE001
        log.warning("analysis_context_subsystem_check_failed", error=type(exc).__name__)
    # Pilot identity check (optional)
    if settings.pilot_require_database_name:
        from urllib.parse import urlparse

        name = (urlparse(
            settings.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        ).path or "").lstrip("/")
        if name != settings.pilot_require_database_name:
            raise RuntimeError(
                f"backup_source_database_mismatch: expected={settings.pilot_require_database_name} got={name}"
            )
    handoff_scheduler = get_handoff_scheduler()
    outbox_scheduler = get_outbox_dispatcher_scheduler()
    publication_scheduler = get_publication_worker_scheduler()
    await handoff_scheduler.start()
    await outbox_scheduler.start()
    await publication_scheduler.start()
    if settings.biv_run_dispatcher_enabled:
        recovery = await get_biv_run_dispatcher().recover_on_startup()
        log.info("biv_run_dispatcher_startup", **recovery)
    log.info("application_starting", **{k: str(v) for k, v in settings.safe_dict().items()})
    yield
    log.info("application_shutdown_begin")
    await publication_scheduler.stop()
    await outbox_scheduler.stop()
    await handoff_scheduler.stop()
    await close_redis()
    await close_db()
    log.info("application_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug and settings.is_development,
        lifespan=lifespan,
        docs_url="/docs" if settings.is_development else None,
        redoc_url=None,
    )
    # Starlette: last added = outermost. RequestId should wrap all responses.
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(BrowserSessionCsrfMiddleware)
    application.add_middleware(TelegramWebhookMiddleware)
    application.add_middleware(RequestIdMiddleware)
    register_api_exception_handlers(application)
    if settings.cors_enabled and settings.browser_allowed_origins:
        if "*" in settings.browser_allowed_origins:
            raise RuntimeError("wildcard_cors: refusing to enable CORS with credentials")
        application.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.browser_allowed_origins),
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=[
                "Authorization",
                "Content-Type",
                "Idempotency-Key",
                "X-Request-ID",
                "X-Request-Id",
                "X-Correlation-ID",
            ],
            expose_headers=["X-Request-ID", "X-Correlation-ID"],
        )
    application.include_router(health.router)
    application.include_router(webhooks.router)
    application.include_router(auth_routes.router)
    application.include_router(me.router)
    application.include_router(users.router)
    application.include_router(projects.router)
    application.include_router(project_briefs_routes.router)
    application.include_router(investigations_routes.router)
    application.include_router(sources_routes.router)
    application.include_router(sources_routes.investigation_sources_router)
    application.include_router(evidence_routes.router)
    application.include_router(business_verdicts_routes.investigation_router)
    application.include_router(business_verdicts_routes.router)
    application.include_router(marketing_strategies_routes.router)
    application.include_router(implementation_plans_routes.router)
    application.include_router(agents_routes.router)
    application.include_router(agent_runs_routes.router)
    application.include_router(agent_chat_routes.router)
    application.include_router(chat_routes.router)
    application.include_router(llm_requests_routes.router)
    application.include_router(tasks.router)
    application.include_router(user_requests_routes.router)
    application.include_router(commercial_research_routes.router)
    application.include_router(analysis_contexts_routes.router)
    application.include_router(business_idea_validation_routes.router)
    application.include_router(business_idea_validation_routes.project_router)
    application.include_router(launch_pack_routes.router)
    application.include_router(offers_routes.router)
    application.include_router(knowledge_foundation_routes.router)
    application.include_router(knowledge_governance_routes.router)
    application.include_router(specialist_skills_routes.router)
    application.include_router(generated_visual_assets_routes.router)
    application.include_router(signed_media_routes.router)
    application.include_router(video_smoke_preview_routes.router)
    application.include_router(video_smoke_execute_routes.router)
    application.include_router(video_studio_routes.router)
    application.include_router(video_clips_routes.router)
    application.include_router(reference_visuals_routes.router)
    application.include_router(identity_generation_routes.router)
    application.include_router(memory.router)
    application.include_router(marketing_briefs_routes.router)
    application.include_router(marketing_plans_routes.router)
    application.include_router(marketing_scenarios_routes.router)
    application.include_router(business_campaigns_routes.router)
    application.include_router(business_operator_routes.router)
    application.include_router(marketing_tools_routes.router)
    application.include_router(marketing_skills_routes.router)
    application.include_router(scenario_wizard_runs_routes.router)
    application.include_router(marketing_plan_execution_runs_routes.router)
    application.include_router(marketing_specialist_outputs_routes.router)
    application.include_router(marketing_campaigns_routes.router)
    application.include_router(content_factory_routes.router)
    application.include_router(content_assets_routes.router)
    application.include_router(content_director_routes.router)
    application.include_router(visual_director_routes.router)
    application.include_router(project_command_center_routes.router)
    application.include_router(product_skills_routes.router)
    application.include_router(publication_packages_routes.router)
    application.include_router(media_briefs_routes.router)
    application.include_router(media_assets_routes.router)
    application.include_router(media_generation_routes.router)
    application.include_router(media_renderer_routes.router)
    application.include_router(marketing_funnels_routes.router)
    application.include_router(publishing_routes.channels_router)
    application.include_router(publishing_routes.jobs_router)
    application.include_router(publishing_routes.deliveries_router)
    application.include_router(publishing_routes.calendar_router)
    application.include_router(publishing_foundation_routes.foundation_channels_router)
    application.include_router(publishing_foundation_routes.package_jobs_router)
    application.include_router(publishing_foundation_routes.metrics_router)
    application.include_router(publishing_foundation_routes.scheduled_jobs_router)
    application.include_router(demo_flow_routes.demo_flow_router)
    application.include_router(demo_flow_routes.provenance_router)
    return application


app = create_app()
