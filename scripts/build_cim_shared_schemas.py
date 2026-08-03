"""One-shot builder for SKILL-02.5 shared CIM schema bundle (dev tooling only)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ICP_SCHEMAS = REPO / "packages/skills/ms.skill.icp_segmentation/schemas"
OUT = REPO / "packages/knowledge/customer_intelligence/0.1.0"

CANONICAL_BASE = "https://schemas.marketsynth.ai/customer-intelligence/0.1.0/"

FILE_MAP = {
    "customer_intelligence.schema.json": "customer-intelligence.schema.json",
    "customer_segment.schema.json": "customer-segment.schema.json",
    "customer_claim.schema.json": "customer-claim.schema.json",
    "job_to_be_done.schema.json": "job-to-be-done.schema.json",
    "decision_role.schema.json": "decision-role.schema.json",
    "priority_assessment.schema.json": "priority-assessment.schema.json",
    "segment_conflict.schema.json": "segment-conflict.schema.json",
    "provenance_stub.schema.json": "provenance.schema.json",
}

TITLE_MAP = {
    "customer-intelligence.schema.json": "CustomerIntelligenceDocument",
    "customer-segment.schema.json": "CustomerSegmentRecord",
    "customer-claim.schema.json": "CustomerClaimRecord",
    "job-to-be-done.schema.json": "JobToBeDone",
    "decision-role.schema.json": "DecisionRole",
    "priority-assessment.schema.json": "SegmentPriorityAssessment",
    "segment-conflict.schema.json": "SegmentConflict",
    "provenance.schema.json": "CimProvenance",
}


def canonical_uri(filename: str) -> str:
    return f"{CANONICAL_BASE}{filename}"


def ref_uri(local_ref: str) -> str:
    name = local_ref.removeprefix("schemas/")
    shared = FILE_MAP.get(name, name.replace("_", "-"))
    return canonical_uri(shared)


def transform_schema(local_name: str, schema: dict) -> dict:
    shared_name = FILE_MAP[local_name]
    out = json.loads(json.dumps(schema))
    out["$id"] = canonical_uri(shared_name)
    out["title"] = TITLE_MAP[shared_name]

    if shared_name == "customer-intelligence.schema.json":
        out["properties"]["cim_version"] = {"type": "string", "const": "0.1.0"}
        out["properties"]["skill_id"] = {
            "type": "string",
            "minLength": 1,
            "maxLength": 128,
        }

    def walk(obj: object) -> None:
        if isinstance(obj, dict):
            if "$ref" in obj and isinstance(obj["$ref"], str) and obj["$ref"].startswith("schemas/"):
                obj["$ref"] = ref_uri(obj["$ref"])
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(out)
    return out


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bundle_hash(file_hashes: dict[str, str]) -> str:
    lines = [f"{name}:{file_hashes[name]}" for name in sorted(file_hashes)]
    payload = "\n".join(lines).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    file_hashes: dict[str, str] = {}

    for local_name, shared_name in FILE_MAP.items():
        schema = transform_schema(local_name, json.loads((ICP_SCHEMAS / local_name).read_text(encoding="utf-8")))
        target = OUT / shared_name
        target.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        file_hashes[shared_name] = file_hash(target)

    bundle = bundle_hash(file_hashes)
    manifest = {
        "schema_version": "0.1.0",
        "canonical_uri_base": CANONICAL_BASE,
        "schema_status": "frozen",
        "file_hashes": file_hashes,
        "bundle_hash": bundle,
        "source_package_reference": {
            "skill_id": "ms.skill.icp_segmentation",
            "skill_version": "0.1.0",
            "local_schema_path": "schemas/customer_intelligence.schema.json",
            "local_cim_version": "0.1.0-draft",
            "package_hash": "075a4f1989a9050614babec004dda54a420d7f7bd717d9ac7e8a34b41e8ae71a",
        },
        "producer_skill": {
            "primary": "ms.skill.icp_segmentation",
            "supported_versions": ["0.1.0"],
        },
        "consumer_compatibility": {
            "supported_cim_versions": ["0.1.0"],
            "icp_local_mapping_version": "0.1.0-draft",
        },
        "generated_at": datetime.now(tz=UTC).isoformat(),
    }
    (OUT / "freeze_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote shared CIM bundle to {OUT}")
    print(f"Bundle hash: {bundle}")


if __name__ == "__main__":
    main()
