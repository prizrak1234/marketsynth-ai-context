"""Specialist prompt package layer (Phase H2.7)."""

from app.prompts.specialist.assembler import (
    PromptAssemblyError,
    assemble_specialist_prompt,
)

__all__ = ["PromptAssemblyError", "assemble_specialist_prompt"]
