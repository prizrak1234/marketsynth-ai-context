"""Catalog serialization and schema validation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.knowledge.workflow_catalog.contracts import (
    DuplicateFamily,
    WorkflowCatalogBundle,
    WorkflowTemplateRecord,
)
from app.knowledge.workflow_catalog.errors import WorkflowValidationError

REPO_ROOT = Path(__file__).resolve().parents[3]
WPL_SCHEMA = REPO_ROOT / "packages" / "knowledge" / "workflow_patterns" / "0.1.0"
CATALOG_ROOT = REPO_ROOT / "packages" / "knowledge" / "workflow_catalog" / "0.1.0"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def record_to_dict(record: WorkflowTemplateRecord) -> dict[str, Any]:
    return json.loads(record.model_dump_json())


def validate_record_against_schema(record: WorkflowTemplateRecord) -> None:
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource

    root = WPL_SCHEMA
    resources: list[tuple[str, Resource]] = []
    for path in sorted(root.glob("*.schema.json")):
        contents = json.loads(path.read_text(encoding="utf-8"))
        resource = Resource.from_contents(contents)
        resources.append((path.name, resource))
        sid = contents.get("$id")
        if isinstance(sid, str):
            resources.append((sid, resource))
    registry = Registry().with_resources(resources)
    schema = json.loads((root / "workflow-template.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema, registry=registry).validate(record_to_dict(record))


def assert_no_executable_body(record_dict: dict[str, Any]) -> None:
    forbidden = {"nodes", "connections", "pinData", "workflow_body", "raw_json", "settings"}
    found = forbidden.intersection(record_dict.keys())
    if found:
        msg = f"executable body keys in catalog record: {found}"
        raise WorkflowValidationError(msg)


def bundle_catalog_hash(bundle: dict[str, Any]) -> str:
    semantic = {
        "schema_version": bundle["schema_version"],
        "templates": bundle["templates"],
        "invalid_files": bundle.get("invalid_files", []),
    }
    return sha256_bytes(json.dumps(semantic, sort_keys=True, separators=(",", ":")).encode())


def duplicate_families_hash(families: list[DuplicateFamily]) -> str:
    payload = [json.loads(f.model_dump_json()) for f in families]
    return sha256_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())


def security_summary_hash(summary: dict[str, Any]) -> str:
    semantic = {k: v for k, v in summary.items() if k != "generated_at"}
    return sha256_bytes(json.dumps(semantic, sort_keys=True, separators=(",", ":")).encode())


def write_catalog_outputs(
    bundle: WorkflowCatalogBundle,
    families: list[DuplicateFamily],
    statistics: dict[str, Any],
    security_summary: dict[str, Any],
) -> dict[str, str]:
    CATALOG_ROOT.mkdir(parents=True, exist_ok=True)
    bundle_dict = json.loads(bundle.model_dump_json())
    for template in bundle_dict["templates"]:
        assert_no_executable_body(template)

    catalog_path = CATALOG_ROOT / "catalog.json"
    catalog_text = json.dumps(bundle_dict, indent=2, ensure_ascii=False) + "\n"
    catalog_path.write_text(catalog_text, encoding="utf-8")

    families_dict = {"families": [json.loads(item.model_dump_json()) for item in families]}
    fam_path = CATALOG_ROOT / "duplicate_families.json"
    fam_text = json.dumps(families_dict, indent=2, ensure_ascii=False) + "\n"
    fam_path.write_text(fam_text, encoding="utf-8")

    sec_path = CATALOG_ROOT / "security_summary.json"
    sec_text = json.dumps(security_summary, indent=2, ensure_ascii=False) + "\n"
    sec_path.write_text(sec_text, encoding="utf-8")

    stats_path = CATALOG_ROOT / "statistics.json"
    stats_text = json.dumps(statistics, indent=2, ensure_ascii=False) + "\n"
    stats_path.write_text(stats_text, encoding="utf-8")

    file_hashes = {
        "catalog.json": sha256_bytes(catalog_path.read_bytes()),
        "duplicate_families.json": sha256_bytes(fam_path.read_bytes()),
        "security_summary.json": sha256_bytes(sec_path.read_bytes()),
        "statistics.json": sha256_bytes(stats_path.read_bytes()),
    }
    bundle_hash = sha256_bytes(
        json.dumps(file_hashes, sort_keys=True, separators=(",", ":")).encode()
    )
    manifest = {
        "schema_version": "0.1.0",
        "schema_bundle_ref": "packages/knowledge/workflow_patterns/0.1.0/",
        "catalog_status": "quarantined_metadata_only",
        "file_hashes": file_hashes,
        "bundle_hash": bundle_hash,
        "catalog_semantic_hash": bundle_catalog_hash(bundle_dict),
        "generated_at": bundle.generated_at,
    }
    manifest_path = CATALOG_ROOT / "freeze_manifest.json"
    manifest_text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    manifest_path.write_text(manifest_text, encoding="utf-8")
    file_hashes["freeze_manifest.json"] = sha256_bytes(manifest_path.read_bytes())

    readme = (
        "# Workflow Catalog — Quarantine Metadata (KB-WPL-01.2.1)\n\n"
        "Metadata-only catalog from n8n workflow exports. **No executable bodies.**\n\n"
        f"- Valid exports: **{bundle.valid_exports}**\n"
        f"- Catalog records: **{len(bundle.templates)}**\n"
        "- Schema SoT: `workflow_patterns/0.1.0/workflow-template.schema.json`\n"
        f"- Bundle hash: `{bundle_hash}`\n"
    )
    readme_path = CATALOG_ROOT / "README.md"
    readme_path.write_text(readme, encoding="utf-8")

    return file_hashes
