"""Measure MP4 duration for VS.2A-R result validation."""

from __future__ import annotations

import struct
from pathlib import Path

from app.schemas.contracts import DurationValidationStatus
from app.video_studio.provider_duration_capabilities import SINGLE_CLIP_DURATION_TOLERANCE_SECONDS


class VideoDurationProbeError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _read_box_header(data: bytes, offset: int) -> tuple[int, bytes, int] | None:
    if offset + 8 > len(data):
        return None
    size, box_type = struct.unpack_from(">I4s", data, offset)
    header_size = 8
    if size == 1:
        if offset + 16 > len(data):
            return None
        size = struct.unpack_from(">Q", data, offset + 8)[0]
        header_size = 16
    elif size == 0:
        size = len(data) - offset
    return size, box_type, header_size


def _find_mvhd(data: bytes, offset: int = 0, end: int | None = None) -> tuple[int, int] | None:
    end = len(data) if end is None else end
    pos = offset
    while pos + 8 <= end:
        parsed = _read_box_header(data, pos)
        if parsed is None:
            return None
        size, box_type, header_size = parsed
        if size < header_size:
            return None
        box_end = pos + size
        if box_type == b"mvhd":
            payload = data[pos + header_size : box_end]
            if len(payload) < 28:
                return None
            version = payload[0]
            if version == 0:
                if len(payload) < 20:
                    return None
                timescale = struct.unpack_from(">I", payload, 12)[0]
                duration = struct.unpack_from(">I", payload, 16)[0]
            elif version == 1:
                if len(payload) < 32:
                    return None
                timescale = struct.unpack_from(">I", payload, 20)[0]
                duration = struct.unpack_from(">Q", payload, 24)[0]
            else:
                return None
            if timescale <= 0:
                return None
            return timescale, duration
        if box_type in {b"moov", b"trak", b"mdia", b"minf", b"stbl", b"edts"}:
            found = _find_mvhd(data, pos + header_size, box_end)
            if found is not None:
                return found
        pos = box_end
    return None


def probe_mp4_duration_seconds(path: Path | str) -> float:
    """Return measured MP4 duration in seconds (mvhd box)."""
    file_path = Path(path)
    if not file_path.is_file():
        raise VideoDurationProbeError("video_file_missing")
    data = file_path.read_bytes()
    if len(data) < 32:
        raise VideoDurationProbeError("video_file_too_small")
    mvhd = _find_mvhd(data)
    if mvhd is None:
        raise VideoDurationProbeError("mvhd_not_found")
    timescale, duration_ticks = mvhd
    return duration_ticks / timescale


def classify_duration_validation(
    *,
    requested_seconds: int,
    actual_seconds: float,
    tolerance_seconds: float = SINGLE_CLIP_DURATION_TOLERANCE_SECONDS,
) -> tuple[DurationValidationStatus, float]:
    delta = round(actual_seconds - requested_seconds, 3)
    abs_delta = abs(delta)
    if abs_delta <= 0.05:
        return DurationValidationStatus.MATCHED, delta
    if abs_delta <= tolerance_seconds:
        return DurationValidationStatus.WITHIN_TOLERANCE, delta
    return DurationValidationStatus.MISMATCH, delta
