"""Runtime capability overlay from Video Router + audit matrix."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings
from app.media_generation.video_router import build_video_router
from app.video_studio.contracts import VideoAspectRatio
from app.video_studio.provider_duration_capabilities import (
    provider_supported_single_clip_durations,
)


@dataclass(frozen=True, slots=True)
class RouteCapabilities:
    single_clip_min_seconds: int
    single_clip_max_seconds: int
    target_scene_duration_seconds: int
    provider_supported_single_clip_durations_seconds: tuple[int, ...]
    native_aspect_ratios: frozenset[str]
    post_process_aspect_ratios: frozenset[str]
    estimated_cost_units_per_clip: str | None
    router_connected: bool


def _load_pilot_aspect_ratios() -> frozenset[str]:
    path = Path(__file__).resolve().parents[2] / "data/audits/video_capability_matrix.json"
    if not path.is_file():
        return frozenset({VideoAspectRatio.LANDSCAPE_16_9.value})
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return frozenset({VideoAspectRatio.LANDSCAPE_16_9.value})
    for row in data.get("rows") or []:
        if row.get("suitable_for_pilot"):
            ratios = row.get("aspect_ratios") or []
            return frozenset(str(r) for r in ratios)
    return frozenset({VideoAspectRatio.LANDSCAPE_16_9.value})


def get_route_capabilities(settings: Settings) -> RouteCapabilities:
    router = build_video_router(settings)
    bundle = router.quote()
    recommended = next((q for q in bundle.quotes if q.recommended), None)
    cost = recommended.estimated_cost_units if recommended else None
    native = _load_pilot_aspect_ratios()
    all_ratios = {r.value for r in VideoAspectRatio}
    post = frozenset(all_ratios - set(native))
    provider_durations = provider_supported_single_clip_durations(
        settings.gptunnel_video_model
    )
    # Long-form scene decomposition uses a broader planning window than live i2v output.
    min_clip = 5
    max_clip = 15
    target = 8
    return RouteCapabilities(
        single_clip_min_seconds=min_clip,
        single_clip_max_seconds=max_clip,
        target_scene_duration_seconds=target,
        provider_supported_single_clip_durations_seconds=provider_durations,
        native_aspect_ratios=native,
        post_process_aspect_ratios=post,
        estimated_cost_units_per_clip=cost,
        router_connected=router.any_connected,
    )
