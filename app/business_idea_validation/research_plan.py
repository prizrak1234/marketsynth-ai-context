"""Build research plan queries — PRODUCT-01.3B.2A delegates to query_strategy."""

from __future__ import annotations

from app.business_idea_validation.query_strategy import build_research_plan as _build_research_plan
from app.schemas.contracts import BusinessIdeaValidationInput, BusinessIdeaValidationResearchPlanItem


def requires_local_context(inp: BusinessIdeaValidationInput) -> bool:
    return bool((inp.location or "").strip())


def build_research_plan(inp: BusinessIdeaValidationInput) -> list[BusinessIdeaValidationResearchPlanItem]:
    return _build_research_plan(inp)
