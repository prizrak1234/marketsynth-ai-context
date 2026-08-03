"""Phase H2.6A-R — reference uploads, limits, selection, isolation."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.reference_images.service import assess_reference_quality
from app.schemas.contracts import (
    ReferenceAssetPurpose,
    ReferenceQualityStatus,
    ReferenceSubjectType,
)


def _png_bytes(w: int = 512, h: int = 512, color=(30, 90, 140)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, format="PNG")
    return buf.getvalue()


def _jpeg_with_exif() -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (512, 512), (40, 80, 120))
    # Pillow may ignore unknown EXIF; we still re-encode without metadata on upload.
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def test_quality_assessment_unsuitable_small() -> None:
    q = assess_reference_quality(
        width=100,
        height=100,
        byte_size=1000,
        purpose=ReferenceAssetPurpose.FACE_REFERENCE,
        subject_type=ReferenceSubjectType.PERSON,
        min_w=256,
        min_h=256,
    )
    assert q.status == ReferenceQualityStatus.UNSUITABLE


def test_honest_copy_never_promises_100(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    limits = client.get("/reference-visual-assets/limits", headers=auth_headers)
    assert limits.status_code == 200
    body = limits.json()
    blob = (body.get("honest_copy_ru") or "") + (body.get("identity_promise") or "")
    assert "100%" not in blob
    assert "гарант" not in blob.lower()
    assert body["identity_promise"] == "maximize_not_guarantee"


def test_upload_limits_and_isolation(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("REFERENCE_IMAGE_MAX_COUNT", "3")
    monkeypatch.setenv("REFERENCE_PROVIDER_MAX_IMAGES", "2")
    monkeypatch.setenv("REFERENCE_IMAGE_STORAGE_DIR", str(tmp_path / "refs"))
    monkeypatch.setenv("REFERENCE_IMAGE_MIN_WIDTH", "256")
    monkeypatch.setenv("REFERENCE_IMAGE_MIN_HEIGHT", "256")
    from app.core.config import get_settings

    get_settings.cache_clear()

    limits = client.get("/reference-visual-assets/limits", headers=auth_headers)
    assert limits.status_code == 200
    assert limits.json()["max_count"] == 3

    created = client.post(
        "/reference-sets",
        headers=auth_headers,
        json={
            "title": "Person set",
            "subject_type": "person",
            "consent_confirmed": True,
            "immutable_traits": ["hair", "face shape"],
        },
    )
    assert created.status_code == 201, created.text
    set_id = created.json()["id"]

    tiny = client.post(
        f"/reference-sets/{set_id}/assets",
        headers=auth_headers,
        files={"file": ("tiny.png", _png_bytes(64, 64), "image/png")},
        data={
            "asset_purpose": "face_reference",
            "subject_type": "person",
            "consent_confirmed": "true",
        },
    )
    assert tiny.status_code == 400
    assert tiny.json()["error_code"] == "dimensions_too_small"

    bad = client.post(
        f"/reference-sets/{set_id}/assets",
        headers=auth_headers,
        files={"file": ("x.txt", b"not-an-image", "text/plain")},
        data={"asset_purpose": "other", "subject_type": "mixed", "consent_confirmed": "true"},
    )
    assert bad.status_code == 400
    assert bad.json()["error_code"] == "unsupported_mime"

    corrupt = client.post(
        f"/reference-sets/{set_id}/assets",
        headers=auth_headers,
        files={"file": ("bad.png", b"\x89PNG\r\n\x1a\n" + b"xxxx", "image/png")},
        data={"asset_purpose": "other", "subject_type": "mixed", "consent_confirmed": "true"},
    )
    assert corrupt.status_code == 400
    assert corrupt.json()["error_code"] == "corrupt_image"

    first_bytes = _png_bytes(512, 512, (10, 20, 30))
    up1 = client.post(
        f"/reference-sets/{set_id}/assets",
        headers=auth_headers,
        files={"file": ("p0.png", first_bytes, "image/png")},
        data={
            "asset_purpose": "face_reference",
            "subject_type": "person",
            "consent_confirmed": "true",
        },
    )
    assert up1.status_code == 201, up1.text
    first_id = up1.json()["id"]
    assert up1.json()["checksum"].startswith("sha256:")

    # EXIF path: JPEG re-encoded without GPS metadata retention
    jpeg_up = client.post(
        f"/reference-sets/{set_id}/assets",
        headers=auth_headers,
        files={"file": ("p1.jpg", _jpeg_with_exif(), "image/jpeg")},
        data={
            "asset_purpose": "body_reference",
            "subject_type": "person",
            "consent_confirmed": "true",
        },
    )
    assert jpeg_up.status_code == 201, jpeg_up.text

    dup = client.post(
        f"/reference-sets/{set_id}/assets",
        headers=auth_headers,
        files={"file": ("again.png", first_bytes, "image/png")},
        data={
            "asset_purpose": "face_reference",
            "subject_type": "person",
            "consent_confirmed": "true",
        },
    )
    assert dup.status_code == 400
    assert dup.json()["error_code"] == "duplicate_checksum"

    up3 = client.post(
        f"/reference-sets/{set_id}/assets",
        headers=auth_headers,
        files={"file": ("p2.png", _png_bytes(640, 640, (90, 40, 10)), "image/png")},
        data={
            "asset_purpose": "style_reference",
            "subject_type": "person",
            "consent_confirmed": "true",
        },
    )
    assert up3.status_code == 201, up3.text

    fourth = client.post(
        f"/reference-sets/{set_id}/assets",
        headers=auth_headers,
        files={"file": ("p3.png", _png_bytes(600, 600, (1, 2, 3)), "image/png")},
        data={
            "asset_purpose": "other",
            "subject_type": "person",
            "consent_confirmed": "true",
        },
    )
    assert fourth.status_code == 400
    assert fourth.json()["error_code"] == "set_full"

    patch = client.patch(
        f"/reference-sets/{set_id}",
        headers=auth_headers,
        json={"primary_reference_id": first_id},
    )
    assert patch.status_code == 200
    assert patch.json()["primary_reference_id"] == first_id

    selection = client.get(
        f"/reference-sets/{set_id}/selection",
        headers=auth_headers,
    )
    assert selection.status_code == 200
    sel = selection.json()
    assert sel["max_provider_references"] == 2
    assert len(sel["selected_reference_ids"]) <= 2
    assert first_id in sel["selected_reference_ids"]
    assert "Использовано" in sel["selection_summary"]

    other = client.get(f"/reference-sets/{set_id}", headers=other_auth_headers)
    assert other.status_code == 404
    other_content = client.get(
        f"/reference-visual-assets/{first_id}/content",
        headers=other_auth_headers,
    )
    assert other_content.status_code == 404

    own = client.get(
        f"/reference-visual-assets/{first_id}/content",
        headers=auth_headers,
    )
    assert own.status_code == 200
    assert own.content[:8] == b"\x89PNG\r\n\x1a\n"
    # Re-encoded PNG should not carry GPS EXIF chunks
    assert b"GPS" not in own.content


def test_upload_fifteen_accept_sixteenth_reject(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Local upload-contour acceptance only — not a real provider Product Gate."""
    monkeypatch.setenv("REFERENCE_IMAGE_MAX_COUNT", "15")
    monkeypatch.setenv("REFERENCE_PROVIDER_MAX_IMAGES", "10")
    monkeypatch.setenv("REFERENCE_IMAGE_STORAGE_DIR", str(tmp_path / "refs15"))
    from app.core.config import get_settings

    get_settings.cache_clear()

    created = client.post(
        "/reference-sets",
        headers=auth_headers,
        json={
            "title": "Fifteen set",
            "subject_type": "person",
            "consent_confirmed": True,
        },
    )
    assert created.status_code == 201
    set_id = created.json()["id"]

    uploaded: list[str] = []
    for i in range(15):
        color = (10 + i * 7) % 256, (40 + i * 11) % 256, (80 + i * 13) % 256
        up = client.post(
            f"/reference-sets/{set_id}/assets",
            headers=auth_headers,
            files={"file": (f"r{i}.png", _png_bytes(320 + i, 320 + i, color), "image/png")},
            data={
                "asset_purpose": "face_reference" if i == 0 else "other",
                "subject_type": "person",
                "consent_confirmed": "true",
            },
        )
        assert up.status_code == 201, up.text
        uploaded.append(up.json()["id"])

    primary = client.patch(
        f"/reference-sets/{set_id}",
        headers=auth_headers,
        json={"primary_reference_id": uploaded[0]},
    )
    assert primary.status_code == 200

    # Persist after "refresh"
    refreshed = client.get(f"/reference-sets/{set_id}", headers=auth_headers)
    assert refreshed.status_code == 200
    assert len(refreshed.json()["reference_asset_ids"]) == 15
    assert refreshed.json()["primary_reference_id"] == uploaded[0]

    listed = client.get(f"/reference-sets/{set_id}/assets", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 15

    selection = client.get(f"/reference-sets/{set_id}/selection", headers=auth_headers)
    assert selection.status_code == 200
    sel = selection.json()
    assert sel["max_provider_references"] == 10
    assert len(sel["selected_reference_ids"]) == 10
    assert len(sel["excluded_reference_ids"]) == 5
    assert uploaded[0] in sel["selected_reference_ids"]
    assert "Использовано 10 из 15" in sel["selection_summary"]

    sixteenth = client.post(
        f"/reference-sets/{set_id}/assets",
        headers=auth_headers,
        files={"file": ("r15.png", _png_bytes(400, 400, (1, 2, 3)), "image/png")},
        data={
            "asset_purpose": "other",
            "subject_type": "person",
            "consent_confirmed": "true",
        },
    )
    assert sixteenth.status_code == 400
    assert sixteenth.json()["error_code"] == "set_full"


def test_archive_set(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("REFERENCE_IMAGE_STORAGE_DIR", str(tmp_path / "refs"))
    from app.core.config import get_settings

    get_settings.cache_clear()
    created = client.post(
        "/reference-sets",
        headers=auth_headers,
        json={"title": "T", "subject_type": "mixed", "consent_confirmed": True},
    )
    set_id = created.json()["id"]
    deleted = client.delete(f"/reference-sets/{set_id}", headers=auth_headers)
    assert deleted.status_code == 204
    got = client.get(f"/reference-sets/{set_id}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["status"] == "archived"
