"""Bounded streaming download for provider video results (VS.2A VR.2A)."""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import httpx

from app.core.config import Settings

ALLOWED_VIDEO_MIMES = frozenset({"video/mp4"})


class VideoDownloadError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class VideoDownloadResult:
    temp_path: Path
    mime: str
    checksum_sha256: str
    size_bytes: int


async def download_provider_video_to_temp(
    settings: Settings,
    *,
    url: str,
    mime_hint: str | None,
) -> VideoDownloadResult:
    """Stream provider URL to a temp file with size/MIME guards."""
    max_bytes = int(settings.video_clip_download_max_bytes)
    timeout = float(settings.video_clip_download_timeout_seconds)
    fd, raw_path = tempfile.mkstemp(prefix="vs2a-vid-", suffix=".part")
    os.close(fd)
    temp_path = Path(raw_path)
    hasher = hashlib.sha256()
    size = 0
    mime = (mime_hint or "video/mp4").split(";")[0].strip().lower()

    try:
        async with (
            httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client,
            client.stream("GET", url) as resp,
        ):
            resp.raise_for_status()
            header_mime = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
            if header_mime.startswith("video/"):
                mime = header_mime
            if mime not in ALLOWED_VIDEO_MIMES:
                raise VideoDownloadError(
                    "provider_result_not_video",
                    "Provider result is not an allowed video MIME type",
                )
            cl = resp.headers.get("content-length")
            if cl and cl.isdigit() and int(cl) > max_bytes:
                raise VideoDownloadError(
                    "result_download_too_large",
                    "Provider video exceeds configured maximum size",
                )
            with temp_path.open("wb") as out:
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    size += len(chunk)
                    if size > max_bytes:
                        raise VideoDownloadError(
                            "result_download_too_large",
                            "Provider video exceeds configured maximum size",
                        )
                    hasher.update(chunk)
                    out.write(chunk)
    except httpx.TimeoutException as exc:
        temp_path.unlink(missing_ok=True)
        raise VideoDownloadError(
            "result_download_timeout",
            "Timed out downloading provider video",
        ) from exc
    except httpx.HTTPError as exc:
        temp_path.unlink(missing_ok=True)
        raise VideoDownloadError(
            "result_download_failed",
            "Failed to download provider video",
        ) from exc
    except VideoDownloadError:
        temp_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        temp_path.unlink(missing_ok=True)
        raise VideoDownloadError(
            "result_download_failed",
            "Failed to download provider video",
        ) from exc

    if size < 1:
        temp_path.unlink(missing_ok=True)
        raise VideoDownloadError("result_download_failed", "Empty provider video body")

    return VideoDownloadResult(
        temp_path=temp_path,
        mime=mime,
        checksum_sha256=hasher.hexdigest(),
        size_bytes=size,
    )


def finalize_video_temp_file(temp_path: Path, storage_dir: Path, asset_id: str) -> Path:
    """Atomic move from temp to final storage path."""
    storage_dir.mkdir(parents=True, exist_ok=True)
    final_path = storage_dir / f"{asset_id}.mp4"
    temp_path.replace(final_path)
    return final_path
