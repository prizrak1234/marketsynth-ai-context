"""Route marketing specialist execution by type (Phase AI.31+)."""

from __future__ import annotations

from app.agents.marketer.specialists.ad_creative_strategist import (
    execute_ad_creative_strategist_specialist,
)
from app.agents.marketer.specialists.analyst import execute_analyst_specialist
from app.agents.marketer.specialists.content_planner import execute_content_planner_specialist
from app.agents.marketer.specialists.copywriter import execute_copywriter_specialist
from app.agents.marketer.specialists.critic import execute_critic_specialist
from app.agents.marketer.specialists.cro_specialist import execute_cro_specialist
from app.agents.marketer.specialists.email_dm_specialist import execute_email_dm_specialist
from app.agents.marketer.specialists.funnel_architect import execute_funnel_architect_specialist
from app.agents.marketer.specialists.lead_magnet_specialist import execute_lead_magnet_specialist
from app.agents.marketer.specialists.offer_strategist import execute_offer_strategist_specialist
from app.agents.marketer.specialists.researcher import execute_researcher_specialist
from app.agents.marketer.specialists.sales_copywriter import execute_sales_copywriter_specialist
from app.agents.marketer.specialists.smm_strategist import execute_smm_strategist_specialist
from app.agents.marketer.specialists.strategist import execute_strategist_specialist
from app.core.exceptions import InvalidStateError
from app.schemas.contracts import (
    MarketingSpecialistExecutionInput,
    MarketingSpecialistExecutionOutput,
    MarketingSpecialistType,
)

_ENABLED_SPECIALISTS = frozenset(
    {
        MarketingSpecialistType.STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
        MarketingSpecialistType.CONTENT_PLANNER,
        MarketingSpecialistType.COPYWRITER,
        MarketingSpecialistType.CRITIC,
        MarketingSpecialistType.ANALYST,
        MarketingSpecialistType.OFFER_STRATEGIST,
        MarketingSpecialistType.FUNNEL_ARCHITECT,
        MarketingSpecialistType.LEAD_MAGNET_SPECIALIST,
        MarketingSpecialistType.SALES_COPYWRITER,
        MarketingSpecialistType.EMAIL_DM_SPECIALIST,
        MarketingSpecialistType.CRO_SPECIALIST,
        MarketingSpecialistType.SMM_STRATEGIST,
        MarketingSpecialistType.AD_CREATIVE_STRATEGIST,
    },
)


async def execute_marketing_specialist(
    data: MarketingSpecialistExecutionInput,
) -> MarketingSpecialistExecutionOutput:
    if data.specialist not in _ENABLED_SPECIALISTS:
        raise InvalidStateError("Specialist execution is not enabled for this role yet")
    if data.specialist == MarketingSpecialistType.STRATEGIST:
        return await execute_strategist_specialist(data)
    if data.specialist == MarketingSpecialistType.RESEARCHER:
        return await execute_researcher_specialist(data)
    if data.specialist == MarketingSpecialistType.CONTENT_PLANNER:
        return await execute_content_planner_specialist(data)
    if data.specialist == MarketingSpecialistType.COPYWRITER:
        return await execute_copywriter_specialist(data)
    if data.specialist == MarketingSpecialistType.CRITIC:
        return await execute_critic_specialist(data)
    if data.specialist == MarketingSpecialistType.ANALYST:
        return await execute_analyst_specialist(data)
    if data.specialist == MarketingSpecialistType.OFFER_STRATEGIST:
        return await execute_offer_strategist_specialist(data)
    if data.specialist == MarketingSpecialistType.FUNNEL_ARCHITECT:
        return await execute_funnel_architect_specialist(data)
    if data.specialist == MarketingSpecialistType.LEAD_MAGNET_SPECIALIST:
        return await execute_lead_magnet_specialist(data)
    if data.specialist == MarketingSpecialistType.SALES_COPYWRITER:
        return await execute_sales_copywriter_specialist(data)
    if data.specialist == MarketingSpecialistType.EMAIL_DM_SPECIALIST:
        return await execute_email_dm_specialist(data)
    if data.specialist == MarketingSpecialistType.CRO_SPECIALIST:
        return await execute_cro_specialist(data)
    if data.specialist == MarketingSpecialistType.SMM_STRATEGIST:
        return await execute_smm_strategist_specialist(data)
    return await execute_ad_creative_strategist_specialist(data)
