"""SKILL-01.0 freeze audit — automated checklist (see docs/rfc/SKILL-01-0-freeze-audit.md)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.schemas.contracts import SkillLifecycleStatus, SkillManifest
from app.skills.hashing import calculate_skill_package_hash
from tests.support.skill_package_validation import (
    PACKAGE_ROOT,
    package_paths_safe,
    package_structure_valid,
    parse_manifest_scalar,
    read_manifest_text,
    scripts_disabled,
)

FROZEN_PACKAGE_HASH = "6c53b5b972e5de900a135b891d8fbbd1641cdb5bf04bb171f83d5023344b8133"


def test_freeze_package_structure() -> None:
    assert package_structure_valid()


def test_freeze_manifest_status_candidate() -> None:
    manifest = read_manifest_text()
    assert parse_manifest_scalar(manifest, "status") == SkillLifecycleStatus.CANDIDATE


def test_freeze_allowed_tools_empty() -> None:
    manifest = read_manifest_text()
    assert "allowed_tools: []" in manifest


def test_freeze_network_deny_and_scripts_disabled() -> None:
    manifest = read_manifest_text()
    assert "default: deny" in manifest
    assert scripts_disabled(manifest)


def test_freeze_skill_md_has_no_permission_logic() -> None:
    skill_md = (PACKAGE_ROOT / "SKILL.md").read_text(encoding="utf-8")
    forbidden_patterns = (
        r"allowed_tools\s*:",
        r"network_policy\s*:",
        r"script_policy\s*:",
        r"api_key\s*:",
        r"credential_binding",
    )
    for pattern in forbidden_patterns:
        assert re.search(pattern, skill_md, re.IGNORECASE) is None


def test_freeze_paths_safe() -> None:
    assert package_paths_safe()


def test_freeze_deterministic_content_hash() -> None:
    assert calculate_skill_package_hash(PACKAGE_ROOT) == FROZEN_PACKAGE_HASH


def test_freeze_json_schemas_use_draft_2020_12() -> None:
    for name in ("input.schema.json", "output.schema.json"):
        schema = json.loads((PACKAGE_ROOT / "schemas" / name).read_text(encoding="utf-8"))
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_freeze_manifest_fixture_roundtrip_with_domain_contract() -> None:
    fixture_path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "skill_manifests"
        / "ms.skill.market_validation.v0.1.0.json"
    )
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    manifest = SkillManifest.model_validate(data)
    assert manifest.id == "ms.skill.market_validation"
    assert manifest.is_non_active_skeleton()
    assert manifest.permissions_deny_by_default()
