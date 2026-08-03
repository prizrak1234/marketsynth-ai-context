"""General Business Operator orchestration (Phase AI.180–AI.213)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.mappers import campaign_to_contract
from app.core.config import get_settings
from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_payload, sanitize_text
from app.domain.business_intent_analyzer import analyze_business_message, campaign_name_for_scenario
from app.domain.business_operator_clarifications import (
    apply_clarification_answers,
    build_clarification_questions,
)
from app.domain.business_operator_explanation import (
    build_campaign_preview,
    build_scenario_explanation,
)
from app.domain.business_operator_llm_merge import (
    ResolvedBusinessIntent,
    resolve_clarification,
    resolve_llm_fallback,
    resolve_rule_based,
    validate_llm_intent,
)
from app.domain.campaign_brief_completeness import evaluate_brief_completeness
from app.domain.campaign_brief_draft import build_brief_draft
from app.domain.marketing_tool_recommendations import build_tool_suggestions
from app.marketing.scenarios import get_scenario
from app.schemas.contracts import (
    BusinessIntent,
    BusinessOperatorAnalyzeResponse,
    BusinessOperatorBriefConfirmResponse,
    BusinessOperatorBriefResponse,
    BusinessOperatorCampaignPreview,
    BusinessOperatorClarification,
    BusinessOperatorClarifyResponse,
    BusinessOperatorCreateCampaignResponse,
    BusinessOperatorIntentSource,
    CampaignBriefCompleteness,
    CampaignBriefFields,
    CampaignStatus,
    ScenarioExplanation,
    ScenarioRecommendation,
)
from app.services.business_operator_audit import (
    build_intent_audit_id,
    build_message_preview,
    log_business_operator_intent_audit,
)
from app.services.business_operator_llm_service import BusinessOperatorLLMService
from app.services.business_scenario_recommendation_service import recommend_scenario
from app.services.campaign_brief_service import CampaignBriefService, campaign_brief_to_contract
from app.services.campaign_control_center_service import CampaignControlCenterService
from app.services.campaign_layer_service import CampaignLayerService
from app.services.projects_service import ProjectService

_MESSAGE_MAX = 4096


@dataclass(frozen=True, slots=True)
class _AssistBundle:
    intent: BusinessIntent
    recommended_scenario: str
    recommended_campaign_name: str
    recommendation: ScenarioRecommendation
    confidence_threshold: float
    confidence_gate_passed: bool
    clarification_questions: list[BusinessOperatorClarification]
    explanation: ScenarioExplanation | None
    preview: BusinessOperatorCampaignPreview | None
    intent_audit_id: str
    message_preview: str
    source: BusinessOperatorIntentSource
    confidence_before: float
    confidence_after: float
    llm_used: bool
    llm_provider: str | None
    llm_model: str | None
    brief_draft: CampaignBriefFields
    brief_completeness: CampaignBriefCompleteness


class BusinessOperatorService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._campaigns = CampaignLayerService(session)
        self._control_center = CampaignControlCenterService(session)
        self._projects = ProjectService(session)
        self._llm = BusinessOperatorLLMService()
        self._briefs = CampaignBriefService(session)

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    @staticmethod
    def _confidence_threshold() -> float:
        return get_settings().business_operator_confidence_threshold

    @staticmethod
    def _sanitize_message(message: str) -> str:
        cleaned = sanitize_text(message).strip()[:_MESSAGE_MAX]
        if not cleaned:
            raise ValueError("Message must not be empty")
        return cleaned

    async def _resolve_intent(self, message: str) -> ResolvedBusinessIntent:
        """Rule-based primary; optional LLM fallback when confidence is low."""
        analysis = analyze_business_message(message)
        threshold = self._confidence_threshold()

        if analysis.intent.confidence >= threshold:
            return resolve_rule_based(analysis)

        settings = get_settings()
        if not settings.business_operator_llm_fallback_enabled:
            return resolve_clarification(analysis)

        llm_intent, provider, model = await self._llm.classify_intent(message)
        if llm_intent is None or not validate_llm_intent(llm_intent):
            return resolve_clarification(analysis)

        min_accept = settings.business_operator_llm_min_confidence_to_accept
        if (
            llm_intent.confidence >= min_accept
            and llm_intent.confidence > analysis.intent.confidence
        ):
            return resolve_llm_fallback(
                analysis,
                llm_intent,
                llm_provider=provider,
                llm_model=model,
            )

        return resolve_clarification(analysis)

    def _build_assist_bundle(
        self,
        resolved: ResolvedBusinessIntent,
        *,
        message: str | None = None,
        audit_action: str,
    ) -> _AssistBundle:
        intent = resolved.intent
        recommendation = recommend_scenario(intent)
        intent = intent.model_copy(
            update={"recommended_scenario": recommendation.recommended_scenario},
        )
        scenario_id = recommendation.recommended_scenario
        campaign_name = campaign_name_for_scenario(scenario_id)
        threshold = self._confidence_threshold()
        gate_passed = intent.confidence >= threshold

        clarifications: list[BusinessOperatorClarification] = []
        explanation: ScenarioExplanation | None = None
        preview: BusinessOperatorCampaignPreview | None = None

        if gate_passed:
            explanation = build_scenario_explanation(
                intent,
                recommendation,
                campaign_name=campaign_name,
            )
            preview = build_campaign_preview(scenario_id, campaign_name)
        else:
            clarifications = build_clarification_questions(
                intent,
                industry_keyword_score=resolved.industry_keyword_score,
                goal_keyword_score=resolved.goal_keyword_score,
            )

        audit_id = build_intent_audit_id(intent, scenario_id)
        preview_text = build_message_preview(message) if message else ""
        brief_draft = build_brief_draft(
            intent,
            scenario_id=scenario_id,
            message=message or "",
        )
        brief_completeness = evaluate_brief_completeness(brief_draft)
        log_business_operator_intent_audit(
            intent_audit_id=audit_id,
            intent=intent,
            scenario_id=scenario_id,
            confidence_gate_passed=gate_passed,
            message_preview=preview_text,
            action=audit_action,
            source=resolved.source,
            confidence_before=resolved.confidence_before,
            confidence_after=resolved.confidence_after,
            llm_used=resolved.llm_used,
            llm_provider=resolved.llm_provider,
            llm_model=resolved.llm_model,
        )

        return _AssistBundle(
            intent=intent,
            recommended_scenario=scenario_id,
            recommended_campaign_name=campaign_name,
            recommendation=recommendation,
            confidence_threshold=threshold,
            confidence_gate_passed=gate_passed,
            clarification_questions=clarifications,
            explanation=explanation,
            preview=preview,
            intent_audit_id=audit_id,
            message_preview=preview_text,
            source=resolved.source,
            confidence_before=resolved.confidence_before,
            confidence_after=resolved.confidence_after,
            llm_used=resolved.llm_used,
            llm_provider=resolved.llm_provider,
            llm_model=resolved.llm_model,
            brief_draft=brief_draft,
            brief_completeness=brief_completeness,
        )

    @staticmethod
    def _brief_response(
        bundle: _AssistBundle,
    ) -> dict[str, Any]:
        return {
            "brief_draft": bundle.brief_draft,
            "brief_completeness": bundle.brief_completeness,
        }

    @staticmethod
    def _assist_response_fields(bundle: _AssistBundle) -> dict[str, Any]:
        return {
            "confidence_threshold": bundle.confidence_threshold,
            "confidence_gate_passed": bundle.confidence_gate_passed,
            "clarification_questions": bundle.clarification_questions,
            "explanation": bundle.explanation,
            "preview": bundle.preview,
            "intent_audit_id": bundle.intent_audit_id,
            "message_preview": bundle.message_preview,
            "source": bundle.source,
            "confidence_before": bundle.confidence_before,
            "confidence_after": bundle.confidence_after,
            "llm_used": bundle.llm_used,
            "llm_provider": bundle.llm_provider,
            "llm_model": bundle.llm_model,
            "tool_suggestions": build_tool_suggestions(
                bundle.intent,
                brief=bundle.brief_draft,
            ),
            **BusinessOperatorService._brief_response(bundle),
        }

    @staticmethod
    def _to_analyze_response(bundle: _AssistBundle) -> BusinessOperatorAnalyzeResponse:
        return BusinessOperatorAnalyzeResponse(
            intent=bundle.intent,
            recommended_scenario=bundle.recommended_scenario,
            recommended_campaign_name=bundle.recommended_campaign_name,
            recommendation=bundle.recommendation,
            **BusinessOperatorService._assist_response_fields(bundle),
        )

    @staticmethod
    def _to_clarify_response(bundle: _AssistBundle) -> BusinessOperatorClarifyResponse:
        return BusinessOperatorClarifyResponse(
            intent=bundle.intent,
            recommended_scenario=bundle.recommended_scenario,
            recommended_campaign_name=bundle.recommended_campaign_name,
            recommendation=bundle.recommendation,
            **BusinessOperatorService._assist_response_fields(bundle),
        )

    @staticmethod
    def _resolved_from_clarified_intent(
        previous: BusinessIntent,
        updated: BusinessIntent,
    ) -> ResolvedBusinessIntent:
        return ResolvedBusinessIntent(
            intent=updated,
            source=(
                BusinessOperatorIntentSource.RULE_BASED
                if updated.confidence >= get_settings().business_operator_confidence_threshold
                else BusinessOperatorIntentSource.CLARIFICATION
            ),
            confidence_before=previous.confidence,
            confidence_after=updated.confidence,
            industry_keyword_score=1,
            goal_keyword_score=1,
        )

    @staticmethod
    def _resolved_from_explicit_intent(intent: BusinessIntent) -> ResolvedBusinessIntent:
        confidence = intent.confidence
        return ResolvedBusinessIntent(
            intent=intent,
            source=BusinessOperatorIntentSource.RULE_BASED,
            confidence_before=confidence,
            confidence_after=confidence,
            industry_keyword_score=1,
            goal_keyword_score=1,
        )

    async def analyze(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        message: str,
    ) -> BusinessOperatorAnalyzeResponse | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        cleaned = self._sanitize_message(message)
        resolved = await self._resolve_intent(cleaned)
        bundle = self._build_assist_bundle(
            resolved,
            message=cleaned,
            audit_action="analyze",
        )
        return self._to_analyze_response(bundle)

    async def clarify(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        previous_intent: BusinessIntent,
        answers: dict[str, str],
    ) -> BusinessOperatorClarifyResponse | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        sanitized_answers = {
            key: sanitize_text(value).strip()
            for key, value in answers.items()
            if value.strip()
        }
        if not sanitized_answers:
            raise ValueError("At least one clarification answer is required")

        updated_intent = apply_clarification_answers(previous_intent, sanitized_answers)
        resolved = self._resolved_from_clarified_intent(previous_intent, updated_intent)
        bundle = self._build_assist_bundle(resolved, audit_action="clarify")
        return self._to_clarify_response(bundle)

    async def complete_brief(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        intent: BusinessIntent,
        recommended_scenario: str,
        brief: CampaignBriefFields,
        answers: dict[str, str] | None = None,
    ) -> BusinessOperatorBriefResponse | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        sanitized, completeness = self._briefs.complete_brief(
            intent=intent,
            scenario_id=recommended_scenario,
            brief=brief,
            answers=answers,
        )
        return BusinessOperatorBriefResponse(
            brief_draft=sanitized,
            brief_completeness=completeness,
            intent=intent,
            recommended_scenario=recommended_scenario,
            recommended_campaign_name=campaign_name_for_scenario(recommended_scenario),
        )

    async def confirm_brief(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        intent: BusinessIntent,
        recommended_scenario: str,
        brief: CampaignBriefFields,
    ) -> BusinessOperatorBriefConfirmResponse | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        self._assert_confidence_gate(intent)
        row = await self._briefs.confirm_brief(
            owner_id,
            project_id,
            intent=intent,
            scenario_id=recommended_scenario,
            brief=brief,
        )
        if row is None:
            return None
        sanitized, completeness = self._briefs.complete_brief(
            intent=intent,
            scenario_id=recommended_scenario,
            brief=brief,
        )
        return BusinessOperatorBriefConfirmResponse(
            brief_draft=sanitized,
            brief_completeness=completeness,
            intent=intent,
            recommended_scenario=recommended_scenario,
            recommended_campaign_name=campaign_name_for_scenario(recommended_scenario),
            brief=campaign_brief_to_contract(row),
        )

    @staticmethod
    def _assert_confidence_gate(intent: BusinessIntent) -> None:
        threshold = get_settings().business_operator_confidence_threshold
        if intent.confidence < threshold:
            raise InvalidStateError("business_operator_confidence_gate")

    @staticmethod
    def _assert_brief_completeness(completeness: CampaignBriefCompleteness) -> None:
        if not completeness.passed:
            raise InvalidStateError("campaign_brief_completeness_gate")

    @staticmethod
    def _intent_metadata(
        intent: BusinessIntent,
        recommendation: ScenarioRecommendation,
        *,
        brief_id: UUID | None = None,
    ) -> dict[str, Any]:
        payload = sanitize_payload(
            {
                "goal": intent.goal,
                "industry": intent.industry,
                "business_type": intent.business_type,
                "campaign_type": intent.campaign_type,
                "confidence": intent.confidence,
                "recommended_scenario": recommendation.recommended_scenario,
                "alternative_scenarios": recommendation.alternative_scenarios,
                "reason": recommendation.reason,
            },
        )
        metadata: dict[str, Any] = {"source_business_intent": payload or {}}
        if brief_id is not None:
            metadata["source_campaign_brief_id"] = str(brief_id)
        return metadata

    async def _create_from_bundle(
        self,
        owner_id: UUID,
        project_id: UUID,
        bundle: _AssistBundle,
        *,
        brief_id: UUID,
        fallback_goal: str | None = None,
    ) -> BusinessOperatorCreateCampaignResponse | None:
        brief_row = await self._briefs.get_confirmed_brief(owner_id, project_id, brief_id)
        if brief_row is None:
            raise InvalidStateError("campaign_brief_not_confirmed")
        threshold = get_settings().campaign_brief_completeness_threshold
        if brief_row.completeness_score < threshold:
            raise InvalidStateError("campaign_brief_completeness_gate")

        self._assert_confidence_gate(bundle.intent)
        scenario_id = bundle.recommended_scenario
        template = get_scenario(scenario_id)
        goal_text = template.goal if template is not None else (fallback_goal or bundle.intent.goal)

        row = await self._campaigns.create(
            owner_id,
            project_id,
            name=bundle.recommended_campaign_name,
            goal=goal_text,
            scenario_id=scenario_id,
            status=CampaignStatus.DRAFT,
            metadata=self._intent_metadata(
                bundle.intent,
                bundle.recommendation,
                brief_id=brief_id,
            ),
        )
        if row is None:
            return None

        await self._briefs.link_to_campaign(brief_row, row.id)

        campaign = campaign_to_contract(row)
        control_center = await self._control_center.get_control_center(
            owner_id,
            project_id,
            row.id,
        )
        if control_center is None:
            return None

        log_business_operator_intent_audit(
            intent_audit_id=bundle.intent_audit_id,
            intent=bundle.intent,
            scenario_id=scenario_id,
            confidence_gate_passed=True,
            message_preview=bundle.message_preview,
            action="create_campaign",
            source=bundle.source,
            confidence_before=bundle.confidence_before,
            confidence_after=bundle.confidence_after,
            llm_used=bundle.llm_used,
            llm_provider=bundle.llm_provider,
            llm_model=bundle.llm_model,
        )

        return BusinessOperatorCreateCampaignResponse(
            campaign=campaign,
            intent=bundle.intent,
            recommendation=bundle.recommendation,
            control_center=control_center,
        )

    async def create_campaign(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        message: str | None = None,
        intent: BusinessIntent | None = None,
        brief_id: UUID,
    ) -> BusinessOperatorCreateCampaignResponse | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        if intent is not None:
            resolved = self._resolved_from_explicit_intent(intent)
            bundle = self._build_assist_bundle(
                resolved,
                audit_action="create_campaign_precheck",
            )
            return await self._create_from_bundle(
                owner_id,
                project_id,
                bundle,
                brief_id=brief_id,
            )

        if message is None:
            raise ValueError("message or intent is required")

        cleaned = self._sanitize_message(message)
        resolved = await self._resolve_intent(cleaned)
        bundle = self._build_assist_bundle(
            resolved,
            message=cleaned,
            audit_action="create_campaign_precheck",
        )
        return await self._create_from_bundle(
            owner_id,
            project_id,
            bundle,
            brief_id=brief_id,
            fallback_goal=cleaned,
        )
