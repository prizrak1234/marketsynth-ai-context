"""Shared test helpers for KB-SKILL-01."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXTERNAL_ARTIFACTS = REPO_ROOT / "packages" / "knowledge" / "external_artifacts" / "0.1.0"
WORKFLOW_CATALOG = REPO_ROOT / "packages" / "knowledge" / "workflow_catalog" / "0.1.0"
ARCHIVE_DOCS = REPO_ROOT / "docs" / "research" / "external-archives"

KB_SKILL_PACKAGE_HASHES = {
    "ms.skill.n8n_workflow_architecture": (
        "5af85271b4f8614ae14b002c3981be54f4128f7381258b3ec1e3729d29b75666"
    ),
    "ms.skill.n8n_workflow_debugging": (
        "e200b06ea6701f0667952b05e523077280e0238a9717787c8a096dc6dcd3d70f"
    ),
    "ms.skill.n8n_deployment_review": (
        "0ec6874bf449bd3e1006d15e9b8b5c004cc64dbad5a14d614dda94f14f6a938c"
    ),
    "ms.skill.knowledge_linking": (
        "95a3ff6d7f83f2e6437b4fb724c9aec13b814be2ae8fdfbc94a5e3872d32602a"
    ),
    "ms.skill.presentation_architecture": (
        "60ce698336fa21006ba203472fc6c3cef5661171ec2e45b641dcca743a42e95c"
    ),
}

FROZEN_POSITIONING_HASH = "cbd8283f4addaa9c8496504a9c6dbccd580e8ca317b2cf86bf628be6557e8da6"
FROZEN_MV_020_HASH = "ec7c86ce0bc39b5481e336b7749de3cf087d47630be315c639897dd687568f7a"
FROZEN_CIM_BUNDLE_HASH = "b13cc76eb8f6405d114a457a8a4bf12a4a5330d9a37bd0adcfd93f48353421ea"
FROZEN_MARKETING_CLAIMS_HASH = "c29ca2c08ccbb8861206fcc855e966c93d50b68264d8d9bdd096e13cd5c32f8d"


def load_external_artifacts_manifest() -> dict:
    return json.loads((EXTERNAL_ARTIFACTS / "freeze_manifest.json").read_text(encoding="utf-8"))


def recompute_external_artifacts_bundle_hash() -> str:
    manifest = load_external_artifacts_manifest()
    payload = json.dumps(manifest["file_hashes"], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_workflow_catalog() -> dict:
    return json.loads((WORKFLOW_CATALOG / "catalog.json").read_text(encoding="utf-8"))


def load_archive_checksums() -> dict:
    return json.loads((ARCHIVE_DOCS / "archive-checksums.json").read_text(encoding="utf-8"))
