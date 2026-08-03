"""Video Router — provider-independent routing + cost quotes (Product Constitution Ch.2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.config import Settings
from app.media_generation.gateway import (
    GatewayCreateRequest,
    GatewayCreateResult,
    GatewayInvokeStatus,
    GatewayModality,
    GatewayPollResult,
    ImageVideoGateway,
)
from app.media_generation.gptunnel_video_gateway import try_build_gptunnel_video_gateway
from app.media_generation.video_readiness import image_to_video_live_verified

# Catalog labels for Cost Optimizer — entrepreneur UI uses display names, not raw ids.
_ROUTER_CATALOG: tuple[dict[str, str], ...] = (
    {
        "display_name": "Google Veo",
        "catalog_model_hint": "glabs-veo",
        "provider_code": "gptunnel_creativelab",
    },
    {
        "display_name": "Runway",
        "catalog_model_hint": "runway",
        "provider_code": "runway",
    },
    {
        "display_name": "Kling",
        "catalog_model_hint": "kling",
        "provider_code": "kling",
    },
    {
        "display_name": "OpenAI",
        "catalog_model_hint": "sora",
        "provider_code": "openai",
    },
)


@dataclass(slots=True)
class VideoRouteQuote:
    display_name: str
    provider_code: str
    estimated_cost_units: str | None
    connected: bool
    recommended: bool = False
    note: str = ""


@dataclass(slots=True)
class VideoCostQuoteBundle:
    quotes: list[VideoRouteQuote] = field(default_factory=list)
    recommendation_display_name: str | None = None
    recommendation_reason_ru: str | None = None
    modality: str = "video"


def _load_discovery_prices() -> dict[str, str]:
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "data/audits/video_aggregator_discovery.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    models = data.get("discovery", {}).get("models") or data.get("pilot_recommendation", {})
    out: dict[str, str] = {}
    if isinstance(models, list):
        for row in models:
            if isinstance(row, dict) and row.get("id"):
                out[str(row["id"]).lower()] = str(row.get("price_units") or "")
    pilot = data.get("pilot_recommendation") if isinstance(data.get("pilot_recommendation"), dict) else {}
    sel = pilot.get("selected_model")
    cost = pilot.get("estimated_max_cost_units")
    if sel and cost is not None:
        out[str(sel).lower()] = str(cost)
    return out


def _price_for_hint(prices: dict[str, str], hint: str, connected_model: str | None) -> str | None:
    if connected_model and hint in connected_model.lower():
        return prices.get(connected_model.lower()) or prices.get(connected_model)
    for model_id, units in prices.items():
        if hint in model_id:
            return units or None
    return None


class VideoRouter:
    """Selects adapter per scene; entrepreneur never sees this as a picker."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._adapters: dict[str, ImageVideoGateway] = {}
        gpt = try_build_gptunnel_video_gateway(settings)
        if gpt is not None:
            self._adapters[gpt.code] = gpt

    @property
    def any_connected(self) -> bool:
        return bool(self._adapters)

    def connected_codes(self) -> list[str]:
        return list(self._adapters.keys())

    def quote(self, *, modality: GatewayModality = GatewayModality.VIDEO) -> VideoCostQuoteBundle:
        prices = _load_discovery_prices()
        connected_model = (
            self._settings.gptunnel_video_model if "gptunnel_creativelab" in self._adapters else None
        )
        quotes: list[VideoRouteQuote] = []
        for row in _ROUTER_CATALOG:
            code = row["provider_code"]
            connected = code in self._adapters
            cost = _price_for_hint(prices, row["catalog_model_hint"], connected_model) if connected else None
            if not connected:
                # Honest placeholder for future adapters — not a fake live price.
                cost = None
            quotes.append(
                VideoRouteQuote(
                    display_name=row["display_name"],
                    provider_code=code,
                    estimated_cost_units=cost,
                    connected=connected,
                    note="" if connected else "planned_adapter",
                )
            )
        recommended: VideoRouteQuote | None = None
        connected_quotes = [q for q in quotes if q.connected and q.estimated_cost_units]
        if connected_quotes:
            recommended = min(
                connected_quotes,
                key=lambda q: float(q.estimated_cost_units or "999999"),
            )
            recommended.recommended = True
        reason: str | None = None
        if recommended and len(connected_quotes) > 1:
            reason = (
                f"Рекомендуем {recommended.display_name} — "
                "оптимальное соотношение стоимости и доступного качества для этой сцены."
            )
        elif recommended:
            reason = f"Рекомендуем {recommended.display_name} — доступный видеодвижок для этой сцены."
        return VideoCostQuoteBundle(
            quotes=quotes,
            recommendation_display_name=recommended.display_name if recommended else None,
            recommendation_reason_ru=reason,
            modality=modality.value,
        )

    def pick_adapter(self) -> tuple[str, ImageVideoGateway] | None:
        bundle = self.quote()
        for q in bundle.quotes:
            if q.recommended and q.provider_code in self._adapters:
                return q.provider_code, self._adapters[q.provider_code]
        if self._adapters:
            code = next(iter(self._adapters))
            return code, self._adapters[code]
        return None

    async def create(self, request: GatewayCreateRequest) -> tuple[str, GatewayCreateResult]:
        picked = self.pick_adapter()
        if picked is None:
            return (
                "none",
                GatewayCreateResult(
                    status=GatewayInvokeStatus.NOT_CONNECTED,
                    detail_code="video_router_no_adapter",
                    detail_ru="Video Router: нет подключённого видеоадаптера.",
                    paid_call_performed=False,
                ),
            )
        code, adapter = picked
        result = await adapter.create(request)
        return code, result

    async def poll(self, provider_code: str, job_id: str) -> GatewayPollResult:
        adapter = self._adapters.get(provider_code)
        if adapter is None:
            return GatewayPollResult(
                status=GatewayInvokeStatus.NOT_CONNECTED,
                detail_code="unknown_provider",
                paid_call_performed=False,
            )
        return await adapter.poll(job_id)


def build_video_router(settings: Settings) -> VideoRouter:
    return VideoRouter(settings)


def video_router_public_status(settings: Settings) -> dict[str, Any]:
    router = build_video_router(settings)
    bundle = router.quote()
    live = image_to_video_live_verified(settings)
    return {
        "port": "VideoRouter",
        "router_registered": True,
        "adapters_connected": router.connected_codes(),
        "clients_connected": router.any_connected,
        "image_to_video_live_verified": live,
        "paid_calls_allowed": router.any_connected and live,
        "cost_optimizer_sample": {
            "recommendation": bundle.recommendation_display_name,
            "quotes": [
                {
                    "display_name": q.display_name,
                    "connected": q.connected,
                    "estimated_cost_units": q.estimated_cost_units,
                    "recommended": q.recommended,
                }
                for q in bundle.quotes
            ],
        },
    }
