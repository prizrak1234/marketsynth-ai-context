"""Workflow metadata normalization, provider taxonomy, and redaction."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

ABS_PATH = re.compile(r"(?:[A-Za-z]:\\|/Users/|/home/|/tmp/)")
SECRET_VALUE = re.compile(
    r"(sk-[a-zA-Z0-9]{20,}|Bearer\s+[a-zA-Z0-9._\-]{10,}|password\s*[:=]\s*['\"][^'\"]+['\"])",
    re.I,
)

NON_PROVIDER_NODE_SUFFIXES = frozenset(
    {
        "stickyNote",
        "code",
        "set",
        "if",
        "merge",
        "wait",
        "httpRequest",
        "webhook",
        "scheduleTrigger",
        "formTrigger",
        "manualTrigger",
        "switch",
        "splitInBatches",
        "aggregate",
        "noOp",
        "filter",
        "itemLists",
        "renameKeys",
        "respondToWebhook",
        "executeWorkflow",
        "start",
        "stopAndError",
        "compareDatasets",
        "limit",
        "removeDuplicates",
        "sort",
        "summarize",
        "dateTime",
        "crypto",
        "html",
        "xml",
        "markdown",
        "moveBinaryData",
        "binaryToPropery",
        "convertToFile",
        "extractFromFile",
        "compression",
        "editImage",
        "executeCommand",
        "function",
        "functionItem",
        "readBinaryFile",
        "readBinaryFiles",
        "writeBinaryFile",
        "spreadsheetFile",
        "dateTimeTool",
        "evaluation",
        "evaluationTrigger",
        "dataTable",
        "dataTableTool",
        "httpRequestTool",
        "uploadtourl",
        "htmlcsstopdf",
    }
)

PROVIDER_FROM_NODE_SUFFIX: dict[str, str] = {
    "googleSheets": "Google Sheets",
    "googleSheetsTrigger": "Google Sheets",
    "googleSheetsTool": "Google Sheets",
    "googleDrive": "Google Drive",
    "googleDocs": "Google Docs",
    "gmail": "Gmail",
    "gmailTrigger": "Gmail",
    "gmailTool": "Gmail",
    "telegram": "Telegram",
    "telegramTrigger": "Telegram",
    "slack": "Slack",
    "slackTool": "Slack",
    "slackHitlTool": "Slack",
    "postgres": "Postgres",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "hubspot": "HubSpot",
    "pipedrive": "Pipedrive",
    "wordpress": "WordPress",
    "twitter": "Twitter",
    "facebookGraphApi": "Facebook",
    "instagram": "Instagram",
    "linkedin": "LinkedIn",
    "gitlab": "GitLab",
    "github": "GitHub",
    "jira": "Jira",
    "notion": "Notion",
    "airtable": "Airtable",
    "stripe": "Stripe",
    "paypal": "PayPal",
    "serpapi": "SerpAPI",
    "reddit": "Reddit",
    "emailSend": "SMTP",
    "perplexityTool": "Perplexity",
    "n8n": "n8n",
}

PROVIDER_FROM_CREDENTIAL: dict[str, str] = {
    "googleSheetsOAuth2Api": "Google Sheets",
    "gmailOAuth2": "Gmail",
    "telegramApi": "Telegram",
    "slackOAuth2Api": "Slack",
    "openAiApi": "OpenAI",
    "postgres": "Postgres",
    "hubspotOAuth2Api": "HubSpot",
    "wordpressApi": "WordPress",
    "twitterOAuth2Api": "Twitter",
    "facebookGraphApi": "Facebook",
    "stripeApi": "Stripe",
}

LANGCHAIN_PROVIDER_PATTERNS: list[tuple[str, str]] = [
    ("openai", "OpenAI"),
    ("groq", "Groq"),
    ("mistral", "Mistral"),
    ("anthropic", "Anthropic"),
    ("gemini", "Google Gemini"),
    ("cohere", "Cohere"),
    ("ollama", "Ollama"),
    ("openrouter", "OpenRouter"),
    ("azure", "Azure OpenAI"),
    ("bedrock", "AWS Bedrock"),
]

HOSTNAME_PROVIDER: dict[str, str] = {
    "api.openai.com": "OpenAI",
    "api.groq.com": "Groq",
    "api.mistral.ai": "Mistral",
    "openrouter.ai": "OpenRouter",
    "api.telegram.org": "Telegram",
    "graph.facebook.com": "Facebook",
    "api.hubspot.com": "HubSpot",
    "api.stripe.com": "Stripe",
    "hooks.slack.com": "Slack",
    "sheets.googleapis.com": "Google Sheets",
    "gmail.googleapis.com": "Gmail",
}

FUNCTIONAL_CLASS_BY_SUFFIX: dict[str, str] = {
    "manualTrigger": "trigger",
    "scheduleTrigger": "trigger",
    "webhook": "trigger",
    "formTrigger": "trigger",
    "telegramTrigger": "trigger",
    "gmailTrigger": "trigger",
    "googleSheetsTrigger": "trigger",
    "evaluationTrigger": "trigger",
    "set": "transform",
    "code": "code",
    "aggregate": "aggregate",
    "merge": "aggregate",
    "if": "branch",
    "switch": "branch",
    "filter": "branch",
    "wait": "delay",
    "httpRequest": "transport",
    "httpRequestTool": "transport",
    "emailSend": "transport",
    "postgres": "database",
    "mysql": "database",
    "mongodb": "database",
    "redis": "database",
    "googleSheets": "storage",
    "googleDrive": "storage",
    "googleDocs": "storage",
    "dataTable": "storage",
    "telegram": "publication",
    "gmail": "publication",
    "slack": "publication",
    "twitter": "publication",
    "facebookGraphApi": "publication",
    "wordpress": "publication",
    "instagram": "publication",
    "linkedin": "publication",
    "slackHitlTool": "human_review",
    "stickyNote": "other",
}


def sha256_bytes(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def normalize_name(name: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", " ", name, flags=re.UNICODE)
    return re.sub(r"\s+", " ", cleaned).strip()[:120]


def node_type_suffix(node_type: str) -> str:
    if "." in node_type:
        return node_type.rsplit(".", 1)[-1]
    return node_type


def extract_integrated_providers(
    nodes: list[dict[str, Any]],
    node_types: list[str],
    text: str,
    credential_refs: list[dict[str, str]],
) -> list[str]:
    providers: set[str] = set()
    for node_type in node_types:
        suffix = node_type_suffix(node_type)
        if suffix in NON_PROVIDER_NODE_SUFFIXES:
            continue
        mapped = PROVIDER_FROM_NODE_SUFFIX.get(suffix)
        if mapped:
            providers.add(mapped)
            continue
        lower = node_type.lower()
        if "langchain" in lower:
            for pattern, name in LANGCHAIN_PROVIDER_PATTERNS:
                if pattern in lower:
                    providers.add(name)
                    break
            else:
                providers.add("LangChain")
    for cred in credential_refs:
        mapped = PROVIDER_FROM_CREDENTIAL.get(cred.get("credential_type", ""))
        if mapped:
            providers.add(mapped)
    for url in extract_external_urls(text):
        try:
            host = urlparse(url).hostname or ""
        except ValueError:
            continue
        for suffix, name in HOSTNAME_PROVIDER.items():
            if host == suffix or host.endswith(f".{suffix}"):
                providers.add(name)
                break
    return sorted(providers)


def classify_functional_classes(node_types: list[str]) -> list[str]:
    classes: set[str] = set()
    for node_type in node_types:
        suffix = node_type_suffix(node_type)
        mapped = FUNCTIONAL_CLASS_BY_SUFFIX.get(suffix)
        if mapped:
            classes.add(mapped)
            continue
        lower = node_type.lower()
        if "trigger" in lower:
            classes.add("trigger")
        elif "langchain" in lower or "agent" in lower:
            classes.add("AI")
        elif "tool" in lower:
            classes.add("transform")
    return sorted(classes) or ["other"]


def assess_documentation_quality(nodes: list[dict[str, Any]], node_types: list[str]) -> str:
    sticky_nodes = [
        n
        for n in nodes
        if isinstance(n, dict) and "stickynote" in str(n.get("type", "")).lower()
    ]
    if not sticky_nodes:
        return "none"
    total_chars = 0
    for node in sticky_nodes:
        params = node.get("parameters") or {}
        if isinstance(params, dict):
            content = str(params.get("content") or params.get("note") or "")
            total_chars += len(content)
    if len(sticky_nodes) >= 3 or total_chars >= 500:
        return "substantial"
    if len(sticky_nodes) == 1 and total_chars < 80:
        return "minimal"
    return "present"


def redact_portable_text(text: str) -> str:
    redacted = ABS_PATH.sub("[PATH_REDACTED]", text)
    return SECRET_VALUE.sub("[REDACTED]", redacted)


def extract_credential_references(nodes: list[dict[str, Any]]) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        creds = node.get("credentials")
        if not isinstance(creds, dict):
            continue
        for cred_type, cred_val in creds.items():
            ref_id = "unknown"
            if isinstance(cred_val, dict):
                ref_id = str(cred_val.get("id", "unknown"))
            elif cred_val is not None:
                ref_id = str(cred_val)
            refs.append(
                {
                    "credential_type": str(cred_type),
                    "credential_id_ref": ref_id,
                    "node_name": str(node.get("name", "")),
                }
            )
    return refs


def extract_external_urls(text: str) -> list[str]:
    urls = re.findall(r"https?://[^\s\"'<>]+", text)
    return sorted({u.rstrip(".,)") for u in urls if "schemas.marketsynth.ai" not in u})[:20]


def side_effect_classes(
    *,
    publication: bool,
    billing: bool,
    destructive: bool,
    database: bool,
    messaging: bool,
) -> list[str]:
    effects: list[str] = []
    if publication:
        effects.append("publication")
    if billing:
        effects.append("billing")
    if destructive:
        effects.append("destructive")
    if database:
        effects.append("database_write")
    if messaging:
        effects.append("messaging")
    return effects
