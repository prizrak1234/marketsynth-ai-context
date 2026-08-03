"""Scene Graph — structural unit for Video Studio (not a Timeline)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4


class VideoSceneMode(StrEnum):
    AI_DIRECTOR = "ai_director"
    TEXT_TO_VIDEO = "text_to_video"
    IMAGE_TO_VIDEO = "image_to_video"
    START_END_FRAME = "start_end_frame"


@dataclass(slots=True)
class SceneGraphNode:
    scene_id: str
    order: int
    description: str
    prompt: str
    duration_seconds: int = 8
    aspect_ratio: str = "16:9"
    camera_motion: str = ""
    start_frame_asset_id: str | None = None
    end_frame_asset_id: str | None = None
    clip_asset_id: str | None = None
    voice_track_id: str | None = None
    music_track_id: str | None = None
    provider_code: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SceneGraph:
    project_id: str
    mode: VideoSceneMode
    target_duration_seconds: int | None = None
    scenes: list[SceneGraphNode] = field(default_factory=list)

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "mode": self.mode.value,
            "target_duration_seconds": self.target_duration_seconds,
            "scene_count": len(self.scenes),
            "scenes": [
                {
                    "scene_id": s.scene_id,
                    "order": s.order,
                    "description": s.description[:200],
                    "duration_seconds": s.duration_seconds,
                    "aspect_ratio": s.aspect_ratio,
                    "has_start_frame": bool(s.start_frame_asset_id),
                    "has_end_frame": bool(s.end_frame_asset_id),
                    "has_clip": bool(s.clip_asset_id),
                }
                for s in self.scenes
            ],
        }


def build_single_clip_scene_graph(
    *,
    brief: str,
    mode: VideoSceneMode,
    duration_seconds: int = 8,
    aspect_ratio: str = "16:9",
    camera_motion: str = "",
    start_frame_asset_id: str | None = None,
) -> SceneGraph:
    """VS.2 — one-scene graph for expert Text/Image → Video."""
    scene = SceneGraphNode(
        scene_id=str(uuid4()),
        order=1,
        description=brief[:500],
        prompt=brief[:4000],
        duration_seconds=duration_seconds,
        aspect_ratio=aspect_ratio,
        camera_motion=camera_motion,
        start_frame_asset_id=start_frame_asset_id,
    )
    return SceneGraph(
        project_id=str(uuid4()),
        mode=mode,
        target_duration_seconds=duration_seconds,
        scenes=[scene],
    )
