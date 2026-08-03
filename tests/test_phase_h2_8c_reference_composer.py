"""Phase H2.8C — reference composer UX + explicit image generation routing."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.domain.user_request_routing import route_user_request
from app.schemas.contracts import UserRequestRouteCategory, UserRequestRouteKind


def _png_bytes(w: int = 512, h: int = 512, color=(30, 90, 140)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, format="PNG")
    return buf.getvalue()


def test_routing_refs_plus_scene_prompt_is_image_not_clarify() -> None:
    decision = route_user_request(
        "Взрослая женщина в образе героини тёмного фэнтези, кинематографический портрет, "
        "чёрно-красная палитра, сохрани лицо и возраст",
        has_reference_set=True,
    )
    assert decision.category == UserRequestRouteCategory.IMAGE_GENERATION
    assert decision.kind == UserRequestRouteKind.SPECIALIST_TASK
    assert "слишком общий" not in (decision.assistant_message or "").lower()


def test_routing_without_refs_still_clarify_for_vague() -> None:
    decision = route_user_request("нужна реклама")
    assert decision.kind == UserRequestRouteKind.CLARIFY


def test_selected_scenario_image_generation_forces_route() -> None:
    decision = route_user_request(
        "портрет в стиле dark fantasy",
        selected_scenario="image_generation",
    )
    assert decision.category == UserRequestRouteCategory.IMAGE_GENERATION
    assert decision.kind == UserRequestRouteKind.SPECIALIST_TASK


def test_per_reference_purpose_and_profile_persist(
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
        json={
            "title": "Composer",
            "subject_type": "person",
            "consent_confirmed": True,
            "immutable_traits": ["facial_geometry", "eye_shape", "skin_tone"],
            "allowed_variations": ["clothing", "lighting", "background"],
        },
    )
    assert created.status_code == 201, created.text
    set_id = created.json()["id"]
    assert created.json()["immutable_traits"] == [
        "facial_geometry",
        "eye_shape",
        "skin_tone",
    ]

    up = client.post(
        f"/reference-sets/{set_id}/assets",
        headers=auth_headers,
        files={"file": ("front.png", _png_bytes(400, 400), "image/png")},
        data={
            "asset_purpose": "face_front",
            "subject_type": "person",
            "consent_confirmed": "true",
        },
    )
    assert up.status_code == 201, up.text
    asset_id = up.json()["id"]
    assert up.json()["asset_purpose"] == "face_front"

    patched = client.patch(
        f"/reference-visual-assets/{asset_id}",
        headers=auth_headers,
        json={
            "asset_purpose": "face_three_quarter",
            "asset_purposes": ["face_three_quarter", "style_reference"],
        },
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["asset_purpose"] == "face_three_quarter"
    assert "face_three_quarter" in patched.json()["asset_purposes"]
    assert "style_reference" in patched.json()["asset_purposes"]

    set_patch = client.patch(
        f"/reference-sets/{set_id}",
        headers=auth_headers,
        json={
            "primary_reference_id": asset_id,
            "immutable_traits": [
                "facial_geometry",
                "face_shape",
                "eye_shape",
                "nose_shape",
                "lip_shape",
                "skin_tone",
                "apparent_age",
                "distinctive_features",
            ],
            "allowed_variations": ["clothing", "pose", "lighting", "background"],
        },
    )
    assert set_patch.status_code == 200, set_patch.text
    body = set_patch.json()
    assert body["primary_reference_id"] == asset_id
    assert len(body["immutable_traits"]) == 8
    assert "clothing" in body["allowed_variations"]


def test_force_image_generation_skill_input_creates_image_route(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("REFERENCE_IMAGE_STORAGE_DIR", str(tmp_path / "refs"))
    monkeypatch.setenv("REFERENCE_IMAGE_MIN_WIDTH", "256")
    monkeypatch.setenv("REFERENCE_IMAGE_MIN_HEIGHT", "256")
    monkeypatch.setenv("IMAGE_GENERATION_ENABLED", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()

    created = client.post(
        "/reference-sets",
        headers=auth_headers,
        json={"title": "G", "subject_type": "person", "consent_confirmed": True},
    )
    set_id = created.json()["id"]
    up = client.post(
        f"/reference-sets/{set_id}/assets",
        headers=auth_headers,
        files={"file": ("a.png", _png_bytes(400, 400), "image/png")},
        data={
            "asset_purpose": "face_front",
            "subject_type": "person",
            "consent_confirmed": "true",
        },
    )
    assert up.status_code == 201

    # First: stale generic clarify
    vague = client.post(
        "/user-requests",
        headers=auth_headers,
        json={"text": "нужна реклама", "source": "home_conversation"},
    )
    assert vague.status_code == 201
    assert vague.json()["status"] == "needs_clarification"

    # Explicit composer generate — must not stay trapped in generic clarify.
    prompt = (
        "Создай фотореалистичный кинематографический портрет взрослой женщины "
        "в образе героини тёмного фэнтези. Сохрани лицо, возраст и цвет кожи."
    )
    gen = client.post(
        "/user-requests",
        headers=auth_headers,
        json={
            "text": prompt,
            "selected_scenario": "image_generation",
            "source": "home_conversation",
            "skill_inputs": {
                "reference_set_id": set_id,
                "force_image_generation": "true",
                "identity_fidelity": "maximum",
                "style_freedom": "low",
                "preserve_traits": "facial_geometry,eye_shape,skin_tone,apparent_age",
                "allowed_changes": "clothing,lighting,background",
            },
        },
    )
    assert gen.status_code == 201, gen.text
    body = gen.json()
    assert body["route_category"] == "image_generation"
    assert body["status"] != "needs_clarification" or body.get("skill_code")
    assert body["skill_code"] in {
        None,
        "design.image_generation",
        "image.generate_visual",
    } or "image" in str(body.get("skill_code") or "")
    # Must not echo the generic ambiguous ads message.
    assert "слишком общий" not in (body.get("assistant_message") or "").lower()
    assert body["skill_inputs"]["reference_set_id"] == set_id


def test_identity_profile_from_composer_traits() -> None:
    from app.domain.identity_preservation import build_identity_profile

    profile = build_identity_profile(
        primary_reference_id=None,
        reference_asset_ids=[],
        immutable_traits=["facial_geometry", "eye_shape"],
        allowed_variations=["clothing", "lighting"],
        strengthen_mode=True,
    )
    assert profile.strengthen_mode is True
    assert "clothing" in profile.allowed_changes
    assert profile.version == "1.0"


def test_no_campaign_publish_in_h28c_files() -> None:
    root = Path(__file__).resolve().parents[1]
    paths = [
        root / "web" / "src" / "lib" / "home" / "image-generation-composer.ts",
        root / "web" / "src" / "components" / "workspace" / "home" / "reference-upload-panel.tsx",
        root / "app" / "domain" / "user_request_routing.py",
    ]
    banned = ("make.com", "n8n", "/business-campaigns", "budget_action")
    for path in paths:
        text = path.read_text(encoding="utf-8").lower()
        for token in banned:
            assert token not in text, f"{path.name} contains {token}"
