"""Marketing orchestrator scenario detection (Phase AI.9)."""

from app.agents.scenarios.contracts import MarketingScenarioType
from app.agents.scenarios.detector import detect_marketing_scenario

__all__ = [
    "MarketingScenarioType",
    "detect_marketing_scenario",
]
