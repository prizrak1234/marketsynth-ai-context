"""Recovery R3.2 — foundation UI wiring static checks."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "web" / "src"


def _read(relative: str) -> str:
    return (WEB_ROOT / relative).read_text(encoding="utf-8")


def test_recovery_r3_preview_route_exists() -> None:
    page = REPO_ROOT / "web" / "src" / "app" / "(product)" / "workspace" / "recovery-preview" / "r3" / "page.tsx"
    assert page.is_file()
    assert "RecoveryPreviewR3View" in page.read_text(encoding="utf-8")


def test_recovery_r3_path_constant() -> None:
    source = _read("lib/home/recovery-preview.ts")
    assert 'RECOVERY_PREVIEW_R3_PATH = "/workspace/recovery-preview/r3"' in source


def test_foundation_api_clients_present() -> None:
    packages = _read("lib/api/endpoints/publication-packages.ts")
    jobs = _read("lib/api/endpoints/publication-package-jobs.ts")
    channels = _read("lib/api/endpoints/publishing-foundation-channels.ts")
    assets = _read("lib/api/endpoints/content-assets.ts")

    assert "submitPublicationPackageForReview" in packages
    assert "approvePublicationPackage" in packages
    assert "executePublicationPackageJobDryRun" in jobs
    assert "schedulePublicationPackageJob" in jobs
    assert "createPublicationPackageJob" in jobs
    assert "fetchPublishingFoundationChannels" in channels
    assert "fetchContentAssets" in assets


def test_content_factory_ui_uses_foundation_clients_only() -> None:
    panel = _read("components/content-factory/content-factory-panel.tsx")
    publish = _read("components/content-factory/content-factory-publish-panel.tsx")
    package = _read("components/content-factory/content-factory-package-panel.tsx")

    for source in (panel, publish, package):
        assert "createPublicationJob" not in source
        assert 'from "@/lib/api/endpoints/publishing"' not in source
        assert "fetchPublishingChannels" not in source


def test_owner_facing_labels_hide_internal_enums() -> None:
    ru = (REPO_ROOT / "web" / "src" / "lib" / "i18n" / "translations" / "ru.ts").read_text(
        encoding="utf-8",
    )

    assert "dry_run_succeeded: \"Предпросмотр готов\"" in ru
    assert "ContentAsset" not in ru.split("contentFactory")[1]
    assert "PublicationPackageJob" not in ru.split("contentFactory")[1]


def test_publish_panel_selects_existing_channel_only() -> None:
    publish = _read("components/content-factory/content-factory-publish-panel.tsx")
    assert "createPublishingFoundationChannel" not in publish
    assert "updatePublishingFoundationChannel" not in publish
    assert "content-factory-channel-select" in publish


def test_demo_materials_disclaimer_exact() -> None:
    ru = (REPO_ROOT / "web" / "src" / "lib" / "i18n" / "translations" / "ru.ts").read_text(
        encoding="utf-8",
    )
    assert (
        "Демонстрационные материалы для приёмки. Не являются результатом реальной генерации."
        in ru
    )
    legacy = _read("components/assets/schedule-publication-form.tsx")
    assert "Legacy publication scheduling" in legacy
    assert "PublicationJob" in legacy


def test_developer_panel_links_r3_preview() -> None:
    dev = _read("components/workspace/home/home-developer-panel.tsx")
    assert "RECOVERY_PREVIEW_R3_PATH" in dev
    assert "recovery-preview-r3-open" in dev


def test_content_factory_panel_has_no_mechanical_generation() -> None:
    panel = _read("components/content-factory/content-factory-panel.tsx")
    assert "generateMaterialsFromBrief" not in panel
    assert "content-factory-create-drafts" not in panel
    assert "allowDemoMaterials" in panel
