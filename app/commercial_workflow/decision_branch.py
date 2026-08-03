"""Map evidence-backed verdict → commercial decision branch (CWF.1a)."""

from __future__ import annotations

from app.business_idea_validation.gap_presentation import (
    is_internal_gap_code,
    present_research_gaps,
)
from app.schemas.contracts import (
    BusinessIdeaValidationOutput,
    BusinessIdeaValidationVerdictKind,
    CommercialNextStepAction,
    VerdictDecisionBranch,
    VerdictDecisionCta,
)

LAUNCH_PACK_INCLUDED_KEYS: tuple[str, ...] = (
    "cwf.launchPack.included.audience",
    "cwf.launchPack.included.positioning",
    "cwf.launchPack.included.offer",
    "cwf.launchPack.included.launchPlan",
    "cwf.launchPack.included.telegramPosts",
    "cwf.launchPack.included.visuals",
    "cwf.launchPack.included.publicationPrep",
)

LAUNCH_PACK_EXCLUDED_KEYS: tuple[str, ...] = (
    "cwf.launchPack.excluded.paidAds",
    "cwf.launchPack.excluded.crm",
    "cwf.launchPack.excluded.salesAnalytics",
    "cwf.launchPack.excluded.multiChannel",
    "cwf.launchPack.excluded.videoExpansion",
)


def _customer_gap_messages(output: BusinessIdeaValidationOutput) -> list[str]:
    if output.research_gap_items:
        return [item.customer_message for item in output.research_gap_items]
    codes = list(output.research_gaps)
    if output.business_verdict_id is None and "business_verdict_missing" not in codes:
        codes.append("business_verdict_missing")
    return [item.customer_message for item in present_research_gaps(codes)]


def _explanation_from_output(output: BusinessIdeaValidationOutput) -> str:
    if output.findings:
        parts = [f"{f.title}: {f.statement}" for f in output.findings[:3]]
        return " ".join(parts)
    gap_messages = _customer_gap_messages(output)
    if gap_messages:
        return gap_messages[0]
    for limitation in output.limitations:
        if not is_internal_gap_code(limitation):
            return limitation
    return "Решение основано на собранных источниках и подтверждённых данных."


def _conditions_from_output(output: BusinessIdeaValidationOutput) -> list[str]:
    conditions: list[str] = []
    for risk in output.risks[:3]:
        text = f"{risk.title}: {risk.description}".strip()
        if text not in conditions:
            conditions.append(text[:500])
    for limitation in output.limitations[:2]:
        if is_internal_gap_code(limitation):
            continue
        if limitation not in conditions:
            conditions.append(limitation[:500])
    return conditions


def _scope_fields() -> dict[str, list[str]]:
    return {
        "launch_pack_included_keys": list(LAUNCH_PACK_INCLUDED_KEYS),
        "launch_pack_excluded_keys": list(LAUNCH_PACK_EXCLUDED_KEYS),
    }


def build_decision_branch(output: BusinessIdeaValidationOutput) -> VerdictDecisionBranch:
    explanation = _explanation_from_output(output)
    scope = _scope_fields()
    verdict = output.verdict

    if verdict == BusinessIdeaValidationVerdictKind.PROCEED:
        return VerdictDecisionBranch(
            verdict=verdict,
            headline_key="cwf.decision.proceed.headline",
            explanation=explanation,
            recommended_next_step_key="cwf.decision.proceed.recommended",
            launch_pack_allowed=True,
            conditions=[],
            primary_cta=VerdictDecisionCta(
                action=CommercialNextStepAction.PREPARE_LAUNCH,
                label_key="cwf.cta.prepareLaunch",
                is_primary=True,
            ),
            **scope,
        )

    if verdict == BusinessIdeaValidationVerdictKind.PROCEED_WITH_CONDITIONS:
        conditions = _conditions_from_output(output)
        return VerdictDecisionBranch(
            verdict=verdict,
            headline_key="cwf.decision.proceedWithConditions.headline",
            explanation=explanation,
            recommended_next_step_key="cwf.decision.proceedWithConditions.recommended",
            launch_pack_allowed=True,
            conditions=conditions,
            primary_cta=VerdictDecisionCta(
                action=CommercialNextStepAction.PREPARE_LAUNCH,
                label_key="cwf.cta.prepareLaunchWithConditions",
                is_primary=True,
                requires_conditions_acceptance=True,
            ),
            secondary_ctas=[
                VerdictDecisionCta(
                    action=CommercialNextStepAction.REFINE_INPUTS,
                    label_key="cwf.cta.refineInputs",
                ),
            ],
            **scope,
        )

    if verdict == BusinessIdeaValidationVerdictKind.REVISE:
        return VerdictDecisionBranch(
            verdict=verdict,
            headline_key="cwf.decision.revise.headline",
            explanation=explanation,
            recommended_next_step_key="cwf.decision.revise.recommended",
            launch_pack_allowed=False,
            conditions=_conditions_from_output(output),
            primary_cta=VerdictDecisionCta(
                action=CommercialNextStepAction.REVISE_IDEA,
                label_key="cwf.cta.reviseIdea",
                is_primary=True,
            ),
            secondary_ctas=[
                VerdictDecisionCta(
                    action=CommercialNextStepAction.REQUEST_ALTERNATIVE,
                    label_key="cwf.cta.requestAlternative",
                ),
                VerdictDecisionCta(
                    action=CommercialNextStepAction.PREPARE_LAUNCH,
                    label_key="cwf.cta.prepareLaunchDespiteRisk",
                    requires_risk_override=True,
                ),
            ],
            **scope,
        )

    if verdict == BusinessIdeaValidationVerdictKind.REJECT:
        return VerdictDecisionBranch(
            verdict=verdict,
            headline_key="cwf.decision.reject.headline",
            explanation=explanation,
            recommended_next_step_key="cwf.decision.reject.recommended",
            launch_pack_allowed=False,
            conditions=_conditions_from_output(output),
            primary_cta=VerdictDecisionCta(
                action=CommercialNextStepAction.REQUEST_ALTERNATIVE,
                label_key="cwf.cta.requestAlternative",
                is_primary=True,
            ),
            secondary_ctas=[
                VerdictDecisionCta(
                    action=CommercialNextStepAction.STOP_PROJECT,
                    label_key="cwf.cta.stopProject",
                ),
            ],
            **scope,
        )

    return VerdictDecisionBranch(
        verdict=BusinessIdeaValidationVerdictKind.INSUFFICIENT_EVIDENCE,
        headline_key="cwf.decision.insufficientEvidence.headline",
        explanation=explanation,
        recommended_next_step_key="cwf.decision.insufficientEvidence.recommended",
        launch_pack_allowed=False,
        conditions=[],
        primary_cta=VerdictDecisionCta(
            action=CommercialNextStepAction.REFINE_INPUTS,
            label_key="cwf.cta.refineInputs",
            is_primary=True,
        ),
        secondary_ctas=[
            VerdictDecisionCta(
                action=CommercialNextStepAction.REVISE_IDEA,
                label_key="cwf.cta.retryResearch",
            ),
        ],
        **scope,
    )


def launch_pack_allowed_for_action(
    branch: VerdictDecisionBranch,
    action: CommercialNextStepAction,
    *,
    accepted_conditions: list[str],
    override_reason: str | None,
) -> bool:
    if action != CommercialNextStepAction.PREPARE_LAUNCH:
        return False
    if branch.verdict == BusinessIdeaValidationVerdictKind.PROCEED:
        return True
    if branch.verdict == BusinessIdeaValidationVerdictKind.PROCEED_WITH_CONDITIONS:
        if not branch.conditions:
            return True
        return bool(accepted_conditions) and all(c in accepted_conditions for c in branch.conditions)
    if branch.verdict == BusinessIdeaValidationVerdictKind.REVISE:
        return bool(override_reason and override_reason.strip())
    return False
