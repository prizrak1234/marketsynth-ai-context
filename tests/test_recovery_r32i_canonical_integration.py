"""Recovery R3.2-I — canonical Commercial Home integration static checks."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "web" / "src"


def _read(relative: str) -> str:
    return (WEB_ROOT / relative).read_text(encoding="utf-8")


def test_prepare_content_next_step_registered() -> None:
    flow = _read("lib/home/agency-analysis-flow.ts")
    assert 'id: "prepare_content"' in flow
    assert "agency.next.prepareContent" in flow


def test_workspace_home_embeds_content_factory_commercially() -> None:
    home = _read("components/workspace/home/workspace-home-view.tsx")
    assert 'phase === "content_factory"' in home
    assert "ContentFactoryPanel" in home
    assert "data-testid=\"content-factory-commercial\"" in home
    assert "hideProjectSelect" in home
    assert "commercialMode" in home
    assert "recovery-preview" not in home


def test_owner_preview_opens_content_factory_on_workspace() -> None:
    preview = _read("lib/home/content-factory-owner-preview.ts")
    home = _read("components/workspace/home/workspace-home-view.tsx")
    assert "owner_preview" in preview
    assert "content_factory" in preview
    assert "parseOwnerContentFactoryPreview" in home
    assert "content-factory-owner-preview-banner" in home


def test_commercial_route_stays_on_workspace() -> None:
    home = _read("components/workspace/home/workspace-home-view.tsx")
    assert "RECOVERY_PREVIEW_R3_PATH" not in home
    assert 'setPhase("content_factory")' in home


def test_next_step_routes_prepare_content_to_factory() -> None:
    home = _read("components/workspace/home/workspace-home-view.tsx")
    assert 'selectedNext.includes("prepare_content")' in home


def test_agency_next_steps_prepare_content_label() -> None:
    ru = (REPO_ROOT / "web" / "src" / "lib" / "i18n" / "translations" / "ru.ts").read_text(
        encoding="utf-8",
    )
    assert 'prepareContent: "Подготовить контент"' in ru
    assert 'continuePrepareContent: "Подготовить контент"' in ru


def test_content_factory_commercial_copy_has_no_recovery_terms() -> None:
    ru = (REPO_ROOT / "web" / "src" / "lib" / "i18n" / "translations" / "ru.ts").read_text(
        encoding="utf-8",
    )
    assert 'commercialTitle: "Подготовить контент"' in ru
    assert "Составим контент-план, подготовим материалы" in ru
    assert "dry-run" not in ru.split("commercialSubtitle")[1].split("demoMaterialsHint")[0]


def test_commercial_panel_has_create_materials_button() -> None:
    panel = _read("components/content-factory/content-factory-panel.tsx")
    assert "content-factory-create-materials" in panel
    assert "generateContentFactoryMaterials" in panel
    assert "fetchContentFactoryProviderReadiness" in panel


def test_commercial_panel_has_no_r33a_imports() -> None:
    panel = _read("components/content-factory/content-factory-panel.tsx")
    assert "generate-materials-from-brief" not in panel
    assert "brief-to-plan-items" not in panel
    assert "generateMaterialsFromBrief" not in panel
    assert "content-factory-create-drafts" not in panel


def test_commercial_panel_hides_project_dropdown() -> None:
    panel = _read("components/content-factory/content-factory-panel.tsx")
    assert "hideProjectSelect" in panel


def test_developer_panel_links_owner_workspace_preview() -> None:
    dev = _read("components/workspace/home/home-developer-panel.tsx")
    assert "workspace-owner-content-factory-open" in dev
    assert "workspaceOwnerContentFactoryPreviewUrl" in dev


def test_recovery_preview_still_uses_same_panel_with_demo() -> None:
    preview = _read("components/workspace/home/recovery-preview-r3-view.tsx")
    panel = _read("components/content-factory/content-factory-panel.tsx")
    assert "ContentFactoryPanel" in preview
    assert "allowDemoMaterials" in preview
    assert "ContentFactoryPanel" in panel
    assert "content-factory-commercial-panel" not in panel
    assert "content-factory-home-v2" not in panel


def test_no_duplicate_content_factory_components() -> None:
    root = WEB_ROOT / "components" / "content-factory"
    names = sorted(p.name for p in root.glob("*.tsx"))
    assert "content-factory-panel.tsx" in names
    assert "content-factory-commercial-panel" not in names
    assert "content-factory-home-v2.tsx" not in names
