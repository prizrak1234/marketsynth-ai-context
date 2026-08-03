"""Workflow security static scan — structured findings, redacted values."""

from __future__ import annotations

import re
import uuid
from typing import Any

from app.knowledge.workflow_catalog.contracts import SecurityFindingRecord

RULES: list[tuple[str, str, str, str]] = [
    (r"sk-[a-zA-Z0-9]{20,}", "embedded_api_key", "secret", "critical"),
    (r"Bearer\s+[a-zA-Z0-9._\-]{10,}", "bearer_token", "secret", "critical"),
    (
        r"-----BEGIN (RSA |OPENSSH )?PRIVATE KEY-----",
        "private_key",
        "secret",
        "critical",
    ),
    (r"api[_-]?key\s*[:=]", "api_key_marker", "secret", "high"),
    (
        r"password\s*[:=]\s*['\"][^'\"]{3,}['\"]",
        "password_marker",
        "secret",
        "high",
    ),
    (r"oauth[_-]?token", "oauth_token_marker", "secret", "high"),
    (r"@\w+\.\w+", "email_address", "personal_data", "medium"),
    (r"\+?\d{10,15}", "phone_number", "personal_data", "medium"),
    (
        r"\b(DROP\s+TABLE|DELETE\s+FROM|TRUNCATE\s+TABLE)\b",
        "destructive_sql",
        "destructive",
        "critical",
    ),
    (r"rm\s+-rf|del\s+/f", "shell_delete", "destructive", "critical"),
    (r"https?://[^\s\"']+\{\{", "ssrf_dynamic_url", "network", "medium"),
    (
        r"prompt.*inject|ignore previous instructions",
        "prompt_injection_exposure",
        "ai",
        "medium",
    ),
]

COMMUNITY_PREFIX = "n8n-nodes-"
BASE_PREFIX = "n8n-nodes-base."
LANGCHAIN = "@n8n/n8n-nodes-langchain"


def _finding(
    workflow_id: str,
    code: str,
    severity: str,
    category: str,
    location: str,
    hint: str,
    archive_id: str,
) -> SecurityFindingRecord:
    finding_seed = f"{workflow_id}:{code}:{location}"
    finding_id = f"sf-{uuid.uuid5(uuid.NAMESPACE_URL, finding_seed).hex[:16]}"
    return SecurityFindingRecord(
        finding_id=finding_id,
        severity=severity,  # type: ignore[arg-type]
        finding_type=code,
        location=location,
        description=f"[{category}] {hint}",
        redacted=True,
        provenance={
            "source_type": "security_scan",
            "archive_id": archive_id,
            "source_id": workflow_id,
        },
    )


def scan_workflow(
    *,
    workflow_id: str,
    text: str,
    node_types: list[str],
    nodes: list[dict[str, Any]],
    archive_id: str,
) -> list[SecurityFindingRecord]:
    del nodes
    findings: list[SecurityFindingRecord] = []
    for pattern, code, category, severity in RULES:
        if re.search(pattern, text, re.IGNORECASE):
            findings.append(
                _finding(
                    workflow_id,
                    code,
                    severity,
                    category,
                    "workflow_body",
                    "Redact before reuse",
                    archive_id,
                )
            )
    for node_type in node_types:
        lower = node_type.lower()
        if "executecommand" in lower:
            findings.append(
                _finding(
                    workflow_id,
                    "shell_command_node",
                    "critical",
                    "execution",
                    node_type,
                    "No shell in catalog patterns",
                    archive_id,
                )
            )
        if "code" in lower and "n8n-nodes" in lower:
            findings.append(
                _finding(
                    workflow_id,
                    "code_node",
                    "high",
                    "execution",
                    node_type,
                    "Review code node logic manually",
                    archive_id,
                )
            )
        is_community = node_type.startswith(COMMUNITY_PREFIX)
        is_base = node_type.startswith(BASE_PREFIX)
        is_langchain = LANGCHAIN in node_type
        if is_community and not is_base and not is_langchain:
            findings.append(
                _finding(
                    workflow_id,
                    "community_node",
                    "medium",
                    "dependency",
                    node_type,
                    "Unknown community node",
                    archive_id,
                )
            )
    pub_types = (
        "telegram",
        "instagram",
        "facebook",
        "linkedin",
        "wordpress",
        "gmail",
        "twitter",
    )
    if any(any(item in node_type.lower() for item in pub_types) for node_type in node_types):
        findings.append(
            _finding(
                workflow_id,
                "publication_node",
                "high",
                "publication",
                "nodes",
                "Requires human approval",
                archive_id,
            )
        )
    if any(keyword in text.lower() for keyword in ("stripe", "payment", "billing", "paypal")):
        findings.append(
            _finding(
                workflow_id,
                "billing_action",
                "high",
                "billing",
                "workflow_body",
                "Requires spend approval",
                archive_id,
            )
        )
    if "credentials" in text.lower():
        findings.append(
            _finding(
                workflow_id,
                "credential_reference",
                "medium",
                "credential",
                "nodes",
                "Metadata only — never bind",
                archive_id,
            )
        )
    has_ai = any("langchain" in item.lower() or "agent" in item.lower() for item in node_types)
    if has_ai and re.search(r"html|http://|scrap", text, re.I):
        findings.append(
            _finding(
                workflow_id,
                "untrusted_content_to_llm",
                "medium",
                "ai",
                "workflow_body",
                "Validate untrusted input before LLM",
                archive_id,
            )
        )
    seen: set[tuple[str, str]] = set()
    unique: list[SecurityFindingRecord] = []
    for finding in findings:
        key = (finding.finding_type, finding.location)
        if key not in seen:
            seen.add(key)
            unique.append(finding)
    return sorted(unique, key=lambda item: item.finding_id)


def redact_secrets(text: str) -> str:
    redacted = text
    for pattern, *_ in RULES:
        redacted = re.sub(pattern, "[REDACTED]", redacted, flags=re.IGNORECASE)
    return redacted
