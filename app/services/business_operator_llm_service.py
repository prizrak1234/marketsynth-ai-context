"""LLM fallback intent classification for Business Operator (Phase AI.199)."""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from app.core.config import get_settings
from app.core.exceptions import ExecutorError
from app.core.logging import get_logger
from app.domain.business_intent_analyzer import analyze_business_message
from app.domain.business_operator_clarifications import GOAL_OPTIONS, INDUSTRY_OPTIONS
from app.domain.business_operator_llm_merge import validate_llm_intent
from app.llm.contracts import LLMGenerateInput
from app.llm.registry import get_llm_adapter
from app.marketing.scenarios import SCENARIO_IDS
from app.prompts.business_operator import build_business_operator_messages
from app.schemas.contracts import BusinessOperatorLLMIntent, LLMProvider

log = get_logger(__name__)
_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


class BusinessOperatorLLMService:
    """Classify business intent via LLM when rule-based confidence is low."""

    async def classify_intent(
        self,
        message: str,
    ) -> tuple[BusinessOperatorLLMIntent | None, str, str]:
        """Return parsed intent, provider label, and model — never raw completion."""
        settings = get_settings()
        provider = self._resolve_provider(settings.default_llm_provider)
        model = settings.default_llm_model

        if provider == LLMProvider.MOCK:
            intent = self._mock_classify(message)
            return intent, provider.value, model

        adapter = get_llm_adapter(provider)
        output = await adapter.generate(
            LLMGenerateInput(
                provider=provider,
                model=model,
                messages=build_business_operator_messages(message),
                temperature=0.0,
                max_tokens=512,
                timeout_seconds=settings.llm_timeout_seconds,
                max_retries=settings.llm_max_retries,
                tools=None,
                metadata={"business_operator_intent": True},
            ),
        )
        intent = parse_llm_intent_json(output.content)
        if intent is None:
            log.info(
                "business_operator_llm_parse_failed",
                provider=provider.value,
                model=model,
            )
        return intent, provider.value, model

    @staticmethod
    def _resolve_provider(provider_name: str) -> LLMProvider:
        try:
            return LLMProvider(provider_name.lower())
        except ValueError as exc:
            raise ExecutorError(f"Unsupported LLM provider: {provider_name}") from exc

    @staticmethod
    def _mock_classify(message: str) -> BusinessOperatorLLMIntent | None:
        """Deterministic mock path — no external API, no tools."""
        normalized = " ".join(message.lower().split())
        analysis = analyze_business_message(message)
        rule = analysis.intent

        if "клиент" in normalized and analysis.industry_keyword_score == 0:
            return BusinessOperatorLLMIntent(
                goal="lead_generation",
                industry="local",
                business_type="local_service",
                campaign_type="lead_generation",
                suggested_scenario="local_service_promo",
                confidence=0.72,
                reasoning_summary=(
                    "Mock LLM inferred local service lead generation from a vague client request."
                ),
                missing_fields=[],
            )

        scenario = rule.recommended_scenario or "local_service_promo"
        confidence = max(rule.confidence, 0.70)
        return BusinessOperatorLLMIntent(
            goal=rule.goal,
            industry=rule.industry,
            business_type=rule.business_type,
            campaign_type=rule.campaign_type,
            suggested_scenario=scenario,
            confidence=round(min(1.0, confidence), 2),
            reasoning_summary="Mock LLM confirmed rule-based intent with higher confidence.",
            missing_fields=[],
        )


def parse_llm_intent_json(content: str) -> BusinessOperatorLLMIntent | None:
    """Parse and validate LLM JSON output — invalid output returns None."""
    stripped = content.strip()
    if not stripped:
        return None

    fence = _JSON_FENCE.search(stripped)
    if fence:
        stripped = fence.group(1).strip()

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    try:
        intent = BusinessOperatorLLMIntent.model_validate(payload)
    except ValidationError:
        return None

    if intent.suggested_scenario is not None and intent.suggested_scenario not in SCENARIO_IDS:
        return None
    if intent.industry is not None and intent.industry not in INDUSTRY_OPTIONS:
        return None
    if intent.goal not in GOAL_OPTIONS:
        return None

    if not validate_llm_intent(intent):
        return None

    return intent
