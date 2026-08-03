"""Load canonical capability model catalog."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.knowledge.capability_model.serialization import BUNDLE_ROOT, load_json

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = REPO_ROOT / "packages" / "skills"


def discover_skill_packages() -> dict[str, Path]:
    packages: dict[str, Path] = {}
    if not SKILLS_ROOT.is_dir():
        return packages
    for path in sorted(SKILLS_ROOT.iterdir()):
        if not path.is_dir() or not path.name.startswith("ms.skill."):
            continue
        manifest = path / "manifest.yaml"
        version_manifest = None
        for sub in path.iterdir():
            if sub.is_dir() and (sub / "manifest.yaml").is_file():
                version_manifest = sub / "manifest.yaml"
        if manifest.is_file() or version_manifest:
            packages[path.name] = path
    return packages


def resolve_skill_exists(skill_id: str) -> bool:
    if skill_id in discover_skill_packages():
        return True
    skill_dir = SKILLS_ROOT / skill_id
    return skill_dir.is_dir()


def load_catalog() -> dict[str, Any]:
    professions = load_json(BUNDLE_ROOT / "professions.json")
    capabilities = load_json(BUNDLE_ROOT / "capabilities.json")
    return {
        "professions": professions,
        "capabilities": capabilities,
        "known_skill_ids": sorted(discover_skill_packages()),
    }


def capability_index(capabilities: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["capability_id"]: item for item in capabilities}


def profession_index(professions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["profession_id"]: item for item in professions}
