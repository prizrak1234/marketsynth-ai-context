"""Image/Video Gateway protocol — connection point for GPTunnel (CGP.7).

No live clients here. Existing GptunnelImagesProvider remains the image adapter;
video client is deferred until after editorial conveyor freeze + owner confirmation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable


class GatewayModality(StrEnum):
    IMAGE = "image"
    VIDEO = "video"


class GatewayInvokeStatus(StrEnum):
    BLOCKED = "blocked"
    NOT_CONNECTED = "not_connected"
    QUEUED = "queued"
    DONE = "done"
    FAILED = "failed"


@dataclass(slots=True)
class GatewayCreateRequest:
    modality: GatewayModality
    model: str
    prompt: str
    aspect_ratio: str = "16:9"
    images: list[str] = field(default_factory=list)
    duration_seconds: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GatewayCreateResult:
    status: GatewayInvokeStatus
    job_id: str | None = None
    detail_code: str = ""
    detail_ru: str = ""
    paid_call_performed: bool = False


@dataclass(slots=True)
class GatewayPollResult:
    status: GatewayInvokeStatus
    url: str | None = None
    mime: str | None = None
    detail_code: str = ""
    paid_call_performed: bool = False


@runtime_checkable
class ImageVideoGateway(Protocol):
    """Normalized create/result surface for image + video aggregators."""

    code: str
    clients_connected: bool

    async def create(self, request: GatewayCreateRequest) -> GatewayCreateResult: ...

    async def poll(self, job_id: str) -> GatewayPollResult: ...


class NullImageVideoGateway:
    """Default port — registered, not connected, never spends."""

    code = "null_image_video_gateway"
    clients_connected = False

    async def create(self, request: GatewayCreateRequest) -> GatewayCreateResult:
        _ = request
        return GatewayCreateResult(
            status=GatewayInvokeStatus.NOT_CONNECTED,
            detail_code="gateway_not_connected",
            detail_ru="ImageVideoGateway зарегистрирован, клиент не подключён.",
            paid_call_performed=False,
        )

    async def poll(self, job_id: str) -> GatewayPollResult:
        _ = job_id
        return GatewayPollResult(
            status=GatewayInvokeStatus.NOT_CONNECTED,
            detail_code="gateway_not_connected",
            paid_call_performed=False,
        )


def gateway_port_status(settings: object | None = None) -> dict[str, object]:
    from app.core.config import get_settings
    from app.media_generation.video_router import video_router_public_status

    cfg = settings if settings is not None else get_settings()
    router_status = video_router_public_status(cfg)  # type: ignore[arg-type]
    return {
        "port": "ImageVideoGateway",
        "ports_registered": True,
        "clients_connected": router_status.get("clients_connected", False),
        "adapters_planned": [
            "gptunnel_creativelab_video",
            "runway",
            "kling",
            "openai",
        ],
        "adapters_connected": router_status.get("adapters_connected", []),
        "video_router": router_status,
        "paid_calls_allowed": router_status.get("paid_calls_allowed", False),
    }
