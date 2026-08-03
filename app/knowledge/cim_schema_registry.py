"""Local read-only registry for canonical Customer Intelligence Model schemas."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

CANONICAL_URI_BASE = "https://schemas.marketsynth.ai/customer-intelligence/"
SUPPORTED_VERSIONS: frozenset[str] = frozenset({"0.1.0"})

SCHEMA_FILES: tuple[str, ...] = (
    "customer-intelligence.schema.json",
    "customer-segment.schema.json",
    "customer-claim.schema.json",
    "job-to-be-done.schema.json",
    "decision-role.schema.json",
    "priority-assessment.schema.json",
    "segment-conflict.schema.json",
    "provenance.schema.json",
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_KNOWLEDGE_ROOT = _REPO_ROOT / "packages" / "knowledge" / "customer_intelligence"


class UnknownCimSchemaVersionError(ValueError):
    """Raised when a CIM schema version is not registered locally."""


class UnknownCanonicalUriError(ValueError):
    """Raised when a canonical schema URI cannot be resolved locally."""


class DuplicateSchemaIdError(ValueError):
    """Raised when duplicate canonical schema IDs are detected."""


def bundle_root(version: str) -> Path:
    if version not in SUPPORTED_VERSIONS:
        raise UnknownCimSchemaVersionError(f"Unsupported CIM schema version: {version}")
    root = (_KNOWLEDGE_ROOT / version).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"CIM schema bundle not found: {root}")
    return root


def canonical_uri(version: str, filename: str) -> str:
    return urljoin(f"{CANONICAL_URI_BASE}{version}/", filename)


def resolve_canonical_uri(uri: str) -> Path:
    parsed = urlparse(uri)
    if parsed.scheme in ("http", "https"):
        if parsed.netloc != "schemas.marketsynth.ai":
            raise UnknownCanonicalUriError(f"Remote schema resolution forbidden: {uri}")
        parts = parsed.path.strip("/").split("/")
        if len(parts) < 3 or parts[0] != "customer-intelligence":
            raise UnknownCanonicalUriError(f"Unknown canonical namespace: {uri}")
        version, filename = parts[1], parts[2]
        if version not in SUPPORTED_VERSIONS:
            raise UnknownCanonicalUriError(f"Unsupported CIM schema version in URI: {uri}")
        if ".." in parts or filename != Path(filename).name:
            raise UnknownCanonicalUriError(f"Unsafe canonical URI: {uri}")
        target = bundle_root(version) / filename
        if not target.is_file():
            raise UnknownCanonicalUriError(f"Canonical schema file missing: {uri}")
        return target
    raise UnknownCanonicalUriError(f"Non-canonical URI: {uri}")


def load_schema_file(version: str, filename: str) -> dict[str, Any]:
    if filename not in SCHEMA_FILES:
        raise UnknownCanonicalUriError(f"Unknown schema file: {filename}")
    return json.loads((bundle_root(version) / filename).read_text(encoding="utf-8"))


def build_registry(version: str = "0.1.0") -> Registry:
    root = bundle_root(version)
    parsed: dict[str, dict[str, Any]] = {}
    for name in SCHEMA_FILES:
        parsed[name] = json.loads((root / name).read_text(encoding="utf-8"))

    seen_ids: set[str] = set()
    resources: list[tuple[str, Resource[Any]]] = []
    for name, contents in parsed.items():
        schema_id = contents.get("$id")
        if isinstance(schema_id, str):
            if schema_id in seen_ids:
                raise DuplicateSchemaIdError(f"Duplicate schema $id: {schema_id}")
            seen_ids.add(schema_id)
        resource = Resource.from_contents(contents)
        resources.append((canonical_uri(version, name), resource))
        if isinstance(schema_id, str):
            resources.append((schema_id, resource))

    return Registry().with_resources(resources)


def schema_validator(version: str, filename: str) -> Draft202012Validator:
    schema = load_schema_file(version, filename)
    return Draft202012Validator(schema, registry=build_registry(version))


def validate_canonical_document(version: str, filename: str, data: Any) -> None:
    schema_validator(version, filename).validate(data)


__all__ = [
    "CANONICAL_URI_BASE",
    "DuplicateSchemaIdError",
    "SCHEMA_FILES",
    "SUPPORTED_VERSIONS",
    "UnknownCanonicalUriError",
    "UnknownCimSchemaVersionError",
    "build_registry",
    "bundle_root",
    "canonical_uri",
    "load_schema_file",
    "resolve_canonical_uri",
    "schema_validator",
    "validate_canonical_document",
]
