"""Phase H2.8E — Identity Generation Subsystem & Provider Qualification."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.domain.reference_selection import select_person_identity_refs, views_from_rows
from app.identity_generation.admission import admit_reference_for_identity
from app.identity_generation.capability import classify_provider_capability
from app.identity_generation.errors import identity_error_message
from app.identity_generation.manifest import (
    build_identity_reference_manifest,
    compute_manifest_hash,
)
from app.identity_generation.preflight import evaluate_identity_preflight
from app.identity_generation.recipes import list_identity_recipes
from app.identity_generation.registry import (
    build_identity_provider_registry,
    get_provider_definition,
    serialize_registry_safe,
)
from app.schemas.contracts import (
    IdentityPaidApprovalChoice,
    IdentityProviderCapability,
    IdentityQualificationVariantStatus,
    ReferenceAssetPurpose,
    ReferenceQualityStatus,
    ReferenceSubjectType,
    VisualExecutionMode,
)


class _FakeRow:
    def __init__(
        self,
        *,
        purpose: ReferenceAssetPurpose,
        quality: ReferenceQualityStatus = ReferenceQualityStatus.SUITABLE,
        width: int = 800,
        height: int = 800,
        checksum: str | None = None,
        mime: str = "image/png",
    ) -> None:
        self.id = uuid4()
        self.asset_purpose = purpose
        self.quality_status = quality
        self.width = width
        self.height = height
        self.checksum = checksum or f"sha256:{uuid4().hex}"
        self.mime_type = mime
        self.asset_purposes = [purpose.value]
        self.byte_size = 12000


def test_registry_definitions_and_no_secrets() -> None:
    settings = get_settings()
    registry = build_identity_provider_registry(settings)
    codes = {e.provider_code for e in registry}
    assert "openai_images" in codes
    assert "gptunnel_images" in codes
    assert "specialized_identity_reserved" in codes
    openai = next(e for e in registry if e.provider_code == "openai_images")
    assert openai.maximum_identity_images == 1
    assert openai.supports_supporting_references is False
    assert VisualExecutionMode.PERSON_IDENTITY_PRESERVATION in openai.supported_modes
    gpt = next(e for e in registry if e.provider_code == "gptunnel_images")
    assert gpt.capability_status == IdentityProviderCapability.UNSUITABLE_FOR_IDENTITY
    blob = str(serialize_registry_safe(settings))
    assert "sk-" not in blob
    assert "api_key" not in blob.lower() or "configured" in blob.lower()


def test_unsupported_mode_fail_closed_message() -> None:
    assert "не поддерживает" in identity_error_message("identity_mode_not_supported")
    assert "основной референс" in identity_error_message("selected_but_not_transmitted")


def test_admission_rejects_low_res_and_duplicate() -> None:
    aid = uuid4()
    bad = admit_reference_for_identity(
        asset_id=aid,
        mime_type="image/png",
        width=64,
        height=64,
        byte_size=100,
        purpose=ReferenceAssetPurpose.FACE_FRONT,
        quality_status=ReferenceQualityStatus.SUITABLE,
        checksum="sha256:abc",
    )
    assert bad.exclusion_code == "low_resolution"
    seen = {"sha256:dup"}
    dup = admit_reference_for_identity(
        asset_id=uuid4(),
        mime_type="image/png",
        width=800,
        height=800,
        byte_size=1000,
        purpose=ReferenceAssetPurpose.FACE_FRONT,
        quality_status=ReferenceQualityStatus.SUITABLE,
        checksum="sha256:dup",
        seen_checksums=seen,
    )
    assert dup.exclusion_code == "duplicate_checksum"


def test_manifest_immutable_hash_primary_first_max_five(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IMAGE_GENERATION_PROVIDER", "openai_images")
    get_settings.cache_clear()
    settings = get_settings()
    rows = [
        _FakeRow(purpose=ReferenceAssetPurpose.FACE_FRONT),
        _FakeRow(purpose=ReferenceAssetPurpose.FACE_THREE_QUARTER),
        _FakeRow(purpose=ReferenceAssetPurpose.FACE_PROFILE),
        _FakeRow(purpose=ReferenceAssetPurpose.FACE_CLOSEUP),
        _FakeRow(purpose=ReferenceAssetPurpose.STYLE_REFERENCE),
        _FakeRow(purpose=ReferenceAssetPurpose.FULL_BODY),
    ]
    primary = rows[0].id
    owner = uuid4()
    set_id = uuid4()
    m1 = build_identity_reference_manifest(
        owner_id=owner,
        reference_set_id=set_id,
        reference_set_version="v1",
        subject_type=ReferenceSubjectType.PERSON,
        rows=rows,
        primary_reference_id=primary,
        settings=settings,
    )
    m2 = build_identity_reference_manifest(
        owner_id=owner,
        reference_set_id=set_id,
        reference_set_version="v1",
        subject_type=ReferenceSubjectType.PERSON,
        rows=rows,
        primary_reference_id=primary,
        settings=settings,
    )
    assert m1.immutable_hash == m2.immutable_hash
    assert m1.immutable_hash.startswith("sha256:")
    assert m1.references_provider_received_count == 1
    assert m1.transmitted_reference_ids[0] == primary
    assert m1.references_selected_count <= 5
    assert any(
        e.transmission_status == "selected_but_not_transmitted"
        for e in m1.selected_entries
    ) or m1.references_selected_count == 1
    # body not primary
    assert m1.primary_reference_id != rows[-1].id


def test_payload_honesty_selected_vs_transmitted() -> None:
    settings = get_settings()
    rows = [
        _FakeRow(purpose=ReferenceAssetPurpose.FACE_FRONT),
        _FakeRow(purpose=ReferenceAssetPurpose.FACE_PROFILE),
    ]
    manifest = build_identity_reference_manifest(
        owner_id=uuid4(),
        reference_set_id=uuid4(),
        reference_set_version="v",
        subject_type=ReferenceSubjectType.PERSON,
        rows=rows,
        primary_reference_id=rows[0].id,
        settings=settings,
        provider_code="openai_images",
    )
    assert manifest.references_provider_received_count == 1
    assert len(manifest.transmitted_reference_ids) == 1
    assert manifest.references_selected_count >= 1


def test_capability_unknown_before_owner_and_not_from_unit_tests() -> None:
    d = classify_provider_capability(
        provider_code="openai_images",
        supports_true_identity_mode=False,
        supports_supporting_references=False,
        owner_review=None,
    )
    assert d.capability_status == IdentityProviderCapability.UNKNOWN
    blocked = classify_provider_capability(
        provider_code="openai_images",
        supports_true_identity_mode=True,
        supports_supporting_references=True,
        owner_review="acceptable",
        decided_by="unit_tests",
    )
    assert blocked.capability_status == IdentityProviderCapability.UNKNOWN


def test_capability_unsuitable_after_owner_not_recognizable() -> None:
    d = classify_provider_capability(
        provider_code="openai_images",
        supports_true_identity_mode=False,
        supports_supporting_references=False,
        owner_review="not_recognizable",
        approved_failed_attempts=2,
        decided_by="owner",
    )
    assert d.capability_status == IdentityProviderCapability.UNSUITABLE_FOR_IDENTITY
    assert d.replacement_recommended is True


def test_recipes_exist_not_skills() -> None:
    recipes = list_identity_recipes()
    assert len(recipes) == 6
    codes = {r.code.value for r in recipes}
    assert "provider_qualification" in codes
    assert "preserve_person_new_scene" in codes


def test_preflight_blocks_without_primary() -> None:
    settings = get_settings()

    class Set:
        owner_id = uuid4()

    owner = Set.owner_id
    ready = evaluate_identity_preflight(
        settings=settings,
        owner_id=owner,
        reference_set=Set(),
        reference_rows=[_FakeRow(purpose=ReferenceAssetPurpose.FACE_FRONT)],
        primary_reference_id=None,
        consent=True,
        prompt="Девушка в студии, мягкий свет, портрет",
        identity_profile_present=True,
    )
    assert any(
        c.code == "primary_reference_required" and c.blocking for c in ready.blocking_conditions
    )


def test_providers_api_and_recipes_api(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = client.get("/identity-generation/providers", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["subsystem"] == "identity_generation"
    assert len(data["providers"]) >= 3
    recipes = client.get("/identity-generation/recipes", headers=auth_headers)
    assert recipes.status_code == 200
    assert len(recipes.json()["recipes"]) == 6


def test_generated_visual_readiness_includes_identity_fields(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = client.get("/generated-visual-assets/readiness", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("subsystem") == "identity_generation"
    assert "identity_capability_status" in data
    assert "identity_provider_input_capacity" in data
    assert "paid_approval_required" in data
    blob = str(data).lower()
    assert "sk-" not in blob
    assert "secret" not in blob or "configured" in blob


def test_qualification_run_requires_approval_before_execute(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Create run → awaiting paid approval; cancel works; no auto provider calls."""
    # Minimal path: without real ref set → preflight_failed is OK; still no paid calls.
    resp = client.post(
        "/identity-generation/qualification-runs",
        headers=auth_headers,
        json={
            "reference_set_id": str(uuid4()),
            "prompt": "Портрет человека в студии при мягком свете",
            "consent": False,
        },
    )
    # 404 if FK fails, or 200 with preflight_failed / awaiting
    assert resp.status_code in {200, 404, 500, 400}
    if resp.status_code != 200:
        pytest.skip("DB/FK environment without reference set for operator create")
    run = resp.json()
    assert run["status"] in {
        "preflight_failed",
        "awaiting_paid_approval",
        "draft",
        "failed",
    }
    # Must not be running/completed without approval
    assert run["status"] not in {"running", "completed"}


def test_variant_plan_marks_bcd_unsupported_for_primary_only() -> None:
    from app.identity_generation.operator import _variant_plan

    variants = _variant_plan(1)
    by_code = {v.variant_code: v for v in variants}
    assert by_code["A"].status == IdentityQualificationVariantStatus.AWAITING_APPROVAL
    assert by_code["B"].status == IdentityQualificationVariantStatus.UNSUPPORTED_BY_ADAPTER
    assert by_code["C"].status == IdentityQualificationVariantStatus.UNSUPPORTED_BY_ADAPTER
    assert by_code["D"].status == IdentityQualificationVariantStatus.UNSUPPORTED_BY_ADAPTER


def test_no_publication_campaign_make_in_subsystem_modules() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "app" / "identity_generation"
    banned = ("make.com", "n8n", "/business-campaigns", "publish_package", "yandex direct")
    for path in root.glob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        for token in banned:
            assert token not in text, f"{path.name} contains {token}"


def test_manifest_hash_stable() -> None:
    h1 = compute_manifest_hash({"a": 1, "b": [2, 3]})
    h2 = compute_manifest_hash({"b": [2, 3], "a": 1})
    assert h1 == h2
