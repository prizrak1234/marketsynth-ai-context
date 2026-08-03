"""Long-form scene decomposition — requested duration ≠ provider clip duration."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.exceptions import InvalidStateError
from app.video_studio.router_capabilities import RouteCapabilities


@dataclass(frozen=True, slots=True)
class LongFormPlan:
    requested_duration_seconds: int
    target_scene_duration_seconds: int
    scene_count: int
    scene_durations_seconds: list[int]
    estimated_provider_calls: int

    @property
    def total_seconds(self) -> int:
        return sum(self.scene_durations_seconds)


def plan_long_form_scenes(
    requested_duration_seconds: int,
    capabilities: RouteCapabilities,
) -> LongFormPlan:
    if requested_duration_seconds <= capabilities.single_clip_max_seconds:
        raise InvalidStateError("not_long_form_duration")

    target = capabilities.target_scene_duration_seconds
    min_scene = capabilities.single_clip_min_seconds
    max_scene = capabilities.single_clip_max_seconds

    scene_count = max(1, (requested_duration_seconds + target - 1) // target)
    for _ in range(64):
        if scene_count < 1:
            break
        head = scene_count - 1
        last = requested_duration_seconds - target * head
        if last <= 0:
            scene_count -= 1
            continue
        if last > max_scene:
            scene_count += 1
            continue
        if last < min_scene:
            scene_count -= 1
            continue
        durations = [target] * head + [last]
        total = sum(durations)
        if total != requested_duration_seconds:
            raise InvalidStateError("long_form_plan_sum_mismatch")
        if any(d <= 0 for d in durations):
            raise InvalidStateError("long_form_invalid_scene_duration")
        return LongFormPlan(
            requested_duration_seconds=requested_duration_seconds,
            target_scene_duration_seconds=target,
            scene_count=len(durations),
            scene_durations_seconds=durations,
            estimated_provider_calls=len(durations),
        )

    raise InvalidStateError("long_form_plan_failed")
