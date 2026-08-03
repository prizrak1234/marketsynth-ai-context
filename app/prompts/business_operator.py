"""Business Operator LLM prompts (Phase AI.198)."""

from __future__ import annotations

import json

from app.llm.contracts import LLMMessage
from app.marketing.scenarios import SCENARIO_IDS

_ALLOWED_GOALS = ("lead_generation", "launch", "content", "promo")
_ALLOWED_INDUSTRIES = ("dental", "restaurant", "expert", "saas", "local")

_SYSTEM_INTRO = (
    "You classify business intent ONLY for BotFazer Business Operator."
)

_BUSINESS_OPERATOR_SYSTEM_PROMPT = f"""{_SYSTEM_INTRO}

Rules:
- Classify intent only — do NOT create campaigns, marketing plans, or execution steps.
- Return JSON only — no markdown, no prose outside JSON.
- Use only allowed scenarios: {", ".join(SCENARIO_IDS)}.
- Use goal values: {", ".join(_ALLOWED_GOALS)}.
- Use industry values: {", ".join(_ALLOWED_INDUSTRIES)}.
- confidence must be between 0.0 and 1.0.
- missing_fields lists unresolved fields (e.g. industry, goal) when uncertain.

JSON schema:
{{
  "goal": "lead_generation|launch|content|promo",
  "industry": "dental|restaurant|expert|saas|local|null",
  "business_type": "string|null",
  "campaign_type": "string|null",
  "suggested_scenario": "one of allowed scenarios|null",
  "confidence": 0.0,
  "reasoning_summary": "short explanation",
  "missing_fields": ["industry"]
}}
"""


def build_business_operator_messages(message: str) -> list[LLMMessage]:
    """Build system + user messages for intent classification."""
    return [
        LLMMessage(role="system", content=_BUSINESS_OPERATOR_SYSTEM_PROMPT),
        LLMMessage(
            role="user",
            content=(
                "Classify this business request:\n"
                f"{message}\n\n"
                "Respond with JSON only."
            ),
        ),
    ]


def business_operator_json_schema_hint() -> str:
    """Compact schema hint for mock/testing."""
    return json.dumps(
        {
            "goal": "lead_generation",
            "industry": "dental",
            "suggested_scenario": "dental_clinic_lead_gen",
            "confidence": 0.8,
            "reasoning_summary": "example",
            "missing_fields": [],
        },
    )
