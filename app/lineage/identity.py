"""Deterministic lineage node identity rules (SKILL-01.7)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel


def _canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def metadata_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def skill_package_node_id(*, skill_id: str, skill_version: str, package_hash: str) -> str:
    return f"skill:{skill_id}:{skill_version}:{package_hash}"


def skill_version_node_id(*, skill_id: str, skill_version: str) -> str:
    return f"skill-version:{skill_id}:{skill_version}"


def package_validation_node_id(
    *, validator_version: str, package_hash: str, report_hash: str
) -> str:
    return f"validation:{validator_version}:{package_hash}:{report_hash}"


def quarantine_import_node_id(*, import_id: str, materialized_hash: str) -> str:
    return f"quarantine:{import_id}:{materialized_hash}"


def registry_projection_node_id(*, skill_id: str, skill_version: str, package_hash: str) -> str:
    return f"registry:{skill_id}:{skill_version}:{package_hash}"


def registry_snapshot_node_id(*, snapshot_id: str) -> str:
    return f"registry-snapshot:{snapshot_id}"


def connector_request_node_id(*, request_id: str) -> str:
    return f"connector-request:{request_id}"


def connector_policy_node_id(*, request_id: str, outcome: str) -> str:
    return f"connector-policy:{request_id}:{outcome}"


def connector_result_node_id(*, request_id: str, result_status: str, output_hash: str) -> str:
    return f"connector-result:{request_id}:{result_status}:{output_hash}"


def connector_evidence_node_id(*, evidence_id: str) -> str:
    return f"connector-evidence:{evidence_id}"


def audit_report_node_id(*, report_hash: str) -> str:
    return f"audit:{report_hash}"


def evidence_node_id(*, evidence_id: str) -> str:
    return f"evidence:{evidence_id}"


def approval_reference_node_id(*, approval_reference: str) -> str:
    return f"approval:{approval_reference}"


def execution_record_node_id(*, execution_id: str) -> str:
    return f"execution:{execution_id}"


def node_metadata_hash(node_payload: dict[str, Any]) -> str:
    safe = {key: value for key, value in node_payload.items() if key not in {"created_at"}}
    return metadata_hash(safe)


def model_metadata_hash(model: BaseModel | dict[str, Any]) -> str:
    if isinstance(model, BaseModel):
        data = model.model_dump(mode="json", exclude_none=True)
    else:
        data = dict(model)
    safe = {key: value for key, value in data.items() if key not in {"created_at", "generated_at"}}
    return metadata_hash(safe)
