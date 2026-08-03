"""Map H1 UserRequest route categories to specialist skills."""

from __future__ import annotations

from app.schemas.contracts import (
    SkillRouteMapping,
    SpecialistSkillCode,
    UserRequestRouteCategory,
)
from app.specialist_skills.capability_packs import get_capability_pack
from app.specialist_skills.registry import get_skill

_ROUTE_MAP: dict[UserRequestRouteCategory, SkillRouteMapping] = {
    UserRequestRouteCategory.CONTENT: SkillRouteMapping(
        route_category=UserRequestRouteCategory.CONTENT,
        specialist_role="content_specialist",
        skill_code=SpecialistSkillCode.CONTENT_TELEGRAM_POST,
        requires_clarification_when_incomplete=True,
        notes="Default content.telegram_post; clarify when inputs missing.",
    ),
    UserRequestRouteCategory.CONTENT_PLAN: SkillRouteMapping(
        route_category=UserRequestRouteCategory.CONTENT_PLAN,
        specialist_role="content_planner",
        skill_code=SpecialistSkillCode.CONTENT_CONTENT_PLAN,
        requires_clarification_when_incomplete=True,
    ),
    UserRequestRouteCategory.SOCIAL_MEDIA: SkillRouteMapping(
        route_category=UserRequestRouteCategory.SOCIAL_MEDIA,
        specialist_role="content_specialist",
        skill_code=SpecialistSkillCode.CONTENT_SOCIAL_POST,
        requires_clarification_when_incomplete=True,
    ),
    UserRequestRouteCategory.YOUTUBE: SkillRouteMapping(
        route_category=UserRequestRouteCategory.YOUTUBE,
        specialist_role="content_specialist",
        skill_code=SpecialistSkillCode.CONTENT_YOUTUBE_SCRIPT,
        requires_clarification_when_incomplete=True,
    ),
    UserRequestRouteCategory.IMAGE_GENERATION: SkillRouteMapping(
        route_category=UserRequestRouteCategory.IMAGE_GENERATION,
        specialist_role="visual_specialist",
        skill_code=SpecialistSkillCode.DESIGN_IMAGE_GENERATION,
        requires_clarification_when_incomplete=True,
        notes="Execute only when IMAGE_GENERATION_ENABLED; no publication.",
    ),
    UserRequestRouteCategory.TELEGRAM_BOT: SkillRouteMapping(
        route_category=UserRequestRouteCategory.TELEGRAM_BOT,
        specialist_role="programmer",
        skill_code=SpecialistSkillCode.PROGRAMMER_TELEGRAM_BOT_SPEC,
        requires_clarification_when_incomplete=True,
    ),
    UserRequestRouteCategory.WEBSITE: SkillRouteMapping(
        route_category=UserRequestRouteCategory.WEBSITE,
        specialist_role="programmer",
        skill_code=SpecialistSkillCode.PROGRAMMER_WEBSITE_SPEC,
        requires_clarification_when_incomplete=True,
    ),
    UserRequestRouteCategory.AUTOMATION: SkillRouteMapping(
        route_category=UserRequestRouteCategory.AUTOMATION,
        specialist_role="programmer",
        skill_code=SpecialistSkillCode.PROGRAMMER_AUTOMATION_SPEC,
        requires_clarification_when_incomplete=True,
    ),
    UserRequestRouteCategory.MARKET_RESEARCH: SkillRouteMapping(
        route_category=UserRequestRouteCategory.MARKET_RESEARCH,
        specialist_role="researcher",
        skill_code=SpecialistSkillCode.RESEARCH_MARKET_OVERVIEW,
        requires_clarification_when_incomplete=True,
        notes="Skill mapping only; H1 may still use project intake path.",
    ),
    UserRequestRouteCategory.COMPETITOR_ANALYSIS: SkillRouteMapping(
        route_category=UserRequestRouteCategory.COMPETITOR_ANALYSIS,
        specialist_role="researcher",
        skill_code=SpecialistSkillCode.RESEARCH_COMPETITOR_ANALYSIS,
        requires_clarification_when_incomplete=True,
    ),
    UserRequestRouteCategory.MARKETING_STRATEGY: SkillRouteMapping(
        route_category=UserRequestRouteCategory.MARKETING_STRATEGY,
        specialist_role="strategist",
        skill_code=SpecialistSkillCode.STRATEGY_POSITIONING,
        requires_clarification_when_incomplete=True,
        domain_eligibility_required=True,
        notes="Strategy skill only when domain eligibility is satisfied.",
    ),
    UserRequestRouteCategory.IDEA_VALIDATION: SkillRouteMapping(
        route_category=UserRequestRouteCategory.IDEA_VALIDATION,
        specialist_role="researcher",
        skill_code=None,
        uses_existing_project_path=True,
        notes="Uses ProjectBrief/Investigation path — not a simple skill.",
    ),
    UserRequestRouteCategory.SAAS: SkillRouteMapping(
        route_category=UserRequestRouteCategory.SAAS,
        specialist_role="programmer",
        skill_code=None,
        uses_existing_project_path=True,
        notes="SaaS requires project intake; no single draft skill yet.",
    ),
    UserRequestRouteCategory.GENERAL: SkillRouteMapping(
        route_category=UserRequestRouteCategory.GENERAL,
        specialist_role=None,
        skill_code=None,
        requires_clarification_when_incomplete=True,
        notes="Clarify before skill assignment.",
    ),
    UserRequestRouteCategory.UNSUPPORTED: SkillRouteMapping(
        route_category=UserRequestRouteCategory.UNSUPPORTED,
        specialist_role=None,
        skill_code=None,
        notes="No skill.",
    ),
}


def list_route_mappings() -> list[SkillRouteMapping]:
    return list(_ROUTE_MAP.values())


def map_route_to_skill(category: UserRequestRouteCategory) -> SkillRouteMapping:
    return _ROUTE_MAP[category]


def resolve_skill_for_user_request_category(
    category: UserRequestRouteCategory,
) -> SpecialistSkillCode | None:
    mapping = map_route_to_skill(category)
    if mapping.uses_existing_project_path:
        return None
    if mapping.skill_code is None:
        return None
    skill = get_skill(mapping.skill_code)
    if skill is None:
        return None
    if mapping.specialist_role:
        pack = get_capability_pack(mapping.specialist_role)
        if pack is None or mapping.skill_code not in pack.allowed_skills:
            return None
    return mapping.skill_code
