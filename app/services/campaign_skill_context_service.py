"""Merge skill run outputs into campaign and plan context (Phase AI.240–AI.241)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import sanitize_payload
from app.db.base import utc_now
from app.db.models.campaign import CampaignTable
from app.db.models.marketing_skill_run import MarketingSkillRunTable
from app.db.repositories.marketing_plans import MarketingPlanRepository
from app.schemas.contracts import CampaignSkillContext, MarketingSkillRunStatus, MarketingSkillType
from app.services.campaign_layer_service import CampaignLayerService, campaign_id_in_context
from app.services.transaction import transactional

_SUMMARY_KEYS = (
    "segment_summary",
    "offer_summary",
    "demand_summary",
    "analytics_summary",
)


class CampaignSkillContextService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._layer = CampaignLayerService(session)
        self._plans = MarketingPlanRepository(session)

    @staticmethod
    def parse_context(metadata: dict[str, Any] | None) -> CampaignSkillContext | None:
        raw = (metadata or {}).get("skill_context")
        if not isinstance(raw, dict):
            return None
        try:
            return CampaignSkillContext.model_validate(raw)
        except Exception:
            return None

    @staticmethod
    def _safe_summary_from_output(
        skill_type: MarketingSkillType,
        output: dict[str, Any],
    ) -> tuple[str, dict[str, Any]] | None:
        if skill_type == MarketingSkillType.SEGMENT_RESEARCH:
            return "segment_summary", sanitize_payload(
                {
                    "headline": output.get("desired_state"),
                    "pains": (output.get("pains") or [])[:5],
                    "desires": (output.get("desires") or [])[:5],
                    "research_questions": (output.get("research_questions") or [])[:5],
                },
            ) or {}

        if skill_type in {
            MarketingSkillType.MEANING_UNPACKING,
            MarketingSkillType.OFFER_PACKAGING,
            MarketingSkillType.OFFER_JUSTIFICATION,
            MarketingSkillType.VISUAL_REPORT,
        }:
            payload: dict[str, Any] = {"skill_type": skill_type.value}
            if skill_type == MarketingSkillType.MEANING_UNPACKING:
                payload["promise_formulations"] = (output.get("promise_formulations") or [])[:3]
            elif skill_type == MarketingSkillType.OFFER_PACKAGING:
                payload["core_thesis"] = output.get("core_thesis")
                payload["measurable_result"] = output.get("measurable_result")
            elif skill_type == MarketingSkillType.OFFER_JUSTIFICATION:
                payload["final_cta"] = output.get("final_cta")
                payload["target_fit"] = output.get("target_fit")
            else:
                payload["report_title"] = output.get("report_title")
                payload["business_conclusion"] = output.get("business_conclusion")
            return "offer_summary", sanitize_payload(payload) or {}

        if skill_type == MarketingSkillType.WORDSTAT_RESEARCH:
            summary = output.get("wordstat_summary")
            if isinstance(summary, dict) and "rows" in summary:
                summary = {"provider": summary.get("provider"), "query": summary.get("query")}
            return "demand_summary", sanitize_payload(
                {
                    "business_conclusion": output.get("business_conclusion"),
                    "demand_signal": output.get("demand_signal"),
                    "query": output.get("query"),
                    "wordstat": summary,
                },
            ) or {}

        if skill_type == MarketingSkillType.METRICA_ANALYSIS:
            summary = output.get("metrica_summary")
            if isinstance(summary, dict):
                summary = {
                    "provider": summary.get("provider"),
                    "metrics": summary.get("metrics"),
                    "row_count": len(summary.get("data") or []),
                }
            return "analytics_summary", sanitize_payload(
                {
                    "business_conclusion": output.get("business_conclusion"),
                    "focus_metrics": output.get("focus_metrics"),
                    "metrica": summary,
                },
            ) or {}

        return None

    async def apply_successful_run(self, run: MarketingSkillRunTable) -> None:
        if run.campaign_id is None or run.status != MarketingSkillRunStatus.SUCCEEDED:
            return
        campaign = await self._layer.get(run.owner_id, run.project_id, run.campaign_id)
        if campaign is None:
            return

        output = dict(run.output_payload or {})
        output["provenance"] = sanitize_payload(
            {
                "campaign_id": str(run.campaign_id),
                "skill_run_id": str(run.id),
                "skill_type": run.skill_type.value,
            },
        ) or {}
        run.output_payload = output

        parsed = self.parse_context(campaign.campaign_metadata) or CampaignSkillContext()
        mapping = self._safe_summary_from_output(run.skill_type, output)
        if mapping is not None:
            key, summary = mapping
            setattr(parsed, key, summary)
            parsed.source_run_ids[key] = str(run.id)
        parsed.updated_at = utc_now()

        metadata = dict(campaign.campaign_metadata or {})
        skill_context_payload = parsed.model_dump(mode="json")
        # ISO datetimes are mangled by PII sanitize_text (YYYY-MM-DD → [PHONE]).
        skill_context_payload.pop("updated_at", None)
        metadata["skill_context"] = skill_context_payload
        async with transactional(self._session):
            await self._layer.update(
                run.owner_id,
                run.project_id,
                run.campaign_id,
                {"metadata": metadata},
            )

        await self._sync_linked_plans(run.owner_id, run.project_id, run.campaign_id, parsed)

    async def _sync_linked_plans(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
        context: CampaignSkillContext,
    ) -> None:
        summaries = self.safe_summaries_for_plan(context)
        if not summaries:
            return
        plans = await self._plans.list_by_project(owner_id, project_id, limit=200)
        for plan in plans:
            if not campaign_id_in_context(plan.project_context, campaign_id):
                continue
            project_context = dict(plan.project_context or {})
            project_context["campaign_skill_summaries"] = summaries
            plan.project_context = project_context
            async with transactional(self._session):
                await self._plans.update(plan)

    @staticmethod
    def safe_summaries_for_plan(context: CampaignSkillContext | None) -> dict[str, Any]:
        if context is None:
            return {}
        payload: dict[str, Any] = {}
        for key in _SUMMARY_KEYS:
            value = getattr(context, key, None)
            if value:
                payload[key] = value
        if context.source_run_ids:
            payload["source_run_ids"] = dict(context.source_run_ids)
        return sanitize_payload(payload) or {}

    @staticmethod
    def skill_context_from_campaign(campaign: CampaignTable) -> CampaignSkillContext | None:
        return CampaignSkillContextService.parse_context(campaign.campaign_metadata)
