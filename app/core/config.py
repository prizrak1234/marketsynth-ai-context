"""Application settings вЂ” single source of truth via environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration is loaded from environment / .env вЂ” no hardcoded secrets."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: Literal["development", "test", "pilot", "staging", "production"] = "development"
    app_name: str = "botfazer"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"
    # CPH.5 вЂ” public URL hints (sanitized; used by deploy validation / docs)
    public_frontend_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("PUBLIC_FRONTEND_URL", "public_frontend_url"),
        description="Pilot frontend public origin, e.g. https://pilot.example",
    )
    public_backend_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("PUBLIC_BACKEND_URL", "public_backend_url"),
        description="Pilot backend public origin, e.g. https://api.pilot.example",
    )
    pilot_backup_max_age_hours: float = Field(
        default=48.0,
        ge=1.0,
        le=720.0,
        validation_alias=AliasChoices(
            "PILOT_BACKUP_MAX_AGE_HOURS",
            "pilot_backup_max_age_hours",
        ),
        description="Warn when latest verified CPH.4 dump exceeds this age (hours).",
    )
    pilot_require_database_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "PILOT_REQUIRE_DATABASE_NAME",
            "pilot_require_database_name",
        ),
        description="If set, readiness/startup refuse when current DB name differs.",
    )

    host: str = "127.0.0.1"
    port: int = 8000

    telegram_webhook_secret: SecretStr | None = Field(
        default=None,
        description="Expected X-Telegram-Bot-Api-Secret-Token header value",
    )
    pii_sanitizer_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "pii_sanitizer_enabled",
            "pii_sanitize_enabled",
        ),
    )

    database_url: str = "postgresql+asyncpg://botfazer:botfazer@localhost:5432/botfazer"
    database_echo: bool = False
    alembic_revision_check_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "ALEMBIC_REVISION_CHECK_ENABLED",
            "alembic_revision_check_enabled",
        ),
        description="Read-only Alembic revision diagnostic at startup (never auto-migrates).",
    )
    alembic_revision_fail_fast: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "ALEMBIC_REVISION_FAIL_FAST",
            "alembic_revision_fail_fast",
        ),
        description=(
            "If true, refuse startup on missing-from-tree / unknown / ahead / multiple heads. "
            "Production should set true for pilot."
        ),
    )
    redis_url: str = "redis://localhost:6379/0"

    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "openai_api_key"),
    )
    anthropic_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("ANTHROPIC_API_KEY", "anthropic_api_key"),
    )
    google_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_API_KEY", "google_api_key"),
    )
    deepseek_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("DEEPSEEK_API_KEY", "deepseek_api_key"),
    )
    grok_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "GROK_API_KEY",
            "Grok_API_KEY",
            "XAI_API_KEY",
            "grok_api_key",
            "xai_api_key",
        ),
    )
    n8n_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("N8N_BASE_URL", "n8n_base_url"),
    )
    n8n_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("N8N_API_KEY", "n8n_api_key"),
    )
    make_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("MAKE_API_KEY", "make_api_key"),
    )
    make_zone: str | None = Field(
        default=None,
        validation_alias=AliasChoices("MAKE_ZONE", "make_zone"),
    )
    make_api_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("MAKE_API_BASE_URL", "make_api_base_url"),
    )
    firecrawl_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("FIRECRAWL_API_KEY", "firecrawl_api_key"),
    )
    xmlriver_user_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("XMLRIVER_USER_ID", "xmlriver_user_id"),
    )
    xmlriver_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("XMLRIVER_API_KEY", "xmlriver_api_key"),
    )
    xmlriver_wordstat_https: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "XMLRIVER_WORDSTAT_HTTPS",
            "xmlriver_wordstat_https",
        ),
        description="Prefer HTTPS for Wordstat product skill calls.",
    )
    avito_client_id: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("AVITO_CLIENT_ID", "avito_client_id"),
    )
    avito_client_secret: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("AVITO_CLIENT_SECRET", "avito_client_secret"),
    )
    research_source_collection_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "RESEARCH_SOURCE_COLLECTION_ENABLED",
            "research_source_collection_enabled",
        ),
    )
    research_source_collection_mock_providers: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "RESEARCH_SOURCE_COLLECTION_MOCK_PROVIDERS",
            "research_source_collection_mock_providers",
        ),
    )
    research_fetch_provider_order: str = Field(
        default="firecrawl,jina,tavily,trafilatura,playwright",
        validation_alias=AliasChoices(
            "RESEARCH_FETCH_PROVIDER_ORDER",
            "research_fetch_provider_order",
        ),
    )
    research_fetch_fallback_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "RESEARCH_FETCH_FALLBACK_ENABLED",
            "research_fetch_fallback_enabled",
        ),
    )
    research_fetch_max_provider_attempts: int = Field(
        default=5,
        ge=1,
        le=10,
        validation_alias=AliasChoices(
            "RESEARCH_FETCH_MAX_PROVIDER_ATTEMPTS",
            "research_fetch_max_provider_attempts",
        ),
    )
    research_fetch_timeout_seconds: float = Field(
        default=30.0,
        ge=5.0,
        le=120.0,
        validation_alias=AliasChoices(
            "RESEARCH_FETCH_TIMEOUT_SECONDS",
            "research_fetch_timeout_seconds",
        ),
    )
    research_fetch_max_content_bytes: int = Field(
        default=512_000,
        ge=1024,
        le=5_000_000,
        validation_alias=AliasChoices(
            "RESEARCH_FETCH_MAX_CONTENT_BYTES",
            "research_fetch_max_content_bytes",
        ),
    )
    research_fetch_cache_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "RESEARCH_FETCH_CACHE_ENABLED",
            "research_fetch_cache_enabled",
        ),
    )
    research_fetch_playwright_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "RESEARCH_FETCH_PLAYWRIGHT_ENABLED",
            "research_fetch_playwright_enabled",
        ),
    )
    jina_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("JINA_API_KEY", "jina_api_key"),
    )
    tavily_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("TAVILY_API_KEY", "tavily_api_key"),
    )
    tavily_extract_depth: str = Field(
        default="basic",
        validation_alias=AliasChoices("TAVILY_EXTRACT_DEPTH", "tavily_extract_depth"),
    )
    biv_research_max_search_calls: int = Field(
        default=32,
        ge=1,
        le=64,
        validation_alias=AliasChoices(
            "BIV_RESEARCH_MAX_SEARCH_CALLS",
            "biv_research_max_search_calls",
        ),
    )
    biv_research_max_fetch_calls: int = Field(
        default=40,
        ge=1,
        le=80,
        validation_alias=AliasChoices(
            "BIV_RESEARCH_MAX_FETCH_CALLS",
            "biv_research_max_fetch_calls",
        ),
    )
    biv_research_max_latency_seconds: float = Field(
        default=600.0,
        ge=60.0,
        le=3600.0,
        validation_alias=AliasChoices(
            "BIV_RESEARCH_MAX_LATENCY_SECONDS",
            "biv_research_max_latency_seconds",
        ),
    )
    biv_research_max_estimated_cost_usd: float = Field(
        default=5.0,
        ge=0.1,
        le=100.0,
        validation_alias=AliasChoices(
            "BIV_RESEARCH_MAX_ESTIMATED_COST_USD",
            "biv_research_max_estimated_cost_usd",
        ),
    )
    biv_max_fetch_attempts_per_url: int = Field(
        default=3,
        ge=1,
        le=10,
        validation_alias=AliasChoices(
            "BIV_MAX_FETCH_ATTEMPTS_PER_URL",
            "biv_max_fetch_attempts_per_url",
        ),
    )
    biv_max_total_fetch_attempts: int = Field(
        default=120,
        ge=1,
        le=300,
        validation_alias=AliasChoices(
            "BIV_MAX_TOTAL_FETCH_ATTEMPTS",
            "biv_max_total_fetch_attempts",
        ),
    )
    biv_max_retries_per_provider: int = Field(
        default=2,
        ge=0,
        le=5,
        validation_alias=AliasChoices(
            "BIV_MAX_RETRIES_PER_PROVIDER",
            "biv_max_retries_per_provider",
        ),
    )
    biv_pipeline_hard_min_fetch_success_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices(
            "BIV_PIPELINE_HARD_MIN_FETCH_SUCCESS_RATE",
            "biv_pipeline_hard_min_fetch_success_rate",
        ),
    )
    mcp_read_only_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("MCP_READ_ONLY_ENABLED", "mcp_read_only_enabled"),
    )
    mcp_tool_call_timeout_seconds: float = Field(
        default=30.0,
        ge=1.0,
        le=120.0,
        validation_alias=AliasChoices(
            "MCP_TOOL_CALL_TIMEOUT_SECONDS",
            "mcp_tool_call_timeout_seconds",
        ),
    )
    mcp_max_response_bytes: int = Field(
        default=512_000,
        ge=1024,
        le=5_000_000,
        validation_alias=AliasChoices("MCP_MAX_RESPONSE_BYTES", "mcp_max_response_bytes"),
    )
    mcp_max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        validation_alias=AliasChoices("MCP_MAX_RETRIES", "mcp_max_retries"),
    )
    business_idea_validation_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "BUSINESS_IDEA_VALIDATION_ENABLED",
            "business_idea_validation_enabled",
        ),
    )
    biv_run_dispatcher_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "BIV_RUN_DISPATCHER_ENABLED",
            "biv_run_dispatcher_enabled",
        ),
    )
    biv_run_stale_seconds: int = Field(
        default=600,
        ge=60,
        le=86400,
        validation_alias=AliasChoices(
            "BIV_RUN_STALE_SECONDS",
            "biv_run_stale_seconds",
        ),
        description="Runs in running status without updated_at refresh beyond this are interrupted on startup.",
    )
    biv_e2e_deterministic_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "BIV_E2E_DETERMINISTIC_ENABLED",
            "biv_e2e_deterministic_enabled",
        ),
        description="Enable server-side deterministic research fixture (development/test E2E only).",
    )
    openrouter_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENROUTER_API_KEY", "openrouter_api_key"),
    )
    abacus_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "ABACUS_API_KEY",
            "ROUTELLM_API_KEY",
            "abacus_api_key",
            "routellm_api_key",
        ),
    )
    abacus_api_base_url: str = Field(
        default="https://routellm.abacus.ai/v1",
        validation_alias=AliasChoices(
            "ABACUS_API_BASE_URL",
            "ROUTELLM_API_BASE_URL",
            "abacus_api_base_url",
            "routellm_api_base_url",
        ),
    )
    pinecone_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("PINECONE_API_KEY", "pinecone_api_key"),
    )
    yandex_disk_oauth_token: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "YANDEX_DISK_OAUTH_TOKEN",
            "yandex_disk_oauth_token",
        ),
    )
    yandex_direct_oauth_token: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "YANDEX_DIRECT_OAUTH_TOKEN",
            "YANDEX_DIRECT_TOKEN",
            "yandex_direct_oauth_token",
        ),
    )
    yandex_ai_studio_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "YANDEX_AI_STUDIO_API_KEY",
            "yandex_ai_studio_api_key",
        ),
    )
    yandex_metrica_oauth_token: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "YANDEX_METRICA_OAUTH_TOKEN",
            "yandex_metrica_oauth_token",
        ),
    )
    google_oauth_client_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "GOOGLE_OAUTH_CLIENT_ID",
            "google_oauth_client_id",
        ),
    )
    google_oauth_client_secret: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "GOOGLE_OAUTH_CLIENT_SECRET",
            "google_oauth_client_secret",
        ),
    )

    default_llm_provider: str = Field(
        default="mock",
        validation_alias=AliasChoices("DEFAULT_LLM_PROVIDER", "default_llm_provider"),
    )
    default_llm_model: str = Field(
        default="mock-model",
        validation_alias=AliasChoices("DEFAULT_LLM_MODEL", "default_llm_model"),
    )
    llm_timeout_seconds: int = Field(
        default=60,
        validation_alias=AliasChoices("LLM_TIMEOUT_SECONDS", "llm_timeout_seconds"),
    )
    llm_max_retries: int = Field(
        default=2,
        validation_alias=AliasChoices("LLM_MAX_RETRIES", "llm_max_retries"),
    )
    chat_general_answer_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "CHAT_GENERAL_ANSWER_ENABLED",
            "chat_general_answer_enabled",
        ),
        description="Commercial chat: LLM general_answer for ordinary questions.",
    )
    chat_general_answer_e2e_delay_seconds: float = Field(
        default=0.0,
        ge=0.0,
        le=30.0,
        validation_alias=AliasChoices(
            "CHAT_GENERAL_ANSWER_E2E_DELAY_SECONDS",
            "chat_general_answer_e2e_delay_seconds",
        ),
        description="Dev/test only: artificial delay before general_answer LLM call.",
    )
    tools_provider_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("TOOLS_PROVIDER_ENABLED", "tools_provider_enabled"),
    )
    tool_result_max_bytes: int = Field(
        default=24_000,
        validation_alias=AliasChoices("TOOL_RESULT_MAX_BYTES", "tool_result_max_bytes"),
    )
    max_tool_calls_per_round: int = Field(
        default=5,
        ge=1,
        validation_alias=AliasChoices("MAX_TOOL_CALLS_PER_ROUND", "max_tool_calls_per_round"),
    )
    tool_results_total_max_bytes: int = Field(
        default=48_000,
        ge=1,
        validation_alias=AliasChoices(
            "TOOL_RESULTS_TOTAL_MAX_BYTES",
            "tool_results_total_max_bytes",
        ),
    )
    agent_write_tools_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "AGENT_WRITE_TOOLS_ENABLED",
            "agent_write_tools_enabled",
        ),
    )
    agent_write_tool_content_asset_create_draft_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "AGENT_WRITE_TOOL_CONTENT_ASSET_CREATE_DRAFT_ENABLED",
            "agent_write_tool_content_asset_create_draft_enabled",
        ),
    )
    agent_write_tool_campaign_plan_draft_create_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "CAMPAIGN_PLAN_DRAFT_WRITE_TOOL_ENABLED",
            "AGENT_WRITE_TOOL_CAMPAIGN_PLAN_DRAFT_CREATE_ENABLED",
            "agent_write_tool_campaign_plan_draft_create_enabled",
        ),
    )
    agent_chat_tools_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "AGENT_CHAT_TOOLS_ENABLED",
            "agent_chat_tools_enabled",
        ),
    )
    agent_chat_session_history_limit: int = Field(
        default=10,
        ge=1,
        le=50,
        validation_alias=AliasChoices(
            "AGENT_CHAT_SESSION_HISTORY_LIMIT",
            "agent_chat_session_history_limit",
        ),
    )
    agent_write_tool_campaign_plan_draft_generate_assets_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_ENABLED",
            "AGENT_WRITE_TOOL_CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_ENABLED",
            "agent_write_tool_campaign_plan_draft_generate_assets_enabled",
        ),
    )
    agent_write_tool_content_asset_revision_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "CONTENT_ASSET_REVISION_WRITE_TOOL_ENABLED",
            "AGENT_WRITE_TOOL_CONTENT_ASSET_REVISION_ENABLED",
            "agent_write_tool_content_asset_revision_enabled",
        ),
    )
    agent_write_tool_body_max_chars: int = Field(
        default=12_000,
        ge=1,
        validation_alias=AliasChoices(
            "AGENT_WRITE_TOOL_BODY_MAX_CHARS",
            "agent_write_tool_body_max_chars",
        ),
    )
    content_asset_rollback_from_archived_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "CONTENT_ASSET_ROLLBACK_FROM_ARCHIVED_ENABLED",
            "content_asset_rollback_from_archived_enabled",
        ),
    )
    agent_execution_engine: Literal["classic", "langgraph"] = Field(
        default="classic",
        validation_alias=AliasChoices(
            "AGENT_EXECUTION_ENGINE",
            "agent_execution_engine",
        ),
    )
    agent_execution_engine_request_override_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "AGENT_EXECUTION_ENGINE_REQUEST_OVERRIDE_ENABLED",
            "agent_execution_engine_request_override_enabled",
        ),
    )
    agent_execution_langgraph_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "AGENT_EXECUTION_LANGGRAPH_ENABLED",
            "agent_execution_langgraph_enabled",
        ),
    )
    agent_execution_force_classic: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "AGENT_EXECUTION_FORCE_CLASSIC",
            "agent_execution_force_classic",
        ),
    )
    graph_version: str = Field(
        default="3.13",
        validation_alias=AliasChoices("GRAPH_VERSION", "graph_version"),
    )
    graph_max_steps: int = Field(
        default=16,
        ge=1,
        validation_alias=AliasChoices("GRAPH_MAX_STEPS", "graph_max_steps"),
    )
    graph_checkpoints_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "GRAPH_CHECKPOINTS_ENABLED",
            "graph_checkpoints_enabled",
        ),
    )
    graph_memory_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "GRAPH_MEMORY_ENABLED",
            "graph_memory_enabled",
        ),
    )
    graph_memory_limit: int = Field(
        default=5,
        ge=1,
        le=20,
        validation_alias=AliasChoices(
            "GRAPH_MEMORY_LIMIT",
            "graph_memory_limit",
        ),
    )
    graph_handoff_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "GRAPH_HANDOFF_ENABLED",
            "graph_handoff_enabled",
        ),
    )
    graph_handoff_child_run_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "GRAPH_HANDOFF_CHILD_RUN_ENABLED",
            "graph_handoff_child_run_enabled",
        ),
    )
    graph_handoff_execute_child: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "GRAPH_HANDOFF_EXECUTE_CHILD",
            "graph_handoff_execute_child",
        ),
    )
    graph_handoff_max_depth: int = Field(
        default=2,
        ge=0,
        le=5,
        validation_alias=AliasChoices(
            "GRAPH_HANDOFF_MAX_DEPTH",
            "graph_handoff_max_depth",
        ),
    )
    graph_handoff_worker_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "GRAPH_HANDOFF_WORKER_ENABLED",
            "graph_handoff_worker_enabled",
        ),
    )
    graph_handoff_worker_batch_limit: int = Field(
        default=5,
        ge=1,
        le=50,
        validation_alias=AliasChoices(
            "GRAPH_HANDOFF_WORKER_BATCH_LIMIT",
            "graph_handoff_worker_batch_limit",
        ),
    )
    graph_handoff_queue_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "GRAPH_HANDOFF_QUEUE_ENABLED",
            "graph_handoff_queue_enabled",
        ),
    )
    graph_handoff_scheduler_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "GRAPH_HANDOFF_SCHEDULER_ENABLED",
            "graph_handoff_scheduler_enabled",
        ),
    )
    graph_handoff_scheduler_interval_seconds: int = Field(
        default=30,
        ge=5,
        le=3600,
        validation_alias=AliasChoices(
            "GRAPH_HANDOFF_SCHEDULER_INTERVAL_SECONDS",
            "graph_handoff_scheduler_interval_seconds",
        ),
    )
    graph_handoff_scheduler_owner_limit: int = Field(
        default=10,
        ge=1,
        le=100,
        validation_alias=AliasChoices(
            "GRAPH_HANDOFF_SCHEDULER_OWNER_LIMIT",
            "graph_handoff_scheduler_owner_limit",
        ),
    )
    graph_handoff_max_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        validation_alias=AliasChoices(
            "GRAPH_HANDOFF_MAX_ATTEMPTS",
            "graph_handoff_max_attempts",
        ),
    )
    graph_handoff_dlq_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "GRAPH_HANDOFF_DLQ_ENABLED",
            "graph_handoff_dlq_enabled",
        ),
    )
    event_outbox_dispatcher_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "EVENT_OUTBOX_DISPATCHER_ENABLED",
            "event_outbox_dispatcher_enabled",
        ),
    )
    event_outbox_dispatcher_interval_seconds: int = Field(
        default=30,
        ge=5,
        le=3600,
        validation_alias=AliasChoices(
            "EVENT_OUTBOX_DISPATCHER_INTERVAL_SECONDS",
            "event_outbox_dispatcher_interval_seconds",
        ),
    )
    event_outbox_dispatch_batch_limit: int = Field(
        default=50,
        ge=1,
        le=500,
        validation_alias=AliasChoices(
            "EVENT_OUTBOX_DISPATCH_BATCH_LIMIT",
            "event_outbox_dispatch_batch_limit",
        ),
    )
    event_outbox_dispatch_max_attempts: int = Field(
        default=5,
        ge=1,
        le=20,
        validation_alias=AliasChoices(
            "EVENT_OUTBOX_DISPATCH_MAX_ATTEMPTS",
            "event_outbox_dispatch_max_attempts",
        ),
    )
    event_outbox_webhook_timeout_seconds: int = Field(
        default=10,
        ge=1,
        le=120,
        validation_alias=AliasChoices(
            "EVENT_OUTBOX_WEBHOOK_TIMEOUT_SECONDS",
            "event_outbox_webhook_timeout_seconds",
        ),
    )
    publication_worker_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "PUBLICATION_WORKER_ENABLED",
            "publication_worker_enabled",
        ),
    )
    publication_worker_interval_seconds: int = Field(
        default=30,
        ge=5,
        le=3600,
        validation_alias=AliasChoices(
            "PUBLICATION_WORKER_INTERVAL_SECONDS",
            "publication_worker_interval_seconds",
        ),
    )
    publication_job_max_attempts: int = Field(
        default=3,
        ge=1,
        le=20,
        validation_alias=AliasChoices(
            "PUBLICATION_JOB_MAX_ATTEMPTS",
            "publication_job_max_attempts",
        ),
    )
    publication_delivery_timeout_seconds: int = Field(
        default=10,
        ge=1,
        le=120,
        validation_alias=AliasChoices(
            "PUBLICATION_DELIVERY_TIMEOUT_SECONDS",
            "publication_delivery_timeout_seconds",
        ),
    )

    media_generation_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "MEDIA_GENERATION_ENABLED",
            "media_generation_enabled",
        ),
    )
    openai_images_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "OPENAI_IMAGES_ENABLED",
            "openai_images_enabled",
        ),
    )
    openai_images_model: str = Field(
        default="dall-e-3",
        validation_alias=AliasChoices(
            "OPENAI_IMAGES_MODEL",
            "openai_images_model",
        ),
    )
    # Phase H2.6A вЂ” UserRequest design.image_generation (separate from MediaBrief jobs)
    # Phase H2.7 вЂ” content.telegram_post draft execution (off until owner smoke).
    content_draft_execution_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "CONTENT_DRAFT_EXECUTION_ENABLED",
            "content_draft_execution_enabled",
        ),
    )
    # PRODUCT-CD-RUNTIME-01 — deterministic Text Director generation for tests/E2E only
    content_director_deterministic: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "CONTENT_DIRECTOR_DETERMINISTIC",
            "content_director_deterministic",
        ),
        description=(
            "When true, Content Director text generation returns fixture candidates. "
            "Must not be used as commercial customer path default."
        ),
    )
    # PRODUCT-CD-RUNTIME-02 — deterministic Image Director generation for tests/E2E only
    content_director_image_deterministic: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "CONTENT_DIRECTOR_IMAGE_DETERMINISTIC",
            "content_director_image_deterministic",
        ),
        description=(
            "When true, Visual Director image generation returns fixture PNG candidates. "
            "Must not be used as commercial customer path default."
        ),
    )
    # KG.2 — require published+fresh governed knowledge for industrial domains
    knowledge_governance_runtime_enforced: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "KNOWLEDGE_GOVERNANCE_RUNTIME_ENFORCED",
            "knowledge_governance_runtime_enforced",
        ),
        description=(
            "When true, drilling/industrial/oil-gas content.telegram_post "
            "must use a non-empty governed KnowledgeSnapshot or block."
        ),
    )
    content_draft_llm_provider: str = Field(
        default="mock",
        validation_alias=AliasChoices(
            "CONTENT_DRAFT_LLM_PROVIDER",
            "content_draft_llm_provider",
        ),
    )
    content_draft_llm_model: str = Field(
        default="mock-model",
        validation_alias=AliasChoices(
            "CONTENT_DRAFT_LLM_MODEL",
            "content_draft_llm_model",
        ),
    )
    openrouter_api_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        validation_alias=AliasChoices(
            "OPENROUTER_API_BASE_URL",
            "openrouter_api_base_url",
        ),
    )
    image_generation_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "IMAGE_GENERATION_ENABLED",
            "image_generation_enabled",
        ),
    )
    image_generation_provider: str = Field(
        default="mock",
        validation_alias=AliasChoices(
            "IMAGE_GENERATION_PROVIDER",
            "image_generation_provider",
        ),
    )
    image_generation_storage_dir: str = Field(
        default="data/generated_visuals",
        validation_alias=AliasChoices(
            "IMAGE_GENERATION_STORAGE_DIR",
            "image_generation_storage_dir",
        ),
    )
    allow_mock_image_results: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "ALLOW_MOCK_IMAGE_RESULTS",
            "allow_mock_image_results",
        ),
    )
    # GPTunnel CreativeLab image API (H2.6A alternate / fallback)
    gptunnel_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "GPTUNNEL_API_KEY",
            "GPTunnel_API_REY",  # common typo alias
            "GPTUNNEL_API_REY",
            "gptunnel_api_key",
        ),
    )
    gptunnel_base_url: str = Field(
        default="https://gptunnel.ru/v1",
        validation_alias=AliasChoices("GPTUNNEL_BASE_URL", "gptunnel_base_url"),
    )
    gptunnel_images_model: str = Field(
        default="gpt-image-1",
        validation_alias=AliasChoices(
            "GPTUNNEL_IMAGES_MODEL",
            "gptunnel_images_model",
        ),
    )
    # Video Studio VS.1 — GPTunnel CreativeLab video (router adapter)
    video_generation_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "VIDEO_GENERATION_ENABLED",
            "video_generation_enabled",
        ),
    )
    gptunnel_video_model: str = Field(
        default="glabs-veo-3-1-fast",
        validation_alias=AliasChoices(
            "GPTUNNEL_VIDEO_MODEL",
            "gptunnel_video_model",
        ),
    )
    # CONN-HF-01 — Higgsfield MCP media renderer (executor only; Skills produce spec)
    higgsfield_mcp_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "HIGGSFIELD_MCP_ENABLED",
            "higgsfield_mcp_enabled",
        ),
    )
    higgsfield_mcp_endpoint: str = Field(
        default="https://mcp.higgsfield.ai/mcp",
        validation_alias=AliasChoices(
            "HIGGSFIELD_MCP_ENDPOINT",
            "higgsfield_mcp_endpoint",
        ),
    )
    higgsfield_oauth_access_token: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "HIGGSFIELD_OAUTH_ACCESS_TOKEN",
            "higgsfield_oauth_access_token",
        ),
        description="OAuth bearer token for Higgsfield MCP (tenant vault in SKILL-03).",
    )
    higgsfield_mcp_timeout_seconds: float = Field(
        default=60.0,
        ge=5.0,
        le=300.0,
        validation_alias=AliasChoices(
            "HIGGSFIELD_MCP_TIMEOUT_SECONDS",
            "higgsfield_mcp_timeout_seconds",
        ),
    )
    higgsfield_video_render_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "HIGGSFIELD_VIDEO_RENDER_ENABLED",
            "higgsfield_video_render_enabled",
        ),
        description="Separate gate for Higgsfield video render (distinct from VS GPTunnel freeze).",
    )
    higgsfield_mcp_tool_overrides_json: str = Field(
        default="{}",
        validation_alias=AliasChoices(
            "HIGGSFIELD_MCP_TOOL_OVERRIDES_JSON",
            "higgsfield_mcp_tool_overrides_json",
        ),
        description="Deprecated — provider tool mapping lives in sandbox operation_mapping.json.",
    )
    higgsfield_owner_sandbox_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "HIGGSFIELD_OWNER_SANDBOX_ENABLED",
            "higgsfield_owner_sandbox_enabled",
        ),
        description="Allow owner/admin live sandbox calls after sandbox_verified manifest.",
    )
    # Temporary HMAC signed media URLs for provider fetch (GPTunnel images[]).
    # Off by default. Absolute URLs require PUBLIC_BACKEND_URL reachable from the internet.
    asset_signed_url_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "ASSET_SIGNED_URL_ENABLED",
            "asset_signed_url_enabled",
        ),
    )
    asset_signed_url_ttl_seconds: int = Field(
        default=600,
        ge=60,
        le=600,
        validation_alias=AliasChoices(
            "ASSET_SIGNED_URL_TTL_SECONDS",
            "asset_signed_url_ttl_seconds",
        ),
        description="TTL for provider-fetch signed URLs (hard max 600s / 10 minutes).",
    )
    asset_signed_url_secret: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "ASSET_SIGNED_URL_SECRET",
            "asset_signed_url_secret",
        ),
        description="HMAC secret for short-lived provider-fetch URLs (not a session cookie).",
    )
    video_clip_download_max_bytes: int = Field(
        default=100 * 1024 * 1024,
        ge=1_048_576,
        le=500 * 1024 * 1024,
        validation_alias=AliasChoices(
            "VIDEO_CLIP_DOWNLOAD_MAX_BYTES",
            "video_clip_download_max_bytes",
        ),
        description="Maximum provider video download size for VS.2A clip import.",
    )
    video_clip_download_timeout_seconds: float = Field(
        default=120.0,
        ge=10.0,
        le=600.0,
        validation_alias=AliasChoices(
            "VIDEO_CLIP_DOWNLOAD_TIMEOUT_SECONDS",
            "video_clip_download_timeout_seconds",
        ),
    )
    image_generation_fallback_provider: str = Field(
        default="",
        validation_alias=AliasChoices(
            "IMAGE_GENERATION_FALLBACK_PROVIDER",
            "image_generation_fallback_provider",
        ),
    )
    # Phase H2.6A-R вЂ” reference uploads
    reference_image_max_count: int = Field(
        default=15,
        validation_alias=AliasChoices(
            "REFERENCE_IMAGE_MAX_COUNT",
            "reference_image_max_count",
        ),
    )
    reference_image_max_bytes_per_file: int = Field(
        default=20 * 1024 * 1024,
        validation_alias=AliasChoices(
            "REFERENCE_IMAGE_MAX_BYTES_PER_FILE",
            "reference_image_max_bytes_per_file",
        ),
    )
    reference_image_max_total_bytes: int = Field(
        default=150 * 1024 * 1024,
        validation_alias=AliasChoices(
            "REFERENCE_IMAGE_MAX_TOTAL_BYTES",
            "reference_image_max_total_bytes",
        ),
    )
    reference_image_min_width: int = Field(
        default=256,
        validation_alias=AliasChoices(
            "REFERENCE_IMAGE_MIN_WIDTH",
            "reference_image_min_width",
        ),
    )
    reference_image_min_height: int = Field(
        default=256,
        validation_alias=AliasChoices(
            "REFERENCE_IMAGE_MIN_HEIGHT",
            "reference_image_min_height",
        ),
    )
    reference_image_storage_dir: str = Field(
        default="data/reference_visuals",
        validation_alias=AliasChoices(
            "REFERENCE_IMAGE_STORAGE_DIR",
            "reference_image_storage_dir",
        ),
    )
    reference_provider_max_images: int = Field(
        default=10,
        validation_alias=AliasChoices(
            "REFERENCE_PROVIDER_MAX_IMAGES",
            "reference_provider_max_images",
        ),
    )
    # H2.8D вЂ” person identity mode: max identity refs transmitted to provider
    reference_identity_max_images: int = Field(
        default=5,
        validation_alias=AliasChoices(
            "REFERENCE_IDENTITY_MAX_IMAGES",
            "reference_identity_max_images",
        ),
    )
    # H2.8D вЂ” gated A/B harness (paid provider calls require explicit confirm)
    identity_ab_harness_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "IDENTITY_AB_HARNESS_ENABLED",
            "identity_ab_harness_enabled",
        ),
    )

    telegram_publication_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "TELEGRAM_PUBLISHING_ENABLED",
            "TELEGRAM_PUBLICATION_ENABLED",
            "telegram_publishing_enabled",
            "telegram_publication_enabled",
        ),
    )
    telegram_publication_bot_token: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_PUBLICATION_BOT_TOKEN",
            "telegram_bot_token",
            "telegram_publication_bot_token",
        ),
    )
    telegram_publication_timeout_seconds: int = Field(
        default=10,
        ge=1,
        le=120,
        validation_alias=AliasChoices(
            "TELEGRAM_PUBLICATION_TIMEOUT_SECONDS",
            "telegram_publication_timeout_seconds",
        ),
    )

    demo_flow_endpoints_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "DEMO_FLOW_ENDPOINTS_ENABLED",
            "demo_flow_endpoints_enabled",
        ),
    )
    beta_admin_endpoints_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "BETA_ADMIN_ENDPOINTS_ENABLED",
            "beta_admin_endpoints_enabled",
        ),
    )
    beta_access_gate_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "BETA_ACCESS_GATE_ENABLED",
            "beta_access_gate_enabled",
        ),
    )
    beta_limits_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "BETA_LIMITS_ENABLED",
            "beta_limits_enabled",
        ),
    )
    business_operator_confidence_threshold: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices(
            "BUSINESS_OPERATOR_CONFIDENCE_THRESHOLD",
            "business_operator_confidence_threshold",
        ),
    )
    business_operator_llm_fallback_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "BUSINESS_OPERATOR_LLM_FALLBACK_ENABLED",
            "business_operator_llm_fallback_enabled",
        ),
    )
    business_operator_llm_min_confidence_to_accept: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices(
            "BUSINESS_OPERATOR_LLM_MIN_CONFIDENCE_TO_ACCEPT",
            "business_operator_llm_min_confidence_to_accept",
        ),
    )
    campaign_brief_completeness_threshold: int = Field(
        default=100,
        ge=0,
        le=100,
        validation_alias=AliasChoices(
            "CAMPAIGN_BRIEF_COMPLETENESS_THRESHOLD",
            "campaign_brief_completeness_threshold",
        ),
    )
    marketing_data_tools_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "MARKETING_DATA_TOOLS_ENABLED",
            "marketing_data_tools_enabled",
        ),
    )
    marketing_data_tools_mock_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "MARKETING_DATA_TOOLS_MOCK_ENABLED",
            "marketing_data_tools_mock_enabled",
        ),
    )
    marketing_skills_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "MARKETING_SKILLS_ENABLED",
            "marketing_skills_enabled",
        ),
    )
    marketing_skills_mock_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "MARKETING_SKILLS_MOCK_ENABLED",
            "marketing_skills_mock_enabled",
        ),
    )
    beta_max_projects_per_user: int = Field(default=100, ge=1, le=10_000)
    beta_max_chat_sessions_per_project: int = Field(default=500, ge=1, le=100_000)
    beta_max_marketing_plans_per_project: int = Field(default=200, ge=1, le=10_000)
    beta_max_generation_jobs_per_day: int = Field(default=500, ge=1, le=100_000)
    beta_max_publication_jobs_per_day: int = Field(default=500, ge=1, le=100_000)
    beta_strict_max_projects_per_user: int = Field(default=10, ge=1, le=1000)
    beta_strict_max_chat_sessions_per_project: int = Field(default=50, ge=1, le=10_000)
    beta_strict_max_marketing_plans_per_project: int = Field(default=25, ge=1, le=1000)
    beta_strict_max_generation_jobs_per_day: int = Field(default=30, ge=1, le=10_000)
    beta_strict_max_publication_jobs_per_day: int = Field(default=40, ge=1, le=10_000)

    # CPH.3 вЂ” pilot browser sessions (HttpOnly cookie; API keys remain for non-browser clients)
    browser_session_ttl_hours: int = Field(
        default=8,
        ge=1,
        le=72,
        validation_alias=AliasChoices(
            "BROWSER_SESSION_TTL_HOURS",
            "browser_session_ttl_hours",
        ),
    )
    browser_session_cookie_name: str = Field(
        default="ms_pilot_session",
        validation_alias=AliasChoices(
            "BROWSER_SESSION_COOKIE_NAME",
            "browser_session_cookie_name",
        ),
    )
    browser_session_cookie_secure: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "BROWSER_SESSION_COOKIE_SECURE",
            "browser_session_cookie_secure",
        ),
        description="Set true when serving HTTPS (pilot/production).",
    )
    browser_session_cookie_samesite: Literal["lax", "strict", "none"] = Field(
        default="lax",
        validation_alias=AliasChoices(
            "BROWSER_SESSION_COOKIE_SAMESITE",
            "browser_session_cookie_samesite",
        ),
    )
    browser_allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        validation_alias=AliasChoices(
            "BROWSER_ALLOWED_ORIGINS",
            "browser_allowed_origins",
        ),
        description="CORS + CSRF Origin allowlist for cookie-authenticated browser calls.",
    )
    browser_csrf_allow_missing_origin: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "BROWSER_CSRF_ALLOW_MISSING_ORIGIN",
            "browser_csrf_allow_missing_origin",
        ),
        description="Dev-only escape hatch for clients that omit Origin (keep false for pilot).",
    )
    # Pilot self-registration v1 вЂ” never invent from debug alone; production default false.
    public_signup_enabled: bool | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "PUBLIC_SIGNUP_ENABLED",
            "public_signup_enabled",
        ),
        description=(
            "When true, POST /auth/register creates member accounts. "
            "None = auto: true for development/test only; false for pilot/staging/production."
        ),
    )
    public_signup_auto_approve_beta: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "PUBLIC_SIGNUP_AUTO_APPROVE_BETA",
            "public_signup_auto_approve_beta",
        ),
        description="If true, new self-registered members get beta_access_status=approved.",
    )

    @property
    def signup_enabled(self) -> bool:
        """Server-side gate for self-registration (role always member)."""
        if self.public_signup_enabled is not None:
            return bool(self.public_signup_enabled)
        return self.app_env in {"development", "test"}

        return self.demo_flow_endpoints_enabled or self.is_development

    @property
    def beta_admin_access_allowed(self) -> bool:
        return self.beta_admin_endpoints_enabled or self.is_development

    @property
    def beta_access_gate_bypass(self) -> bool:
        return self.is_development

    @property
    def beta_limits_strict(self) -> bool:
        return self.is_production or self.app_env in {"staging", "pilot"}

    def effective_beta_limit(self, *, generous: int, strict: int) -> int:
        if not self.beta_limits_enabled:
            return generous
        return strict if self.beta_limits_strict else generous

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def biv_e2e_deterministic_allowed(self) -> bool:
        """E2E fixture boundary — env-gated; never active in pilot/staging/production."""
        return self.biv_e2e_deterministic_enabled and self.app_env in {"development", "test"}

    @property
    def is_pilot(self) -> bool:
        return self.app_env == "pilot"

    @property
    def is_pilot_like(self) -> bool:
        """Hardened operational modes: pilot, staging, production."""
        return self.app_env in {"pilot", "staging", "production"}

    @property
    def cors_enabled(self) -> bool:
        """Credentialed CORS only when origins are explicit (never wildcard)."""
        return self.is_development or self.app_env == "test" or self.is_pilot_like

    @property
    def higgsfield_mcp_configured(self) -> bool:
        token = self.higgsfield_oauth_access_token
        if token is None:
            return False
        return bool(token.get_secret_value().strip())

    @property
    def higgsfield_sandbox_verified(self) -> bool:
        from app.connectors.higgsfield.sandbox.operation_mapping import load_operation_mapping

        return load_operation_mapping().sandbox_verified()

    @property
    def higgsfield_mcp_live_calls_allowed(self) -> bool:
        return (
            self.higgsfield_mcp_enabled
            and self.higgsfield_mcp_configured
            and self.higgsfield_sandbox_verified
            and self.higgsfield_owner_sandbox_enabled
        )

    @property
    def higgsfield_mcp_tool_overrides(self) -> dict[str, str]:
        import json

        raw = (self.higgsfield_mcp_tool_overrides_json or "{}").strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        if not isinstance(parsed, dict):
            return {}
        return {str(k): str(v) for k, v in parsed.items()}

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        return value.upper()

    def safe_dict(self) -> dict[str, object]:
        """Settings snapshot safe for logs (secrets redacted)."""
        import re

        data = self.model_dump()
        secret_fields = (
            "telegram_webhook_secret",
            "telegram_publication_bot_token",
            "openai_api_key",
            "anthropic_api_key",
            "google_api_key",
            "deepseek_api_key",
            "gptunnel_api_key",
            "grok_api_key",
            "n8n_api_key",
            "make_api_key",
            "firecrawl_api_key",
            "xmlriver_api_key",
            "avito_client_id",
            "avito_client_secret",
            "openrouter_api_key",
            "abacus_api_key",
            "pinecone_api_key",
            "yandex_disk_oauth_token",
            "yandex_direct_oauth_token",
            "yandex_ai_studio_api_key",
            "yandex_metrica_oauth_token",
            "abacus_api_key",
            "google_oauth_client_secret",
            "higgsfield_oauth_access_token",
        )
        for field_name in secret_fields:
            if data.get(field_name) is not None:
                data[field_name] = "***"
        if data.get("database_url"):
            data["database_url"] = re.sub(
                r"://([^:/]+):([^@]+)@",
                r"://\1:***@",
                str(data["database_url"]),
            )
        if data.get("redis_url"):
            data["redis_url"] = re.sub(
                r"://([^:/]+):([^@]+)@",
                r"://\1:***@",
                str(data["redis_url"]),
            )
        return data


@lru_cache
def get_settings() -> Settings:
    return Settings()
