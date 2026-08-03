"""H2.8D — IdentityImageProvider abstraction (no second Runtime)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID

from app.media_generation.contracts import ImageGenerationResult
from app.schemas.contracts import (
    IdentityProviderCapability,
    VisualExecutionMode,
)


@dataclass
class IdentityProviderInput:
    """Separated identity / scene / style / negative provider inputs."""

    identity_section: str
    scene_section: str
    style_section: str
    negative_section: str
    primary_image_path: str
    supporting_image_paths: list[str] = field(default_factory=list)
    primary_reference_id: UUID | None = None
    transmitted_reference_ids: list[UUID] = field(default_factory=list)
    identity_fidelity: str = "maximum"
    style_freedom: str = "low"
    size: str = "1024x1024"
    execution_mode: VisualExecutionMode = VisualExecutionMode.PERSON_IDENTITY_PRESERVATION
    roles: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class IdentityProviderLineage:
    """Safe lineage about what was actually transmitted — never image bytes."""

    provider: str
    model: str | None
    supports_person_identity: bool
    capability: IdentityProviderCapability
    requested_mode: str
    actual_mode: str
    transmitted_count: int
    transmitted_reference_ids: list[str]
    primary_reference_id: str | None
    primary_position: int | None
    original_dimensions: dict[str, list[int]]
    transmitted_dimensions: dict[str, list[int]]
    checksums: dict[str, str]
    mime_types: dict[str, str]
    prompt_section_hashes: dict[str, str]
    provider_request_id: str | None = None
    roles: list[dict[str, Any]] = field(default_factory=list)


class IdentityImageProvider(Protocol):
    """Dedicated identity-preservation adapter surface."""

    provider_name: str

    def supports_person_identity_preservation(self) -> bool: ...

    def capability_class(self) -> IdentityProviderCapability: ...

    async def generate_with_identity(
        self,
        input_data: IdentityProviderInput,
    ) -> tuple[ImageGenerationResult, IdentityProviderLineage]: ...


def build_prompt_sections(
    *,
    identity_section: str,
    scene_section: str,
    style_section: str,
    negative_section: str,
) -> str:
    parts = [
        "IDENTITY:",
        identity_section.strip(),
        "",
        "SCENE:",
        scene_section.strip(),
        "",
        "STYLE:",
        style_section.strip(),
        "",
        "NEGATIVE CONSTRAINTS:",
        negative_section.strip(),
    ]
    return "\n".join(parts)


def hash_section(text: str) -> str:
    import hashlib

    digest = hashlib.sha256((text or "").encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def file_lineage(path: str) -> dict[str, Any]:
    """Safe per-file lineage (dims/checksum/mime) — no bytes logged."""
    import hashlib

    p = Path(path)
    if not p.is_file():
        return {
            "exists": False,
            "original_dimensions": [0, 0],
            "transmitted_dimensions": [0, 0],
            "checksum": None,
            "mime_type": None,
        }
    raw = p.read_bytes()
    checksum = "sha256:" + hashlib.sha256(raw).hexdigest()
    mime = "application/octet-stream"
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        mime = "image/png"
    elif raw[:2] == b"\xff\xd8":
        mime = "image/jpeg"
    elif raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        mime = "image/webp"
    width = height = 0
    try:
        from PIL import Image

        with Image.open(p) as img:
            width, height = img.size
    except Exception:  # noqa: BLE001
        pass
    return {
        "exists": True,
        "original_dimensions": [width, height],
        "transmitted_dimensions": [width, height],  # no silent downscale today
        "checksum": checksum,
        "mime_type": mime,
        "byte_size": len(raw),
    }


class OpenAIIdentityAdapter:
    """Wraps OpenAI images.edit as one IdentityImageProvider adapter."""

    provider_name = "openai_images"

    def __init__(self, openai_provider: Any, *, model: str | None = None) -> None:
        self._provider = openai_provider
        self._model = model

    def supports_person_identity_preservation(self) -> bool:
        # Soft claim: API accepts a primary reference via images.edit.
        # Suitability for recognizable likeness is an owner decision after A/B.
        return True

    def capability_class(self) -> IdentityProviderCapability:
        return IdentityProviderCapability.UNKNOWN

    async def generate_with_identity(
        self,
        input_data: IdentityProviderInput,
    ) -> tuple[ImageGenerationResult, IdentityProviderLineage]:
        if not self.supports_person_identity_preservation():
            raise RuntimeError("identity_mode_not_supported")
        if not input_data.primary_image_path:
            raise RuntimeError("primary_reference_required")

        combined = build_prompt_sections(
            identity_section=input_data.identity_section,
            scene_section=input_data.scene_section,
            style_section=input_data.style_section,
            negative_section=input_data.negative_section,
        )
        fidelity = (
            "INPUT FIDELITY: high. Treat the primary reference as the identity "
            "source of truth. Supporting angles inform structure only. "
            "Best-effort generative preservation — not a biometric guarantee."
        )
        result = await self._provider.edit_with_reference(
            prompt=combined[:3500],
            image_path=input_data.primary_image_path,
            size=input_data.size if input_data.size in {"256x256", "512x512", "1024x1024"} else "1024x1024",
            preservation_instructions=fidelity,
        )

        # Honest transmit: only primary image file is sent to images.edit.
        transmitted_ids = []
        if input_data.primary_reference_id is not None:
            transmitted_ids = [str(input_data.primary_reference_id)]
        elif input_data.transmitted_reference_ids:
            transmitted_ids = [str(input_data.transmitted_reference_ids[0])]

        primary_meta = file_lineage(input_data.primary_image_path)
        orig: dict[str, list[int]] = {}
        tx: dict[str, list[int]] = {}
        checks: dict[str, str] = {}
        mimes: dict[str, str] = {}
        if transmitted_ids:
            rid = transmitted_ids[0]
            orig[rid] = list(primary_meta.get("original_dimensions") or [0, 0])
            tx[rid] = list(primary_meta.get("transmitted_dimensions") or [0, 0])
            if primary_meta.get("checksum"):
                checks[rid] = str(primary_meta["checksum"])
            if primary_meta.get("mime_type"):
                mimes[rid] = str(primary_meta["mime_type"])

        provider_request_id = None
        if isinstance(result.safe_metadata, dict):
            provider_request_id = (
                result.safe_metadata.get("provider_request_id")
                or result.safe_metadata.get("id")
            )

        lineage = IdentityProviderLineage(
            provider=self.provider_name,
            model=self._model,
            supports_person_identity=True,
            capability=self.capability_class(),
            requested_mode=VisualExecutionMode.PERSON_IDENTITY_PRESERVATION.value,
            actual_mode=VisualExecutionMode.PERSON_IDENTITY_PRESERVATION.value,
            transmitted_count=1 if transmitted_ids else 0,
            transmitted_reference_ids=transmitted_ids,
            primary_reference_id=transmitted_ids[0] if transmitted_ids else None,
            primary_position=0 if transmitted_ids else None,
            original_dimensions=orig,
            transmitted_dimensions=tx,
            checksums=checks,
            mime_types=mimes,
            prompt_section_hashes={
                "identity": hash_section(input_data.identity_section),
                "scene": hash_section(input_data.scene_section),
                "style": hash_section(input_data.style_section),
                "negative": hash_section(input_data.negative_section),
            },
            provider_request_id=str(provider_request_id) if provider_request_id else None,
            roles=list(input_data.roles or []),
        )
        # Annotate result metadata honestly
        meta = dict(result.safe_metadata or {})
        meta["mode"] = VisualExecutionMode.PERSON_IDENTITY_PRESERVATION.value
        meta["references_provider_received"] = lineage.transmitted_count
        meta["transmitted_reference_ids"] = lineage.transmitted_reference_ids
        meta["primary_reference_position"] = lineage.primary_position
        result.safe_metadata = meta
        return result, lineage


class UnsupportedIdentityAdapter:
    """Adapter for providers that cannot do person_identity_preservation."""

    provider_name = "unsupported"

    def __init__(self, name: str = "unsupported") -> None:
        self.provider_name = name

    def supports_person_identity_preservation(self) -> bool:
        return False

    def capability_class(self) -> IdentityProviderCapability:
        return IdentityProviderCapability.UNSUITABLE_FOR_IDENTITY

    async def generate_with_identity(
        self,
        input_data: IdentityProviderInput,
    ) -> tuple[ImageGenerationResult, IdentityProviderLineage]:
        raise RuntimeError("identity_mode_not_supported")
