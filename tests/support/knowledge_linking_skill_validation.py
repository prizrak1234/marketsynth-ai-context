"""Test helpers for KB-WPL-01.5 Knowledge Linking Skill."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urldefrag, urljoin

from app.knowledge.knowledge_linking.contracts import SKILL_ID
from app.skills.hashing import calculate_skill_package_hash
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO = Path(__file__).resolve().parents[2]
SKILLS_ROOT = REPO / "packages" / "skills"


def package_root() -> Path:
    return SKILLS_ROOT / SKILL_ID


def load_json_fixture(relative_path: str) -> dict:
    path = package_root() / relative_path
    return json.loads(path.read_text(encoding="utf-8"))


def schema_registry() -> Registry:
    schema_dir = package_root() / "schemas"
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


def schema_validator(schema_name: str) -> Draft202012Validator:
    schema_path = package_root() / "schemas" / schema_name
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=schema_registry())


def package_hash() -> str:
    return calculate_skill_package_hash(package_root())


def sample_node(
    artifact_id: str,
    *,
    tenant_scope: str = "global",
    tenant_id: str = "global",
    project_id: str | None = None,
    content_hash: str = "a" * 64,
    artifact_type: str = "skill",
    **extra: object,
) -> dict:
    node = {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "title": artifact_id,
        "version": "0.1.0",
        "content_hash": content_hash,
        "tenant_scope": tenant_scope,
        "tenant_id": tenant_id,
        "lifecycle_status": "candidate",
        "trust_status": "reviewed",
        "source_references": [],
        "provenance": {"origin": "fixture"},
    }
    if project_id:
        node["project_id"] = project_id
    node.update(extra)
    return node


def sample_link(
    source_id: str,
    target_id: str,
    *,
    confidence: str = "high",
    evidence: list[dict] | None = None,
    relation_type: str = "depends_on",
) -> dict:
    return {
        "link_id": f"link-{source_id}-{target_id}",
        "source_artifact_id": source_id,
        "target_artifact_id": target_id,
        "relation_type": relation_type,
        "direction": "forward",
        "reason": "Fixture declared dependency.",
        "supporting_evidence": (
            evidence if evidence is not None else [{"type": "declared_dependency"}]
        ),
        "confidence": confidence,
        "tenant_scope": "global",
        "human_review_required": confidence != "high",
        "conflict_status": "none",
        "provenance": {"origin": "fixture"},
    }
