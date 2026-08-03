"""Phase H2.8B — reference fidelity hardening (dedupe UX, identity profile, review gate)."""

from __future__ import annotations

import io
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.domain.identity_preservation import (
    assess_visual_consistency_assist,
    build_identity_profile,
    build_identity_prompt_sections,
    consistency_user_message,
)
from app.schemas.contracts import (
    GeneratedVisualAssetStatus,
    VisualConsistencyLevel,
)
from app.services.design_image_generation_service import (
    MSG_LOW_IDENTITY,
    MSG_REAL_SUCCESS,
    MSG_REAL_SUCCESS_WITH_REFS,
    apply_generation_success,
)


def _png_bytes(w: int = 512, h: int = 512, color=(30, 90, 140)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, format="PNG")
    return buf.getvalue()


def test_identity_prompt_sections_structure() -> None:
    profile = build_identity_profile(
        primary_reference_id=uuid4(),
        reference_asset_ids=[uuid4(), uuid4()],
        strengthen_mode=True,
    )
    text = build_identity_prompt_sections(
        scene_prompt="Dark fantasy cinematic portrait of an adult woman",
        profile=profile,
    )
    assert "IDENTITY:" in text
    assert "SCENE:" in text
    assert "STYLE:" in text
    assert "NEGATIVE CONSTRAINTS:" in text
    assert "Increase identity priority" in text
    assert profile.version == "1.0"
    assert "artistic_setting" not in profile.allowed_changes


def test_consistency_assist_never_biometric() -> None:
    low = assess_visual_consistency_assist(
        used_reference_count=1,
        strengthen_mode=False,
        generation_mode="reference_guided_generation",
    )
    assert low == VisualConsistencyLevel.LOW
    msg = consistency_user_message(low)
    assert msg is not None
    assert "biometric" not in msg.lower()
    assert "verified" not in msg.lower()
    assert "Готово" not in (msg or "")

    unavailable = assess_visual_consistency_assist(
        used_reference_count=0,
        strengthen_mode=False,
        generation_mode="text_to_image",
    )
    assert unavailable == VisualConsistencyLevel.UNAVAILABLE


def test_apply_generation_success_awaits_identity_review(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Row:
        generated_visual_asset_ids: list[str] = []
        generation_status = None
        assistant_message = None
        generation_warnings: list[str] = []
        status = None
        next_action_label = None
        next_href = None
        updated_at = None

    class _Asset:
        id = uuid4()
        generation_mode = "real"
        asset_type = "user_result"
        prompt_summary = "dark fantasy portrait"
        used_reference_ids = [str(uuid4()), str(uuid4())]
        generation_metadata = {
            "_used_refs": True,
            "visual_consistency": VisualConsistencyLevel.LOW.value,
        }
        status = GeneratedVisualAssetStatus.SUCCEEDED
        user_accepted = None
        review_notes = None

    from app.schemas.contracts import (
        GeneratedVisualAssetType,
        GeneratedVisualGenerationMode,
    )

    row = _Row()
    asset = _Asset()
    asset.generation_mode = GeneratedVisualGenerationMode.REAL
    asset.asset_type = GeneratedVisualAssetType.USER_RESULT

    apply_generation_success(row, asset)  # type: ignore[arg-type]
    assert row.generation_status == GeneratedVisualAssetStatus.AWAITING_IDENTITY_REVIEW.value
    assert asset.status == GeneratedVisualAssetStatus.AWAITING_IDENTITY_REVIEW
    assert "Готово" not in (row.assistant_message or "")
    assert MSG_LOW_IDENTITY[:40] in (row.assistant_message or "")
    assert "awaiting_identity_review" in (row.generation_warnings or [])
    assert "low_identity_consistency" in (row.generation_warnings or [])


def test_apply_generation_success_without_refs_still_done() -> None:
    from app.schemas.contracts import (
        GeneratedVisualAssetType,
        GeneratedVisualGenerationMode,
    )

    class _Row:
        generated_visual_asset_ids: list[str] = []
        generation_status = None
        assistant_message = None
        generation_warnings: list[str] = []
        status = None
        next_action_label = None
        next_href = None
        updated_at = None

    class _Asset:
        id = uuid4()
        generation_mode = GeneratedVisualGenerationMode.REAL
        asset_type = GeneratedVisualAssetType.USER_RESULT
        prompt_summary = "simple landscape"
        used_reference_ids: list[str] = []
        generation_metadata: dict = {"_used_refs": False}
        status = GeneratedVisualAssetStatus.SUCCEEDED
        user_accepted = None
        review_notes = None

    row = _Row()
    asset = _Asset()
    apply_generation_success(row, asset)  # type: ignore[arg-type]
    assert row.generation_status == GeneratedVisualAssetStatus.SUCCEEDED.value
    assert MSG_REAL_SUCCESS in (row.assistant_message or "")
    assert MSG_REAL_SUCCESS_WITH_REFS not in (row.assistant_message or "")


def test_duplicate_already_attached_and_cross_set_reuse(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("REFERENCE_IMAGE_STORAGE_DIR", str(tmp_path / "refs"))
    monkeypatch.setenv("REFERENCE_IMAGE_MIN_WIDTH", "256")
    monkeypatch.setenv("REFERENCE_IMAGE_MIN_HEIGHT", "256")
    from app.core.config import get_settings

    get_settings.cache_clear()

    set_a = client.post(
        "/reference-sets",
        headers=auth_headers,
        json={"title": "A", "subject_type": "person", "consent_confirmed": True},
    )
    assert set_a.status_code == 201
    set_a_id = set_a.json()["id"]

    payload = _png_bytes(520, 520, (11, 22, 33))
    up = client.post(
        f"/reference-sets/{set_a_id}/assets",
        headers=auth_headers,
        files={"file": ("face.png", payload, "image/png")},
        data={
            "asset_purpose": "face_reference",
            "subject_type": "person",
            "consent_confirmed": "true",
        },
    )
    assert up.status_code == 201
    asset_id = up.json()["id"]
    assert up.json().get("attach_status") in {None, "created"}

    again = client.post(
        f"/reference-sets/{set_a_id}/assets",
        headers=auth_headers,
        files={"file": ("face-again.png", payload, "image/png")},
        data={
            "asset_purpose": "face_reference",
            "subject_type": "person",
            "consent_confirmed": "true",
        },
    )
    assert again.status_code == 201
    assert again.json()["attach_status"] == "already_attached"
    assert again.json()["id"] == asset_id
    listed = client.get(f"/reference-sets/{set_a_id}/assets", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    set_b = client.post(
        "/reference-sets",
        headers=auth_headers,
        json={"title": "B", "subject_type": "person", "consent_confirmed": True},
    )
    set_b_id = set_b.json()["id"]
    reuse = client.post(
        f"/reference-sets/{set_b_id}/assets",
        headers=auth_headers,
        files={"file": ("face-reuse.png", payload, "image/png")},
        data={
            "asset_purpose": "face_reference",
            "subject_type": "person",
            "consent_confirmed": "true",
        },
    )
    assert reuse.status_code == 201
    assert reuse.json()["attach_status"] == "reused_existing_asset"
    assert reuse.json()["id"] == asset_id
    assert "повторно" in (reuse.json().get("attach_message") or "").lower()

    # Cross-owner: other user uploading same bytes must not learn about owner asset.
    other_set = client.post(
        "/reference-sets",
        headers=other_auth_headers,
        json={"title": "Other", "subject_type": "person", "consent_confirmed": True},
    )
    assert other_set.status_code == 201
    other_up = client.post(
        f"/reference-sets/{other_set.json()['id']}/assets",
        headers=other_auth_headers,
        files={"file": ("x.png", payload, "image/png")},
        data={
            "asset_purpose": "face_reference",
            "subject_type": "person",
            "consent_confirmed": "true",
        },
    )
    assert other_up.status_code == 201
    assert other_up.json()["id"] != asset_id
    assert other_up.json().get("attach_status") in {None, "created"}

    leak = client.get(f"/reference-visual-assets/{asset_id}", headers=other_auth_headers)
    assert leak.status_code == 404


def test_selection_summary_recommends_more_angles(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("REFERENCE_IMAGE_STORAGE_DIR", str(tmp_path / "refs"))
    monkeypatch.setenv("REFERENCE_IMAGE_MIN_WIDTH", "256")
    monkeypatch.setenv("REFERENCE_IMAGE_MIN_HEIGHT", "256")
    from app.core.config import get_settings

    get_settings.cache_clear()

    created = client.post(
        "/reference-sets",
        headers=auth_headers,
        json={"title": "Few", "subject_type": "person", "consent_confirmed": True},
    )
    set_id = created.json()["id"]
    up = client.post(
        f"/reference-sets/{set_id}/assets",
        headers=auth_headers,
        files={"file": ("one.png", _png_bytes(400, 400), "image/png")},
        data={
            "asset_purpose": "face_reference",
            "subject_type": "person",
            "consent_confirmed": "true",
        },
    )
    assert up.status_code == 201
    sel = client.get(f"/reference-sets/{set_id}/selection", headers=auth_headers)
    assert sel.status_code == 200
    summary = sel.json()["selection_summary"]
    assert "Загружено: 1" in summary or "Использовано 1" in summary
    assert "других ракурсов" in summary or "анфас" in summary or "¾" in summary


def test_no_publication_campaign_budget_markers_in_h28b_modules() -> None:
    """Guard: H2.8B must not introduce publication / campaign / budget actions."""
    root = Path(__file__).resolve().parents[1]
    paths = [
        root / "app" / "domain" / "identity_preservation.py",
        root / "app" / "reference_images" / "service.py",
        root / "app" / "services" / "design_image_generation_service.py",
    ]
    banned = ("make.com", "n8n", "/business-campaigns", "budget_action", "publish_package")
    for path in paths:
        text = path.read_text(encoding="utf-8").lower()
        for token in banned:
            assert token not in text, f"{path.name} contains {token}"
