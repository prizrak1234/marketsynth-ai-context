"""Media Renderer abstraction — interchangeable executor backends."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.schemas.contracts import MediaRendererReadiness, MediaRenderJobResponse, MediaRenderRequest


@runtime_checkable
class MediaRendererBackend(Protocol):
    """Executor protocol — Skills produce MediaRenderSpec; renderer executes only."""

    renderer_id: str

    async def readiness(self) -> MediaRendererReadiness: ...

    async def render(self, request: MediaRenderRequest, **context) -> MediaRenderJobResponse: ...

    async def get_status(self, job_id: str, **context) -> MediaRenderJobResponse: ...

    async def download_result(self, job_id: str, **context) -> MediaRenderJobResponse: ...
