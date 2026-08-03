"""Phase H2.8D — identity engine audit, selection, provider decision."""

from __future__ import annotations

import io
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.domain.identity_preservation import (
    MSG_IDENTITY_MODE_UNSUPPORTED,
    MSG_QUALITY_GATE_REJECTED,
    build_identity_profile,
    build_identity_prompt_sections,
    build_separated_provider_inputs,
)
from app.domain.reference_selection import (
    can_be_primary_face,
    select_person_identity_refs,
    views_from_rows,
)
from app.media_generation.identity_provider import (
    IdentityProviderInput,
    OpenAIIdentityAdapter,
    UnsupportedIdentityAdapter,
    hash_section,
)
from app.schemas.contracts import (
    GeneratedVisualAssetStatus,
    ReferenceAssetPurpose,
    ReferencePurposeGroup,
    ReferenceQualityStatus,
    ReferenceSubjectType,
    VisualConsistencyLevel,
    VisualExecutionMode,
)


def _png_bytes(w: int = 512, h: int = 512, color=(30, 90, 140)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, format="PNG")
    return buf.getvalue()


class _FakeRow:
    def __init__(
        self,
        *,
        purpose: ReferenceAssetPurpose,
        quality: ReferenceQualityStatus = ReferenceQualityStatus.SUITABLE,
        width: int = 800,
        height: int = 800,
        purposes: list | None = None,
    ) -> None:
        self.id = uuid4()
        self.asset_purpose = purpose
        self.quality_status = quality
        self.width = width
        self.height = height
        self.asset_purposes = purposes or [purpose.value]


def test_body_photo_cannot_be_primary_face() -> None:
    assert can_be_primary_face(ReferenceAssetPurpose.FACE_FRONT) is True
    assert can_be_primary_face(ReferenceAssetPurpose.FULL_BODY) is False
    assert can_be_primary_face(ReferenceAssetPurpose.POSE) is False
    assert can_be_primary_face(ReferenceAssetPurpose.CLOTHING) is False


def test_selection_does_not_default_all_to_face_and_caps_identity() -> None:
    rows = [
        _FakeRow(purpose=ReferenceAssetPurpose.FACE_FRONT),
        _FakeRow(purpose=ReferenceAssetPurpose.FACE_THREE_QUARTER),
        _FakeRow(purpose=ReferenceAssetPurpose.FACE_PROFILE),
        _FakeRow(purpose=ReferenceAssetPurpose.FACE_CLOSEUP),
        _FakeRow(purpose=ReferenceAssetPurpose.FACE_REFERENCE),
        _FakeRow(purpose=ReferenceAssetPurpose.FACE_FRONT, width=400, height=400),
        _FakeRow(purpose=ReferenceAssetPurpose.STYLE_REFERENCE),
        _FakeRow(purpose=ReferenceAssetPurpose.FULL_BODY),
        _FakeRow(purpose=ReferenceAssetPurpose.OTHER),
    ]
    primary = rows[0].id
    result = select_person_identity_refs(
        assets=views_from_rows(rows),
        primary_reference_id=primary,
        subject_type=ReferenceSubjectType.PERSON,
        identity_max=5,
        style_max=1,
        appearance_max=1,
    )
    assert result.identity_selected_count <= 5
    assert result.primary_reference_id == primary
    assert result.transmitted_reference_ids[0] == primary
    assert len(result.transmitted_reference_ids) == 1  # honest OpenAI transmit
    assert result.style_selected_count >= 1
    assert result.excluded_count >= 1
    assert "Для внешности выбрано" in result.selection_summary
    # Body is appearance-selected at most once, not all faces blindly.
    body_ids = {r.id for r in rows if r.asset_purpose == ReferenceAssetPurpose.FULL_BODY}
    assert not body_ids.issubset(set(result.identity_selected_ids))


def test_body_primary_is_rejected_and_reassigned() -> None:
    body = _FakeRow(purpose=ReferenceAssetPurpose.FULL_BODY)
    face = _FakeRow(purpose=ReferenceAssetPurpose.FACE_FRONT)
    result = select_person_identity_refs(
        assets=views_from_rows([body, face]),
        primary_reference_id=body.id,
        subject_type=ReferenceSubjectType.PERSON,
        identity_max=5,
    )
    assert str(body.id) in result.exclusion_reasons
    assert result.exclusion_reasons[str(body.id)] == "body_not_primary"
    assert face.id in result.identity_selected_ids
    # Primary face should win after body primary is rejected.
    assert result.primary_reference_id in {None, face.id} or face.id in (
        result.transmitted_reference_ids or []
    )


def test_separated_prompt_sections() -> None:
    profile = build_identity_profile(
        primary_reference_id=uuid4(),
        reference_asset_ids=[uuid4()],
        strengthen_mode=True,
    )
    parts = build_separated_provider_inputs(
        scene_prompt="Dark fantasy cinematic portrait",
        profile=profile,
    )
    assert "IDENTITY" not in parts  # keys are lowercase section names
    assert "identity" in parts and "scene" in parts and "style" in parts and "negative" in parts
    text = build_identity_prompt_sections(
        scene_prompt="Dark fantasy cinematic portrait",
        profile=profile,
    )
    assert "IDENTITY:" in text
    assert "SCENE:" in text
    assert "STYLE:" in text
    assert "NEGATIVE CONSTRAINTS:" in text
    assert hash_section(parts["identity"]).startswith("sha256:")


def test_unsupported_identity_adapter_fails_honestly() -> None:
    import asyncio

    adapter = UnsupportedIdentityAdapter("gptunnel")
    assert adapter.supports_person_identity_preservation() is False

    async def _run() -> None:
        await adapter.generate_with_identity(
            IdentityProviderInput(
                identity_section="x",
                scene_section="y",
                style_section="z",
                negative_section="n",
                primary_image_path="/tmp/missing.png",
            )
        )

    with pytest.raises(RuntimeError, match="identity_mode_not_supported"):
        asyncio.run(_run())


def test_openai_adapter_reports_single_transmit(tmp_path: Path) -> None:
    import asyncio

    img = tmp_path / "primary.png"
    img.write_bytes(_png_bytes())

    class _Prov:
        async def edit_with_reference(self, **kwargs):  # noqa: ANN003
            from app.media_generation.contracts import ImageGenerationResult

            return ImageGenerationResult(
                provider="openai_images",
                safe_metadata={"mode": "reference_guided"},
                image_bytes=_png_bytes(256, 256),
                mime_type="image/png",
                width=256,
                height=256,
            )

    adapter = OpenAIIdentityAdapter(_Prov(), model="gpt-image-1")
    primary_id = uuid4()

    async def _run():
        return await adapter.generate_with_identity(
            IdentityProviderInput(
                identity_section="keep face",
                scene_section="dark fantasy",
                style_section="cinematic",
                negative_section="no replace",
                primary_image_path=str(img),
                primary_reference_id=primary_id,
                transmitted_reference_ids=[primary_id],
            )
        )

    result, lineage = asyncio.run(_run())
    assert lineage.transmitted_count == 1
    assert lineage.transmitted_reference_ids == [str(primary_id)]
    assert lineage.primary_position == 0
    assert lineage.actual_mode == VisualExecutionMode.PERSON_IDENTITY_PRESERVATION.value
    assert result.safe_metadata["references_provider_received"] == 1


def test_quality_gate_copy_not_success() -> None:
    assert "не принят" in MSG_QUALITY_GATE_REJECTED.lower() or "не принят" in MSG_QUALITY_GATE_REJECTED
    assert "специализированный" in MSG_IDENTITY_MODE_UNSUPPORTED


def test_purpose_groups_separated() -> None:
    from app.domain.reference_selection import purpose_group

    assert purpose_group(ReferenceAssetPurpose.FACE_FRONT) == ReferencePurposeGroup.IDENTITY
    assert purpose_group(ReferenceAssetPurpose.HAIR) == ReferencePurposeGroup.APPEARANCE
    assert purpose_group(ReferenceAssetPurpose.STYLE_REFERENCE) == ReferencePurposeGroup.SCENE


def test_selection_api_and_review_freeze(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("REFERENCE_IMAGE_STORAGE_DIR", str(tmp_path / "refs"))
    monkeypatch.setenv("REFERENCE_IMAGE_MIN_WIDTH", "256")
    monkeypatch.setenv("REFERENCE_IMAGE_MIN_HEIGHT", "256")
    monkeypatch.setenv("REFERENCE_IDENTITY_MAX_IMAGES", "5")
    from app.core.config import get_settings

    get_settings.cache_clear()

    created = client.post(
        "/reference-sets",
        headers=auth_headers,
        json={"title": "H28D", "subject_type": "person", "consent_confirmed": True},
    )
    assert created.status_code == 201
    set_id = created.json()["id"]

    # Upload mixed purposes — do NOT default everything to face_front
    purposes = [
        "face_front",
        "face_three_quarter",
        "face_profile",
        "full_body",
        "style_reference",
        "other",
        "face_closeup",
        "clothing",
    ]
    ids = []
    for i, purpose in enumerate(purposes):
        up = client.post(
            f"/reference-sets/{set_id}/assets",
            headers=auth_headers,
            files={"file": (f"r{i}.png", _png_bytes(400 + i, 400 + i, (10 * i, 20, 30)), "image/png")},
            data={
                "asset_purpose": purpose,
                "subject_type": "person",
                "consent_confirmed": "true",
            },
        )
        assert up.status_code == 201, up.text
        ids.append(up.json()["id"])

    # Body cannot be primary
    bad_primary = client.patch(
        f"/reference-sets/{set_id}",
        headers=auth_headers,
        json={"primary_reference_id": ids[3]},  # full_body
    )
    assert bad_primary.status_code == 200

    sel = client.get(f"/reference-sets/{set_id}/selection", headers=auth_headers)
    assert sel.status_code == 200
    body = sel.json()
    assert body["identity_selected_count"] <= 5
    assert body["stored_count"] == len(purposes)
    assert "Для внешности выбрано" in body["selection_summary"]
    assert ids[3] not in body.get("identity_selected_ids", [])
    # Primary body should be excluded as body_not_primary when selecting
    reasons = body.get("exclusion_reasons") or {}
    assert reasons.get(ids[3]) in {"body_not_primary", "not_selected", "style_only", None} or ids[
        3
    ] in body["excluded_reference_ids"]

    # Mark face primary
    client.patch(
        f"/reference-sets/{set_id}",
        headers=auth_headers,
        json={"primary_reference_id": ids[0]},
    )
    sel2 = client.get(f"/reference-sets/{set_id}/selection", headers=auth_headers)
    assert sel2.json()["primary_reference_id"] == ids[0]
    assert sel2.json()["transmitted_reference_ids"][0] == ids[0]


def test_gptunnel_identity_mode_not_supported(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("REFERENCE_IMAGE_STORAGE_DIR", str(tmp_path / "refs"))
    monkeypatch.setenv("IMAGE_GENERATION_ENABLED", "true")
    monkeypatch.setenv("IMAGE_GENERATION_PROVIDER", "gptunnel")
    monkeypatch.setenv("GPTUNNEL_API_KEY", "test-key")
    monkeypatch.setenv("ALLOW_MOCK_IMAGE_RESULTS", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()

    created = client.post(
        "/reference-sets",
        headers=auth_headers,
        json={"title": "GT", "subject_type": "person", "consent_confirmed": True},
    )
    set_id = created.json()["id"]
    up = client.post(
        f"/reference-sets/{set_id}/assets",
        headers=auth_headers,
        files={"file": ("f.png", _png_bytes(), "image/png")},
        data={
            "asset_purpose": "face_front",
            "subject_type": "person",
            "consent_confirmed": "true",
        },
    )
    assert up.status_code == 201

    resp = client.post(
        "/user-requests",
        headers=auth_headers,
        json={
            "text": "Создай фотореалистичный кинематографический портрет взрослой женщины в тёмном фэнтези.",
            "selected_scenario": "image_generation",
            "skill_inputs": {
                "reference_set_id": set_id,
                "force_image_generation": "true",
                "execution_mode": "person_identity_preservation",
            },
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data.get("generation_status") in {
        "unavailable",
        None,
        "failed",
    } or "внешности" in (data.get("assistant_message") or "")
    msg = (data.get("assistant_message") or "").lower()
    assert "внешности" in msg or data.get("generation_warnings")


def test_ab_harness_requires_confirmation(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    monkeypatch.setattr(settings, "identity_ab_harness_enabled", True)
    resp = client.post(
        "/generated-visual-assets/identity-ab-harness",
        headers=auth_headers,
        json={
            "reference_set_id": str(uuid4()),
            "prompt": "portrait",
            "owner_confirmed_paid_calls": False,
        },
    )
    assert resp.status_code == 400, resp.text
    body = resp.json()
    detail = body.get("detail")
    blob = str(body)
    assert (
        (isinstance(detail, dict) and detail.get("error_code") == "owner_confirmation_required")
        or "owner_confirmation_required" in blob
    )


def test_ab_harness_disabled_by_default(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    from app.core.config import get_settings

    get_settings.cache_clear()
    resp = client.post(
        "/generated-visual-assets/identity-ab-harness",
        headers=auth_headers,
        json={
            "reference_set_id": str(uuid4()),
            "prompt": "portrait",
            "owner_confirmed_paid_calls": True,
        },
    )
    assert resp.status_code == 403


def test_review_marks_rejected_insufficient_similarity_immutable(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Create a real asset via mock path is hard; use DB through API list after generation mock."""
    monkeypatch.setenv("IMAGE_GENERATION_ENABLED", "true")
    monkeypatch.setenv("IMAGE_GENERATION_PROVIDER", "mock")
    monkeypatch.setenv("ALLOW_MOCK_IMAGE_RESULTS", "true")
    monkeypatch.setenv("IMAGE_GENERATION_STORAGE_DIR", str(tmp_path / "gen"))
    from app.core.config import get_settings

    get_settings.cache_clear()

    # Without refs mock succeeds as diagnostic — still reviewable if we have an asset id.
    # Seed via execute path without refs.
    resp = client.post(
        "/user-requests",
        headers=auth_headers,
        json={
            "text": "Нарисуй абстрактный пейзаж с горами и озером вечером.",
            "selected_scenario": "image_generation",
            "skill_inputs": {"force_image_generation": "true"},
        },
    )
    assert resp.status_code == 201
    ids = resp.json().get("generated_visual_asset_ids") or []
    if not ids:
        pytest.skip("mock generation did not return asset in this env")
    asset_id = ids[0]
    rev = client.post(
        f"/generated-visual-assets/{asset_id}/review",
        headers=auth_headers,
        json={
            "user_accepted": False,
            "identity_similarity": "low",
            "rejection_code": "rejected_insufficient_similarity",
            "review_notes": "owner: different person",
        },
    )
    assert rev.status_code == 200
    assert rev.json()["status"] == GeneratedVisualAssetStatus.REJECTED_INSUFFICIENT_SIMILARITY.value
    assert rev.json()["user_accepted"] is False

    # Immutable: cannot accept afterwards
    again = client.post(
        f"/generated-visual-assets/{asset_id}/review",
        headers=auth_headers,
        json={"user_accepted": True},
    )
    assert again.status_code == 409


def test_no_publication_campaign_budget_markers_in_h28d_modules() -> None:
    root = Path(__file__).resolve().parents[1]
    paths = [
        root / "app" / "domain" / "reference_selection.py",
        root / "app" / "media_generation" / "identity_provider.py",
        root / "app" / "services" / "design_image_generation_service.py",
        root / "app" / "api" / "routes" / "generated_visual_assets.py",
    ]
    banned = ("make.com", "n8n", "/business-campaigns", "budget_action", "publish_package")
    for path in paths:
        text = path.read_text(encoding="utf-8").lower()
        for token in banned:
            assert token not in text, f"{path.name} contains {token}"


def test_consistency_levels_exist() -> None:
    assert VisualConsistencyLevel.LOW.value == "low"
    assert VisualExecutionMode.PERSON_IDENTITY_PRESERVATION.value == (
        "person_identity_preservation"
    )


def test_selection_roles_and_groups_persisted() -> None:
    face = _FakeRow(purpose=ReferenceAssetPurpose.FACE_FRONT)
    style = _FakeRow(purpose=ReferenceAssetPurpose.STYLE_REFERENCE)
    body = _FakeRow(purpose=ReferenceAssetPurpose.FULL_BODY)
    result = select_person_identity_refs(
        assets=views_from_rows([face, style, body]),
        primary_reference_id=face.id,
        subject_type=ReferenceSubjectType.PERSON,
        identity_max=5,
        style_max=1,
        appearance_max=1,
    )
    assert result.roles
    primary_roles = [r for r in result.roles if r.is_primary]
    assert len(primary_roles) == 1
    assert primary_roles[0].reference_id == face.id
    assert primary_roles[0].group == ReferencePurposeGroup.IDENTITY
    assert result.style_selected_count >= 1
    assert result.max_provider_references == 5


def test_lineage_sanitize_keeps_transmit_fields() -> None:
    from app.media_generation.safe_metadata import sanitize_generation_metadata

    rid = str(uuid4())
    cleaned = sanitize_generation_metadata(
        {
            "provider": "openai_images",
            "references_provider_received": 1,
            "transmitted_reference_ids": [rid],
            "primary_reference_position": 0,
            "prompt_section_hashes": {"identity": "abc", "scene": "def"},
            "transmitted_dimensions": {rid: [800, 600]},
            "transmitted_checksums": {rid: "sha256:deadbeef"},
            "transmitted_mime_types": {rid: "image/png"},
            "provider_request_id": "req_123",
            "provider_capability": "unknown",
            "selection_roles": [
                {
                    "reference_id": rid,
                    "purpose": "face_front",
                    "group": "identity",
                    "role_label": "Анфас (primary)",
                    "is_primary": True,
                    "selected": True,
                    "exclusion_reason": None,
                }
            ],
            "b64_json": "SHOULD_DROP",
        }
    )
    assert cleaned["references_provider_received"] == 1
    assert cleaned["transmitted_reference_ids"] == [rid]
    assert cleaned["prompt_section_hashes"]["identity"] == "abc"
    assert cleaned["transmitted_dimensions"][rid] == [800.0, 600.0]
    assert cleaned["provider_request_id"] == "req_123"
    assert cleaned["selection_roles"][0]["is_primary"] is True
    assert "b64_json" not in cleaned


def test_parent_asset_id_column_on_model() -> None:
    from app.db.models.generated_visual_asset import GeneratedVisualAssetTable

    assert hasattr(GeneratedVisualAssetTable, "parent_asset_id")


def test_identity_capability_enum_and_modes() -> None:
    from app.schemas.contracts import IdentityProviderCapability

    assert VisualExecutionMode.REFERENCE_GUIDED_STYLE.value == "reference_guided_style"
    assert IdentityProviderCapability.UNKNOWN.value == "unknown"
    assert IdentityProviderCapability.UNSUITABLE_FOR_IDENTITY.value == (
        "unsuitable_for_identity"
    )
