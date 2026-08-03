"""Scenario wizard step order (Phase AI.138)."""

from __future__ import annotations

SCENARIO_WIZARD_STEPS: tuple[str, ...] = (
    "create_plan",
    "approve_plan",
    "create_execution_run",
    "execute_specialists",
    "approve_copywriter_output",
    "create_content_asset",
    "submit_asset",
    "approve_asset",
    "create_media_brief",
    "submit_media_brief",
    "approve_media_brief",
    "create_publication_package",
    "submit_package",
    "approve_package",
    "create_dry_run_job",
)

SCENARIO_WIZARD_FIRST_STEP = SCENARIO_WIZARD_STEPS[0]
SCENARIO_WIZARD_LAST_STEP = SCENARIO_WIZARD_STEPS[-1]


def next_wizard_step(current_step: str) -> str | None:
    try:
        index = SCENARIO_WIZARD_STEPS.index(current_step)
    except ValueError:
        return None
    if index + 1 >= len(SCENARIO_WIZARD_STEPS):
        return None
    return SCENARIO_WIZARD_STEPS[index + 1]


def wizard_step_index(step: str) -> int:
    return SCENARIO_WIZARD_STEPS.index(step)
