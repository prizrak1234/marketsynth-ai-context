"""Explicit allowlists — never recursive /docs or whole-repo indexing."""

from __future__ import annotations

# Paths that may become KnowledgeItem candidates after review (allowlist only).
KNOWLEDGE_SOURCE_ALLOWLIST: frozenset[str] = frozenset(
    {
        "docs/PROJECT_VISION.md",
        "docs/AGENT_OS_ARCHITECTURE.md",
        "docs/MARKETING_AGENT_TARGET_MODEL.md",
        "docs/MARKETING_FRAMEWORKS_CONTEXT.md",
        "docs/KNOWLEDGE_ARCHITECTURE.md",
        "docs/CURSOR_OPERATING_RULES.md",
        "docs/DEVELOPMENT.md",
        "standards/memory",
        "standards/skills",
        "standards/tools",
        "standards/supervisor",
        "standards/workflows",
        "knowledge/manuals",
        "knowledge/positioning",
        "knowledge/audience",
        "skills/segment-research",
        "skills/offer-packaging",
        "skills/content-production",
        "skills/wordstat-research",
        "skills/metrica-analysis",
        "skills/supervisor-quality",
    }
)

# Hard exclude — never auto-index, never treat as operational truth.
KNOWLEDGE_SOURCE_BLOCKLIST_PREFIXES: tuple[str, ...] = (
    "docs/phase_ai_",
    "docs/controlled_pilot_",
    "alembic/",
    ".venv/",
    "tests/",
    "web/e2e/",
    "knowledge_import/",
    "workflows/raw/",
    ".env",
    "scripts/",
    ".pytest_cache/",
    "agent-transcripts/",
)

KNOWLEDGE_SOURCE_BLOCKLIST_GLOBS: tuple[str, ...] = (
    "**/BOTFAZER_*",
    "**/*audit*.md",
    "**/*readiness_audit*.md",
    "**/*_freeze*.md",
    "**/mock*",
    "**/*.log",
    "**/credentials*",
    "**/*secret*",
)

FORBIDDEN_CONTENT_MARKERS: frozenset[str] = frozenset(
    {
        "api_key",
        "apikey",
        "secret_key",
        "private_key",
        "password=",
        "BEGIN RSA PRIVATE KEY",
        "chain-of-thought",
        "chain_of_thought",
    }
)


def is_path_blocked(source_uri: str) -> bool:
    normalized = source_uri.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    for prefix in KNOWLEDGE_SOURCE_BLOCKLIST_PREFIXES:
        if normalized == prefix or normalized.startswith(prefix) or f"/{prefix}" in f"/{normalized}":
            return True
    lower = normalized.lower()
    if "botfazer" in lower and "marketsynth" not in lower and "architecture" not in lower:
        # Legacy BotFazer brand docs are historical unless explicitly allowlisted.
        if normalized not in KNOWLEDGE_SOURCE_ALLOWLIST:
            return True
    return False


def is_path_allowlisted(source_uri: str) -> bool:
    normalized = source_uri.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if is_path_blocked(normalized):
        return False
    if normalized in KNOWLEDGE_SOURCE_ALLOWLIST:
        return True
    return any(
        normalized == path or normalized.startswith(f"{path}/")
        for path in KNOWLEDGE_SOURCE_ALLOWLIST
    )


def contains_forbidden_secret_markers(text: str) -> bool:
    lower = (text or "").lower()
    return any(marker.lower() in lower for marker in FORBIDDEN_CONTENT_MARKERS)
