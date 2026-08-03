"""Programmer domain contracts (Phase AI.16) — consultation skeleton only."""

from __future__ import annotations

from enum import StrEnum

# Tool name substrings forbidden for Programmer (no shell, repo, deploy, live bots).
PROGRAMMER_FORBIDDEN_TOOL_MARKERS: frozenset[str] = frozenset(
    {
        "shell",
        "github",
        "git.",
        "filesystem",
        "file.write",
        "file_write",
        "deploy",
        "secret",
        "webhook.execute",
        "telegram.bot.create",
        "telegram_bot",
        "subprocess",
        "terminal",
        "cursor.",
    },
)


class ProgrammerOutputKind(StrEnum):
    """Structured programmer run output (in-memory only in AI.16)."""

    CONSULTATION = "consultation"
    TECHNICAL_TASK_DRAFT = "technical_task_draft"
