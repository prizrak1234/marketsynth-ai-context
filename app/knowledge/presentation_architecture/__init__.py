"""KB-WPL-01.6 Presentation Architecture — non-executable validation."""

from __future__ import annotations

from app.knowledge.presentation_architecture.contracts import (
    SKILL_ID,
    SKILL_VERSION,
)
from app.knowledge.presentation_architecture.narrative import validate_narrative_arc
from app.knowledge.presentation_architecture.slide_rules import (
    validate_slide_plan,
    validate_slide_specification,
)
from app.knowledge.presentation_architecture.theme_rules import validate_theme_recommendation
from app.knowledge.presentation_architecture.validation import (
    validate_chart_requirement,
    validate_presentation_input,
    validate_presentation_output,
    validate_prohibited_claim,
)

__all__ = [
    "SKILL_ID",
    "SKILL_VERSION",
    "validate_chart_requirement",
    "validate_narrative_arc",
    "validate_presentation_input",
    "validate_presentation_output",
    "validate_prohibited_claim",
    "validate_slide_plan",
    "validate_slide_specification",
    "validate_theme_recommendation",
]
