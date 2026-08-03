"""Marketing specialist executors (Phase AI.31+) — controlled single-task paths."""

from app.agents.marketer.specialists.content_planner import execute_content_planner_specialist
from app.agents.marketer.specialists.executor import execute_marketing_specialist
from app.agents.marketer.specialists.researcher import execute_researcher_specialist
from app.agents.marketer.specialists.strategist import execute_strategist_specialist

__all__ = [
    "execute_content_planner_specialist",
    "execute_marketing_specialist",
    "execute_researcher_specialist",
    "execute_strategist_specialist",
]
