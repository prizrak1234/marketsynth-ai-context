"""Test helpers for KB-WPL-01.4 n8n Engineering Skills."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urldefrag, urljoin

from app.knowledge.n8n_engineering.constants import N8N_ENGINEERING_SKILL_IDS
from app.skills.hashing import calculate_skill_package_hash
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO = Path(__file__).resolve().parents[2]
SKILLS_ROOT = REPO / "packages" / "skills"


def package_root(skill_id: str) -> Path:
    return SKILLS_ROOT / skill_id


def load_json_fixture(skill_id: str, relative_path: str) -> dict:
    path = package_root(skill_id) / relative_path
    return json.loads(path.read_text(encoding="utf-8"))


def schema_registry(skill_id: str) -> Registry:
    schema_dir = package_root(skill_id) / "schemas"
    resources: list[tuple[str, Resource]] = []
    schemas_by_name: dict[str, tuple[dict, Resource]] = {}
    for path in sorted(schema_dir.glob("*.schema.json")):
        contents = json.loads(path.read_text(encoding="utf-8"))
        resource = Resource.from_contents(contents)
        schemas_by_name[path.name] = (contents, resource)
        resources.append((path.name, resource))
        resources.append((f"schemas/{path.name}", resource))
        schema_id = contents.get("$id")
        if isinstance(schema_id, str):
            resources.append((schema_id, resource))
    for contents, _resource in schemas_by_name.values():
        base_id = contents.get("$id")
        if not isinstance(base_id, str):
            continue
        for other_name, (_, other_resource) in schemas_by_name.items():
            for ref_path in (f"schemas/{other_name}", other_name):
                resolved = urldefrag(urljoin(base_id, ref_path))[0]
                resources.append((resolved, other_resource))
    return Registry().with_resources(resources)


def schema_validator(skill_id: str, schema_name: str) -> Draft202012Validator:
    schema_path = package_root(skill_id) / "schemas" / schema_name
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=schema_registry(skill_id))


def package_hash(skill_id: str) -> str:
    return calculate_skill_package_hash(package_root(skill_id))


__all__ = [
    "N8N_ENGINEERING_SKILL_IDS",
    "load_json_fixture",
    "package_hash",
    "package_root",
    "schema_validator",
]
