"""Safe intent audit logging for Business Operator (Phase AI.193, AI.201)."""

from __future__ import annotations

import hashlib

from app.core.logging import get_logger
from app.core.security import sanitize_text
from app.schemas.contracts import BusinessIntent, BusinessOperatorIntentSource

log = get_logger(__name__)
_MESSAGE_PREVIEW_MAX = 80


def build_intent_audit_id(intent: BusinessIntent, scenario_id: str) -> str:
    """Stable hash from intent fields — not from raw user message."""
    payload = (
        f"{intent.goal}|{intent.industry}|{intent.business_type}|"
        f"{intent.confidence}|{scenario_id}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def build_message_preview(message: str) -> str:
    """Sanitized short preview only — never log full raw prompt."""
    cleaned = sanitize_text(message).strip()
    if len(cleaned) <= _MESSAGE_PREVIEW_MAX:
        return cleaned
    return f"{cleaned[: _MESSAGE_PREVIEW_MAX - 3]}..."


def log_business_operator_intent_audit(
    *,
    intent_audit_id: str,
    intent: BusinessIntent,
    scenario_id: str,
    confidence_gate_passed: bool,
    message_preview: str = "",
    action: str,
    source: BusinessOperatorIntentSource = BusinessOperatorIntentSource.RULE_BASED,
    confidence_before: float | None = None,
    confidence_after: float | None = None,
    llm_used: bool = False,
    llm_provider: str | None = None,
    llm_model: str | None = None,
) -> None:
    log.info(
        "business_operator_intent_audit",
        action=action,
        intent_audit_id=intent_audit_id,
        goal=intent.goal,
        industry=intent.industry,
        confidence=intent.confidence,
        scenario=scenario_id,
        selected_scenario=scenario_id,
        confidence_gate_passed=confidence_gate_passed,
        message_preview=message_preview,
        source=source.value,
        confidence_before=confidence_before if confidence_before is not None else intent.confidence,
        confidence_after=confidence_after if confidence_after is not None else intent.confidence,
        llm_used=llm_used,
        llm_provider=llm_provider,
        llm_model=llm_model,
    )
