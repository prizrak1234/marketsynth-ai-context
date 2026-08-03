"""Canonical operation → verified provider tool binding (CONN-HF-01.1)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.connectors.evidence import hash_payload
from app.connectors.higgsfield.constants import MEDIA_CANONICAL_OPERATIONS
from app.connectors.higgsfield.sandbox.snapshot import SANDBOX_ROOT, sanitize_snapshot_payload


@dataclass(frozen=True)
class ProviderToolBinding:
    canonical_operation: str
    provider_tool_name: str
    tool_schema_hash: str
    verified_at: str | None
    server_version: str | None
    enabled: bool


class OperationMappingStore:
    """Loads verified canonical→provider bindings from sandbox snapshot only."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = root or SANDBOX_ROOT
        self._mapping_path = self._root / "operation_mapping.json"
        self._schema_hashes_path = self._root / "tool_schema_hashes.json"
        self._manifest_path = self._root / "freeze_manifest.json"

    def load_manifest(self) -> dict[str, Any]:
        if not self._manifest_path.is_file():
            return {"status": "sandbox_verification_required", "phase": "CONN-HF-01.1"}
        return json.loads(self._manifest_path.read_text(encoding="utf-8"))

    def sandbox_verified(self) -> bool:
        manifest = self.load_manifest()
        return str(manifest.get("status")) == "sandbox_verified"

    def verification_status(self) -> str:
        manifest = self.load_manifest()
        return str(manifest.get("status") or "sandbox_verification_required")

    def load_mapping_document(self) -> dict[str, Any]:
        if not self._mapping_path.is_file():
            return {
                "status": "sandbox_verification_required",
                "verified_at": None,
                "mappings": {},
            }
        return json.loads(self._mapping_path.read_text(encoding="utf-8"))

    def get_binding(self, canonical_operation: str) -> ProviderToolBinding | None:
        if canonical_operation not in MEDIA_CANONICAL_OPERATIONS:
            return None
        doc = self.load_mapping_document()
        entry = (doc.get("mappings") or {}).get(canonical_operation)
        if not isinstance(entry, dict):
            return None
        provider_tool = str(entry.get("provider_tool_name") or "").strip()
        schema_hash = str(entry.get("tool_schema_hash") or "").strip()
        if not provider_tool or not schema_hash:
            return None
        if entry.get("enabled") is False:
            return None
        return ProviderToolBinding(
            canonical_operation=canonical_operation,
            provider_tool_name=provider_tool,
            tool_schema_hash=schema_hash,
            verified_at=entry.get("verified_at"),
            server_version=entry.get("server_version"),
            enabled=True,
        )

    def mapping_status(self, canonical_operation: str) -> str:
        binding = self.get_binding(canonical_operation)
        if binding is not None:
            return "mapped"
        doc = self.load_mapping_document()
        entry = (doc.get("mappings") or {}).get(canonical_operation)
        if isinstance(entry, dict) and entry.get("status") == "unsupported":
            return "unsupported"
        return "unverified"

    def verify_schema_hash(self, provider_tool_name: str, schema: dict[str, Any]) -> bool:
        if not self._schema_hashes_path.is_file():
            return False
        hashes = json.loads(self._schema_hashes_path.read_text(encoding="utf-8"))
        expected = hashes.get(provider_tool_name)
        if not expected:
            return False
        return hash_payload(schema) == str(expected)

    def discovered_tool_names(self) -> list[str]:
        tools_path = self._root / "tools_snapshot.json"
        if not tools_path.is_file():
            return []
        doc = json.loads(tools_path.read_text(encoding="utf-8"))
        names: list[str] = []
        for item in doc.get("tools") or []:
            if isinstance(item, dict) and item.get("name"):
                names.append(str(item["name"]))
        return names

    def save_mapping_document(self, document: dict[str, Any]) -> None:
        self._mapping_path.parent.mkdir(parents=True, exist_ok=True)
        self._mapping_path.write_text(
            json.dumps(sanitize_snapshot_payload(document), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def load_operation_mapping() -> OperationMappingStore:
    return OperationMappingStore()


def load_sandbox_manifest() -> dict[str, Any]:
    return OperationMappingStore().load_manifest()
