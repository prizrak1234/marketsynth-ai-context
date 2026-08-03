"""Sanitize provider outputs — no secrets, base64, or raw payloads (Phase AI.56+)."""

from __future__ import annotations

from typing import Any

_FORBIDDEN_KEYS = frozenset(
    {
        "b64_json",
        "base64",
        "raw",
        "raw_response",
        "api_key",
        "authorization",
        "secret",
        "data",
        "images",
        "output",
    },
)

_ALLOWED_TOP_LEVEL = frozenset(
    {
        "provider",
        "model",
        "image_count",
        "size",
        "mime_type",
        "mock",
        "placeholder",
        "provider_asset_ref",
        "revision",
        "quality",
        "style",
        "aspect_ratio",
        "skill_code",
        "user_request_id",
        "generation_mode",
        "asset_type",
        "diagnostic_marker",
        "is_user_result",
        "provider_model",
        "warnings",
        "has_b64",
        "mode",
        "visual_generation_mode",
        "requested_generation_mode",
        "selection_summary",
        "prompt_hash",
        "input_fingerprint",
        "expected_subject",
        "observed_subject_category",
        "references_provider_received",
        "prompt_preview",
        "prompt_length",
        "is_meta_only",
        "semantic_mismatch",
        "_used_refs",
        "_prompt_recovered_from_prior",
        "identity_profile_version",
        "identity_strengthen_mode",
        "visual_consistency",
        "parent_asset_id",
        "primary_reference_id",
        "selected_reference_ids",
        "excluded_reference_ids",
        "requested_mode",
        "actual_mode",
        "input_fidelity",
        "omitted_reference_reasons",
        "identity_prompt_hash",
        "references_count_in_set",
        "references_selected_count",
        # H2.8D honest transmit lineage (ids/counts/hashes only — never image bytes)
        "transmitted_reference_ids",
        "primary_reference_position",
        "identity_selected_count",
        "style_selected_count",
        "prompt_section_hashes",
        "provider_request_id",
        "provider_capability",
        "selection_roles",
        "transmitted_original_dimensions",
        "transmitted_dimensions",
        "transmitted_checksums",
        "transmitted_mime_types",
        "ab_variant",
        "selected_but_not_transmitted_ids",
        "selected_but_not_transmitted_reason",
        "references_provider_received_count",
        "safe_transmit_note_ru",
        "manifest_id",
        "manifest_hash",
        "subsystem",
        "identity_capability_status",
        "identity_provider_input_capacity",
    },
)

# Dict values allowed only for bounded lineage maps (id -> small scalar/list).
_ALLOWED_DICT_KEYS = frozenset(
    {
        "prompt_section_hashes",
        "transmitted_original_dimensions",
        "transmitted_dimensions",
        "transmitted_checksums",
        "transmitted_mime_types",
        "exclusion_reasons",
    },
)


def _contains_base64_blob(value: object) -> bool:
    if not isinstance(value, str):
        return False
    lowered = value.lower()
    if len(value) < 256:
        return False
    return "base64" in lowered or lowered.startswith("data:image")


def _sanitize_lineage_dict(value: dict[str, Any], *, max_items: int = 20) -> dict[str, Any]:
    """Keep id→scalar/list maps only; drop nested blobs."""
    out: dict[str, Any] = {}
    for i, (k, v) in enumerate(value.items()):
        if i >= max_items:
            break
        key = str(k)[:64]
        if isinstance(v, (int, float, bool)) or v is None:
            out[key] = v
        elif isinstance(v, str) and not _contains_base64_blob(v):
            out[key] = v[:128]
        elif isinstance(v, list) and all(isinstance(x, (int, float)) for x in v):
            out[key] = [float(x) for x in v[:8]]
        elif isinstance(v, list) and all(isinstance(x, str) for x in v):
            out[key] = [str(x)[:64] for x in v[:8]]
    return out


def sanitize_generation_metadata(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not raw:
        return {}
    cleaned: dict[str, Any] = {}
    for key, value in raw.items():
        key_lower = str(key).lower()
        if key_lower in _FORBIDDEN_KEYS:
            continue
        if _contains_base64_blob(value):
            continue
        if isinstance(value, dict):
            if key_lower in _ALLOWED_DICT_KEYS:
                cleaned[key] = _sanitize_lineage_dict(value)
            continue
        # Allow short string lists (e.g. warnings) — never nested blobs.
        if isinstance(value, list):
            if key_lower == "warnings" and all(isinstance(x, str) for x in value):
                cleaned[key] = [str(x)[:200] for x in value[:20]]
            elif key_lower in {
                "selected_reference_ids",
                "excluded_reference_ids",
                "transmitted_reference_ids",
                "selected_but_not_transmitted_ids",
            } and all(isinstance(x, str) for x in value):
                cleaned[key] = [str(x)[:64] for x in value[:15]]
            elif key_lower == "selection_roles" and all(isinstance(x, dict) for x in value):
                roles: list[dict[str, Any]] = []
                for item in value[:20]:
                    roles.append(
                        {
                            "reference_id": str(item.get("reference_id") or "")[:64],
                            "purpose": str(item.get("purpose") or "")[:64],
                            "group": str(item.get("group") or "")[:32],
                            "role_label": str(item.get("role_label") or "")[:120],
                            "is_primary": bool(item.get("is_primary")),
                            "selected": bool(item.get("selected")),
                            "exclusion_reason": (
                                str(item["exclusion_reason"])[:64]
                                if item.get("exclusion_reason") is not None
                                else None
                            ),
                        }
                    )
                cleaned[key] = roles
            continue
        if key_lower in _ALLOWED_TOP_LEVEL or key_lower.endswith("_ref"):
            cleaned[key] = value
    return cleaned
