"""Marketing data tool registry (Phase AI.221)."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from app.schemas.contracts import MarketingToolType

ToolHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, tuple[dict[str, Any], dict[str, Any]]]]


class MarketingToolRegistry:
    """Maps tool types to mock/read-only handlers."""

    def __init__(self) -> None:
        self._handlers: dict[MarketingToolType, ToolHandler] = {}

    def register(self, tool_type: MarketingToolType, handler: ToolHandler) -> None:
        self._handlers[tool_type] = handler

    def get(self, tool_type: MarketingToolType) -> ToolHandler:
        handler = self._handlers.get(tool_type)
        if handler is None:
            raise KeyError(f"Unsupported marketing tool: {tool_type.value}")
        return handler

    def supported_types(self) -> list[MarketingToolType]:
        return list(self._handlers.keys())


_registry: MarketingToolRegistry | None = None


def get_marketing_tool_registry() -> MarketingToolRegistry:
    global _registry
    if _registry is None:
        from app.services.marketing_image_generation_service import MarketingImageGenerationService
        from app.services.marketing_metrica_service import MarketingMetricaService
        from app.services.marketing_wordstat_service import MarketingWordstatService

        registry = MarketingToolRegistry()
        wordstat = MarketingWordstatService()
        metrica = MarketingMetricaService()
        image = MarketingImageGenerationService()
        registry.register(MarketingToolType.WORDSTAT, wordstat.execute)
        registry.register(MarketingToolType.METRICA, metrica.execute)
        registry.register(MarketingToolType.IMAGE_GENERATION, image.execute)
        _registry = registry
    return _registry
