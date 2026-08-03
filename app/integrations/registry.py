"""Integration Registry (Phase H2.7).

Authoritative, governed view of external integrations. Credential presence
never implies capability: readiness is decided here, not by the .env file.
No secrets are ever returned — only masked presence and safe diagnostics.
"""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.schemas.contracts import (
    IntegrationAuthType,
    IntegrationCategory,
    IntegrationCode,
    IntegrationDefinition,
    IntegrationReadiness,
    IntegrationRiskLevel,
)


def _has(secret: object | None) -> bool:
    if secret is None:
        return False
    raw = secret.get_secret_value() if hasattr(secret, "get_secret_value") else secret
    return bool(raw and str(raw).strip())


def build_integration_registry(
    settings: Settings | None = None,
) -> list[IntegrationDefinition]:
    """Build the current registry snapshot. Pure function of Settings."""
    s = settings or get_settings()
    env = (s.app_env or "development").strip().lower()

    openai_ready = _has(s.openai_api_key)
    openrouter_ready = _has(s.openrouter_api_key)
    gptunnel_ready = _has(s.gptunnel_api_key)
    higgsfield_ready = _has(s.higgsfield_oauth_access_token)
    firecrawl_cfg = _has(s.firecrawl_api_key)
    xmlriver_cfg = bool(s.xmlriver_user_id) and _has(s.xmlriver_api_key)
    pinecone_cfg = _has(s.pinecone_api_key)
    make_cfg = _has(s.make_api_key)
    n8n_cfg = bool(s.n8n_base_url) and _has(s.n8n_api_key)
    direct_cfg = _has(s.yandex_direct_oauth_token)
    metrica_cfg = _has(getattr(s, "yandex_metrica_oauth_token", None))

    defs: list[IntegrationDefinition] = [
        IntegrationDefinition(
            code=IntegrationCode.OPENAI,
            provider="OpenAI",
            category=IntegrationCategory.LLM,
            read_capabilities=["chat_completion", "image_generation"],
            authentication_type=IntegrationAuthType.API_KEY,
            configured=openai_ready,
            readiness=(
                IntegrationReadiness.READY if openai_ready else IntegrationReadiness.CONFIGURED
            ),
            health_status="key_present" if openai_ready else "key_missing",
            allowed_environments=["development", "test", "pilot", "staging", "production"],
            cost_profile="per_token",
            risk_level=IntegrationRiskLevel.LOW,
            owner_approval_required=False,
            supported_skills=["content.telegram_post", "design.image_generation"],
        ),
        IntegrationDefinition(
            code=IntegrationCode.OPENROUTER,
            provider="OpenRouter",
            category=IntegrationCategory.LLM,
            read_capabilities=["chat_completion"],
            authentication_type=IntegrationAuthType.API_KEY,
            configured=openrouter_ready,
            readiness=(
                IntegrationReadiness.READY if openrouter_ready else IntegrationReadiness.CONFIGURED
            ),
            health_status="key_present" if openrouter_ready else "key_missing",
            allowed_environments=["development", "test", "pilot", "staging", "production"],
            cost_profile="per_token",
            risk_level=IntegrationRiskLevel.LOW,
            owner_approval_required=False,
            supported_skills=["content.telegram_post"],
            notes="LLM provider option via LLM adapter only; skills never select provider.",
        ),
        IntegrationDefinition(
            code=IntegrationCode.GPTUNNEL,
            provider="GPTunnel",
            category=IntegrationCategory.IMAGE,
            read_capabilities=["image_generation"],
            authentication_type=IntegrationAuthType.API_KEY,
            configured=gptunnel_ready,
            readiness=(
                IntegrationReadiness.READY if gptunnel_ready else IntegrationReadiness.CONFIGURED
            ),
            health_status="key_present" if gptunnel_ready else "key_missing",
            cost_profile="per_image",
            risk_level=IntegrationRiskLevel.LOW,
            owner_approval_required=False,
            supported_skills=["design.image_generation"],
        ),
        IntegrationDefinition(
            code=IntegrationCode.HIGGSFIELD,
            provider="Higgsfield",
            category=IntegrationCategory.IMAGE,
            read_capabilities=["generation_status", "download_result"],
            write_capabilities=["render_image", "render_video"],
            authentication_type=IntegrationAuthType.OAUTH_TOKEN,
            configured=higgsfield_ready,
            readiness=(
                IntegrationReadiness.READY
                if higgsfield_ready and s.higgsfield_mcp_enabled
                else IntegrationReadiness.CONFIGURED
                if s.higgsfield_mcp_enabled
                else IntegrationReadiness.DISABLED
            ),
            health_status=(
                "oauth_present"
                if higgsfield_ready
                else "oauth_missing"
            ),
            cost_profile="per_generation",
            risk_level=IntegrationRiskLevel.HIGH,
            owner_approval_required=True,
            supported_skills=[
                "ms.skill.presentation_architecture",
                "ms.skill.visual_brief",
                "ms.skill.image_generation_spec",
            ],
            notes=(
                "Executor-only MCP renderer via connector.higgsfield. "
                "Skills must supply complete MediaRenderSpec; no business logic in connector."
            ),
        ),
        IntegrationDefinition(
            code=IntegrationCode.FIRECRAWL,
            provider="Firecrawl",
            category=IntegrationCategory.RESEARCH_READ,
            read_capabilities=["fetch_url", "scrape_single"],
            authentication_type=IntegrationAuthType.API_KEY,
            configured=firecrawl_cfg,
            # Read-only candidate; not wired to an executable research skill this slice.
            readiness=(
                IntegrationReadiness.CONFIGURED if firecrawl_cfg else IntegrationReadiness.DISABLED
            ),
            health_status="key_present" if firecrawl_cfg else "key_missing",
            cost_profile="per_request",
            risk_level=IntegrationRiskLevel.LOW,
            owner_approval_required=True,
            supported_skills=[],
            notes="Read-only source fetch. Returns Source candidates only; no Evidence.",
        ),
        IntegrationDefinition(
            code=IntegrationCode.XMLRIVER,
            provider="XMLRiver",
            category=IntegrationCategory.SEARCH_READ,
            read_capabilities=["web_search", "wordstat"],
            authentication_type=IntegrationAuthType.API_KEY,
            configured=xmlriver_cfg,
            readiness=(
                IntegrationReadiness.CONFIGURED if xmlriver_cfg else IntegrationReadiness.DISABLED
            ),
            health_status="key_present" if xmlriver_cfg else "key_missing",
            cost_profile="per_request",
            risk_level=IntegrationRiskLevel.LOW,
            owner_approval_required=True,
            supported_skills=[],
            notes="Read-only search. Returns candidate sources only; no auto Evidence.",
        ),
        IntegrationDefinition(
            code=IntegrationCode.PINECONE,
            provider="Pinecone",
            category=IntegrationCategory.RETRIEVAL,
            read_capabilities=["vector_query"],
            write_capabilities=["upsert"],
            authentication_type=IntegrationAuthType.API_KEY,
            configured=pinecone_cfg,
            # Explicitly disabled: PostgreSQL FTS remains Source of Truth.
            readiness=IntegrationReadiness.DISABLED,
            health_status="disabled_by_policy",
            cost_profile="per_query",
            risk_level=IntegrationRiskLevel.MEDIUM,
            owner_approval_required=True,
            supported_skills=[],
            notes="Disabled until retrieval comparison justifies it. Not Source of Truth.",
        ),
        IntegrationDefinition(
            code=IntegrationCode.MAKE,
            provider="Make",
            category=IntegrationCategory.EXTERNAL_EXECUTION,
            read_capabilities=["scenario_read"],
            write_capabilities=["scenario_run"],
            authentication_type=IntegrationAuthType.API_KEY,
            configured=make_cfg,
            # Configured only; execution stays behind an approval boundary.
            readiness=(
                IntegrationReadiness.CONFIGURED if make_cfg else IntegrationReadiness.DISABLED
            ),
            health_status="configured_execution_disabled" if make_cfg else "key_missing",
            cost_profile="per_operation",
            risk_level=IntegrationRiskLevel.HIGH,
            owner_approval_required=True,
            supported_skills=[],
            notes="Execution disabled. Draft descriptor only; explicit approval required.",
        ),
        IntegrationDefinition(
            code=IntegrationCode.N8N,
            provider="n8n",
            category=IntegrationCategory.EXTERNAL_EXECUTION,
            read_capabilities=["workflow_read"],
            write_capabilities=["workflow_create", "workflow_activate"],
            authentication_type=IntegrationAuthType.API_KEY,
            configured=n8n_cfg,
            # Hard blocked: SSL certificate mismatch + API method mismatch (405).
            readiness=IntegrationReadiness.BLOCKED,
            health_status="ssl_certificate_mismatch;http_405_method_not_allowed",
            cost_profile="self_hosted",
            risk_level=IntegrationRiskLevel.HIGH,
            owner_approval_required=True,
            supported_skills=[],
            notes=(
                "Blocked. Do not bypass TLS verification. Re-audit only after the host "
                "certificate and API method mismatch are fixed."
            ),
        ),
        IntegrationDefinition(
            code=IntegrationCode.YANDEX_DIRECT,
            provider="Yandex Direct",
            category=IntegrationCategory.ADVERTISING,
            read_capabilities=["account_read", "campaign_read", "metrics_read"],
            write_capabilities=["campaign_write", "budget_write"],
            authentication_type=IntegrationAuthType.OAUTH_TOKEN,
            configured=direct_cfg,
            # Write disabled; read pending API access approval (error 58).
            readiness=(
                IntegrationReadiness.CONFIGURED if direct_cfg else IntegrationReadiness.DISABLED
            ),
            health_status="write_disabled;api_access_application_required" if direct_cfg else "token_missing",
            cost_profile="ad_spend",
            risk_level=IntegrationRiskLevel.HIGH,
            owner_approval_required=True,
            supported_skills=[],
            notes="Read-only audit later. All write/budget actions disabled.",
        ),
        IntegrationDefinition(
            code=IntegrationCode.YANDEX_METRICA,
            provider="Yandex Metrica",
            category=IntegrationCategory.ANALYTICS,
            read_capabilities=["counters_read", "stats_read"],
            authentication_type=IntegrationAuthType.OAUTH_TOKEN,
            configured=metrica_cfg,
            readiness=(
                IntegrationReadiness.CONFIGURED if metrica_cfg else IntegrationReadiness.DISABLED
            ),
            health_status="scope_or_access_pending" if metrica_cfg else "token_missing",
            cost_profile="free_tier",
            risk_level=IntegrationRiskLevel.MEDIUM,
            owner_approval_required=True,
            supported_skills=[],
            notes="Read-only later. counter_id is per-project (provided in UI, not global env).",
        ),
    ]
    # Environment scoping: nothing is 'ready' outside its allowed environments.
    for d in defs:
        if env not in d.allowed_environments and d.readiness == IntegrationReadiness.READY:
            d.readiness = IntegrationReadiness.CONFIGURED
    return defs


def get_integration(
    code: IntegrationCode,
    settings: Settings | None = None,
) -> IntegrationDefinition | None:
    for d in build_integration_registry(settings):
        if d.code == code:
            return d
    return None
