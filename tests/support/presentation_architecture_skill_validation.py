"""Test helpers for KB-WPL-01.6 Presentation Architecture Skill."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urldefrag, urljoin

from app.knowledge.presentation_architecture.contracts import SKILL_ID
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


def sample_slide(
    slide_id: str,
    sequence: int,
    *,
    key_message: str = "Primary message",
    unsupported: list[str] | None = None,
    extra_points: int = 0,
) -> dict:
    return {
        "slide_id": slide_id,
        "sequence_number": sequence,
        "slide_type": "evidence",
        "title": f"Slide {sequence}",
        "purpose": "Test slide",
        "key_message": key_message,
        "supporting_points": [f"point-{i}" for i in range(extra_points)],
        "evidence_references": [{"source_id": "src-1", "claim": "c1"}],
        "claim_references": [],
        "content_blocks": [],
        "visual_requirements": [],
        "chart_requirements": [],
        "image_requirements": [],
        "layout_recommendation": "default",
        "speaker_note_requirements": {},
        "transition_from_previous": "",
        "transition_to_next": "",
        "accessibility_notes": [],
        "unsupported_or_missing_evidence": unsupported or [],
        "human_review_required": False,
        "provenance": {},
    }
