"""Deterministic lineage graph serialization and hashing (SKILL-01.7)."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.lineage.contracts import LineageEdge, LineageGraph, LineageNodeReference

_ABSOLUTE_PATH = re.compile(r"(?:[A-Za-z]:\\|/)[^\s\"']+")
_SECRET_FRAGMENTS = ("token", "secret", "password", "api_key", "credential", "authorization")


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=_json_default)


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Unsupported type for canonical JSON: {type(value)!r}")


def sanitize_for_serialization(text: str) -> str:
    redacted = _ABSOLUTE_PATH.sub("[PATH]", text)
    lowered = redacted.lower()
    if any(fragment in lowered for fragment in _SECRET_FRAGMENTS):
        return "[REDACTED]"
    return redacted


def node_sort_key(node: LineageNodeReference) -> tuple[str, str]:
    return (node.node_type.value, node.node_id)


def edge_sort_key(edge: LineageEdge) -> tuple[str, str, str]:
    return (edge.from_node_id, edge.to_node_id, edge.edge_type.value)


def sorted_nodes(nodes: tuple[LineageNodeReference, ...]) -> tuple[LineageNodeReference, ...]:
    return tuple(sorted(nodes, key=node_sort_key))


def sorted_edges(edges: tuple[LineageEdge, ...]) -> tuple[LineageEdge, ...]:
    return tuple(sorted(edges, key=edge_sort_key))


def canonical_model_dict(model: BaseModel) -> dict[str, Any]:
    return json.loads(canonical_json(model.model_dump(mode="json")))


def compute_graph_hash(graph: LineageGraph, *, exclude_volatile: bool = True) -> str:
    payload = canonical_model_dict(graph)
    payload.pop("graph_hash", None)
    if exclude_volatile:
        for node in payload.get("nodes", []):
            node.pop("created_at", None)
        for source in payload.get("source_references", []):
            source.pop("created_at", None)
            source.pop("generated_at", None)
    payload["nodes"] = sorted(
        payload.get("nodes", []),
        key=lambda item: (item["node_type"], item["node_id"]),
    )
    payload["edges"] = sorted(
        payload.get("edges", []),
        key=lambda item: (item["from_node_id"], item["to_node_id"], item["edge_type"]),
    )
    encoded = canonical_json(payload).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def serialize_graph(graph: LineageGraph) -> str:
    return canonical_json(canonical_model_dict(graph))
