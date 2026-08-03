"""Clarification contracts — do not execute when mandatory inputs are missing."""

from __future__ import annotations

from app.schemas.contracts import (
    SkillClarificationResult,
    SpecialistSkillCode,
)
from app.specialist_skills.registry import get_skill


def evaluate_clarification(
    skill_code: SpecialistSkillCode,
    provided: dict[str, str | None] | None = None,
) -> SkillClarificationResult:
    skill = get_skill(skill_code)
    if skill is None:
        return SkillClarificationResult(
            skill_code=skill_code,
            ready=False,
            missing_fields=["<unknown_skill>"],
            clarification_prompt="Unknown skill — cannot execute.",
        )
    provided = provided or {}
    missing: list[str] = []
    for field in skill.clarification_schema:
        value = provided.get(field)
        if value is None or not str(value).strip():
            missing.append(field)
    if missing:
        prompt = (
            "Для навыка "
            f"{skill.code.value} нужны уточнения: "
            + ", ".join(missing)
            + ". Не запускаю черновик, пока поля не заполнены."
        )
        return SkillClarificationResult(
            skill_code=skill_code,
            ready=False,
            missing_fields=missing,
            clarification_prompt=prompt,
        )
    return SkillClarificationResult(
        skill_code=skill_code,
        ready=True,
        missing_fields=[],
        clarification_prompt=None,
    )
