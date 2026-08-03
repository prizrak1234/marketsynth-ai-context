"""H2.8E — immutable IdentityReferenceManifest builder (Source of Truth)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.domain.reference_selection import select_person_identity_refs, views_from_rows
from app.identity_generation.admission import exclusion_safe_reason
from app.identity_generation.registry import get_provider_definition
from app.schemas.contracts import (
    IdentityManifestExcludedEntry,
    IdentityManifestSelectedEntry,
    IdentityReferenceManifest,
    ReferenceSubjectType,
)
from app.core.config import Settings


SELECTION_POLICY_VERSION = "h2.8e.1"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def compute_manifest_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_identity_reference_manifest(
    *,
    owner_id: UUID,
    reference_set_id: UUID,
    reference_set_version: str,
    subject_type: ReferenceSubjectType | str,
    rows: list[Any],
    primary_reference_id: UUID | None,
    settings: Settings,
    identity_profile_version: str | None = None,
    identity_profile_id: str | None = None,
    provider_code: str | None = None,
) -> IdentityReferenceManifest:
    """Build immutable SoT from ReferenceSet + selection policy + provider limits."""
    subject = (
        subject_type
        if isinstance(subject_type, ReferenceSubjectType)
        else ReferenceSubjectType(str(subject_type))
    )
    provider = get_provider_definition(settings, provider_code)
    identity_max = min(5, int(settings.reference_identity_max_images or 5))
    # Default person policy: ≤5 total selected across identity+appearance+style
    selection = select_person_identity_refs(
        assets=views_from_rows(rows),
        primary_reference_id=primary_reference_id,
        subject_type=subject,
        identity_max=min(4, identity_max),  # 1 primary + up to 3 supporting
        style_max=1,
        appearance_max=1,
    )

    row_by_id = {r.id: r for r in rows}
    selected_entries: list[IdentityManifestSelectedEntry] = []
    transmit_cap = max(0, int(provider.maximum_identity_images))
    transmitted: list[UUID] = []

    # Cap total selected entries at 5 (identity policy SoT)
    ordered = list(selection.selected_reference_ids)
    if selection.primary_reference_id and selection.primary_reference_id in ordered:
        ordered = [selection.primary_reference_id] + [
            i for i in ordered if i != selection.primary_reference_id
        ]
    ordered = ordered[:5]

    for rank, asset_id in enumerate(ordered):
        row = row_by_id.get(asset_id)
        if row is None:
            continue
        role = next(
            (r for r in selection.roles if r.reference_id == asset_id),
            None,
        )
        will_transmit = len(transmitted) < transmit_cap
        if will_transmit:
            transmitted.append(asset_id)
            tx_status = "transmitted"
            tx_w = row.width
            tx_h = row.height
        else:
            tx_status = "selected_but_not_transmitted"
            tx_w = None
            tx_h = None
        selected_entries.append(
            IdentityManifestSelectedEntry(
                asset_id=asset_id,
                checksum=str(getattr(row, "checksum", "") or ""),
                purpose=str(
                    row.asset_purpose.value
                    if hasattr(row.asset_purpose, "value")
                    else row.asset_purpose
                ),
                role=role.role_label if role else "selected",
                group=str(
                    role.group.value if role and hasattr(role.group, "value") else (role.group if role else "other")
                ),
                original_width=row.width,
                original_height=row.height,
                transmitted_width=tx_w if will_transmit else None,
                transmitted_height=tx_h if will_transmit else None,
                mime_type=getattr(row, "mime_type", None),
                quality_status=str(
                    row.quality_status.value
                    if hasattr(row.quality_status, "value")
                    else row.quality_status
                ),
                selection_rank=rank,
                selected_reason=(
                    "primary_face"
                    if selection.primary_reference_id == asset_id
                    else "policy_selected"
                ),
                will_transmit=will_transmit,
                transmission_status=tx_status,
            )
        )

    excluded: list[IdentityManifestExcludedEntry] = []
    for asset_id in selection.excluded_reference_ids:
        code = selection.exclusion_reasons.get(str(asset_id), "not_selected")
        excluded.append(
            IdentityManifestExcludedEntry(
                asset_id=asset_id,
                exclusion_code=code,
                safe_reason=exclusion_safe_reason(code),
            )
        )
    # Also record selected-but-not-transmitted as honest adapter limit notes
    for entry in selected_entries:
        if entry.transmission_status == "selected_but_not_transmitted":
            # Keep in selected_entries; also surface in excluded-like reasons for UI diagnostics
            pass

    manifest_id = uuid4()
    created = _utc_now()
    hash_payload = {
        "owner_id": str(owner_id),
        "reference_set_id": str(reference_set_id),
        "reference_set_version": reference_set_version,
        "subject_type": subject.value,
        "primary_reference_id": str(selection.primary_reference_id)
        if selection.primary_reference_id
        else None,
        "identity_reference_ids": [str(x) for x in selection.identity_selected_ids],
        "appearance_reference_ids": [str(x) for x in selection.appearance_selected_ids],
        "style_reference_ids": [str(x) for x in selection.scene_selected_ids],
        "excluded": [
            {"asset_id": str(e.asset_id), "code": e.exclusion_code} for e in excluded
        ],
        "selected": [
            {
                "asset_id": str(e.asset_id),
                "rank": e.selection_rank,
                "purpose": e.purpose,
                "checksum": e.checksum,
                "will_transmit": e.will_transmit,
            }
            for e in selected_entries
        ],
        "selection_policy_version": SELECTION_POLICY_VERSION,
        "identity_profile_version": identity_profile_version,
        "provider_code": provider.provider_code,
        "transmitted_reference_ids": [str(x) for x in transmitted],
        "transmit_cap": transmit_cap,
    }
    immutable_hash = compute_manifest_hash(hash_payload)

    return IdentityReferenceManifest(
        manifest_id=manifest_id,
        owner_id=owner_id,
        reference_set_id=reference_set_id,
        reference_set_version=reference_set_version,
        subject_type=subject.value,
        primary_reference_id=selection.primary_reference_id,
        identity_reference_ids=list(selection.identity_selected_ids),
        appearance_reference_ids=list(selection.appearance_selected_ids),
        style_reference_ids=list(selection.scene_selected_ids),
        excluded_references=excluded,
        selected_entries=selected_entries,
        selection_policy_version=SELECTION_POLICY_VERSION,
        identity_profile_id=identity_profile_id,
        identity_profile_version=identity_profile_version,
        provider_code=provider.provider_code,
        transmitted_reference_ids=transmitted,
        references_selected_count=len(selected_entries),
        references_provider_received_count=len(transmitted),
        stored_count=len(rows),
        created_at=created,
        immutable_hash=immutable_hash,
    )
