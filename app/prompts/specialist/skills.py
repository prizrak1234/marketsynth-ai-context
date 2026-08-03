"""Skill instruction + output contract layer (Phase H2.7).

Only content.telegram_post is fully specified for slice 1 execution.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SkillInstruction(BaseModel):
    skill_code: str
    instruction_version: str
    output_schema_version: str
    quality_profile_version: str
    instruction_text: str
    output_schema_json: str
    quality_gates: list[str] = Field(default_factory=list)
    expertise_labels: list[str] = Field(default_factory=list)


_TELEGRAM_OUTPUT_SCHEMA = """\
{
  "hook": "string",
  "body": "string",
  "cta": "string",
  "variants": ["string"],
  "assumptions": ["string"],
  "factual_claims": ["string"],
  "warnings": ["string"]
}"""

_TELEGRAM_INSTRUCTION = """\
Write a single Telegram post draft for the given topic, audience and objective.

Structure (professional Telegram expert post):
1. Strong hook — concrete operational angle, not a cliché.
2. Body — operational context, 2–4 concrete examples (weak signals, trends, crew
   observations, parameter deviations). Use domain knowledge from approved materials.
3. Practical implication for supervisors.
4. ONE final CTA or discussion question — place it ONLY in the "cta" field, never
   repeat the same question in the body.

Requirements:
- Match audience vocabulary (e.g. drilling supervisors: torque, drag, flow check,
  near miss, shift handover — when domain-appropriate).
- Do NOT invent statistics, percentages, regulations, or named standards.
- Do NOT use filler: "В современном мире", "Важно понимать", "не просто рекомендация".
- List assumptions in assumptions; declare factual_claims only for verifiable claims.
- Target body length: 450–1200 characters for a substantive post.

Return ONLY a JSON object matching the output schema. No extra text."""

_INSTRUCTIONS: dict[str, SkillInstruction] = {
    "content.telegram_post": SkillInstruction(
        skill_code="content.telegram_post",
        instruction_version="1.0",
        output_schema_version="1.0",
        quality_profile_version="content_quality_v1",
        instruction_text=_TELEGRAM_INSTRUCTION,
        output_schema_json=_TELEGRAM_OUTPUT_SCHEMA,
        quality_gates=["no_fake_facts", "platform_fit", "brand_voice"],
        expertise_labels=[
            "Telegram-формат",
            "Профессиональная коммуникация",
            "Адаптация под аудиторию",
            "Вовлекающий вопрос",
            "Проверка неподтверждённых утверждений",
        ],
    ),
}


def get_skill_instruction(skill_code: str) -> SkillInstruction | None:
    return _INSTRUCTIONS.get(skill_code)
