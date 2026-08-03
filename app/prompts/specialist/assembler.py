"""Prompt Assembler (Phase H2.7).

Single place that assembles a specialist prompt in the governed order. Emits
LLM messages plus a safe, versioned PromptPackage (hashes and lineage only —
never hidden reasoning, never secrets).
"""

from __future__ import annotations

import hashlib
import json
from uuid import UUID

from app.llm.contracts import LLMMessage
from app.prompts.specialist.constitutional import (
    CONSTITUTIONAL_PROMPT,
    CONSTITUTIONAL_PROMPT_VERSION,
)
from app.prompts.specialist.roles import get_role_prompt
from app.prompts.specialist.skills import get_skill_instruction
from app.schemas.contracts import PromptPackage


class PromptAssemblyError(RuntimeError):
    pass


def _knowledge_block(knowledge_blocks: list[str], locale: str) -> str:
    if not knowledge_blocks:
        return "APPROVED KNOWLEDGE: (none attached)"
    lines = ["APPROVED KNOWLEDGE (use only this; cite when required):"]
    for idx, block in enumerate(knowledge_blocks, start=1):
        cleaned = " ".join(str(block).split())[:1200]
        lines.append(f"[{idx}] {cleaned}")
    return "\n".join(lines)


def _user_block(*, locale: str, user_text: str, inputs: dict[str, object]) -> str:
    safe_inputs = {
        k: v
        for k, v in (inputs or {}).items()
        if not str(k).startswith("_") and v not in (None, "")
    }
    return (
        f"LOCALE: {locale}\n"
        f"USER REQUEST:\n{user_text.strip()[:4000]}\n\n"
        f"STRUCTURED INPUTS:\n{json.dumps(safe_inputs, ensure_ascii=False, sort_keys=True)}"
    )


def assemble_specialist_prompt(
    *,
    specialist_role: str,
    skill_code: str,
    locale: str,
    user_text: str,
    skill_inputs: dict[str, object],
    knowledge_blocks: list[str],
    knowledge_snapshot_id: UUID | None,
    knowledge_snapshot_hash: str | None,
    tool_policy_version: str,
) -> tuple[list[LLMMessage], PromptPackage]:
    role_prompt = get_role_prompt(specialist_role)
    if role_prompt is None:
        raise PromptAssemblyError(f"no_role_prompt:{specialist_role}")
    skill = get_skill_instruction(skill_code)
    if skill is None:
        raise PromptAssemblyError(f"no_skill_instruction:{skill_code}")

    knowledge_text = _knowledge_block(knowledge_blocks, locale)
    user_text_block = _user_block(locale=locale, user_text=user_text, inputs=skill_inputs)

    # Governed assembly order:
    # 1 constitutional, 2 role, 3 skill instruction, 4 knowledge,
    # 5 user request, 6 output schema, 7 quality gates, 8 tool policy, 9 locale/style
    system_sections = [
        CONSTITUTIONAL_PROMPT.strip(),
        f"ROLE:\n{role_prompt.text}",
        f"SKILL INSTRUCTION ({skill_code}):\n{skill.instruction_text}",
        knowledge_text,
        f"OUTPUT SCHEMA (return ONLY this JSON):\n{skill.output_schema_json}",
        "QUALITY GATES: " + ", ".join(skill.quality_gates),
        (
            "TOOL POLICY: No tools available for this task. Do not request or assume "
            "external tools, publishing, ads or workflows."
        ),
        f"STYLE: respond in locale '{locale}'. Output must be valid JSON only.",
    ]
    system_prompt = "\n\n".join(system_sections)

    messages = [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=user_text_block),
    ]

    rendered_hash = "sha256:" + hashlib.sha256(
        (system_prompt + "\n\n" + user_text_block).encode("utf-8")
    ).hexdigest()

    package = PromptPackage(
        code=f"prompt.{skill_code}",
        version="1.0",
        locale=locale,
        specialist_role=specialist_role,
        skill_code=skill_code,
        constitutional_prompt_version=CONSTITUTIONAL_PROMPT_VERSION,
        role_prompt_version=role_prompt.version,
        skill_instruction_version=skill.instruction_version,
        output_schema_version=skill.output_schema_version,
        quality_profile_version=skill.quality_profile_version,
        tool_policy_version=tool_policy_version,
        knowledge_snapshot_id=knowledge_snapshot_id,
        knowledge_snapshot_hash=knowledge_snapshot_hash,
        rendered_hash=rendered_hash,
        status="assembled",
    )
    return messages, package
