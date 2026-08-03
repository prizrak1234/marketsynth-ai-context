"""Expected read-only tool names exposed to researcher / strategist agents."""

RESEARCHER_READ_ONLY_TOOL_NAMES = [
    "marketing_brief.get",
    "marketing_brief.list",
    "marketing_funnel.gap_analysis",
    "marketing_funnel.get",
    "marketing_funnel.list",
    "marketing_funnel.step_assets",
    "memory.search",
    "project_context.get",
    "task.get",
    "task.list_recent",
]

RESEARCHER_READ_ONLY_TOOL_COUNT = len(RESEARCHER_READ_ONLY_TOOL_NAMES)
