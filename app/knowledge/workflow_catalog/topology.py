"""Workflow topology hashing — provider-aware and provider-neutral."""

from __future__ import annotations

import hashlib
import json
from typing import Any

FUNCTIONAL_CLASS: dict[str, str] = {
    "executecommand": "shell_execution",
    "code": "code_execution",
    "httprequest": "http_request",
    "webhook": "webhook_trigger",
    "telegram": "publication_messaging",
    "gmail": "email_publication",
    "instagram": "social_publication",
    "facebook": "social_publication",
    "linkedin": "social_publication",
    "wordpress": "cms_publication",
    "postgres": "database",
    "mysql": "database",
    "mongodb": "database",
    "googlesheets": "spreadsheet",
    "agent": "ai_agent",
    "lmchat": "llm_model",
    "openai": "llm_model",
    "stickynote": "documentation",
    "manualtrigger": "manual_trigger",
    "scheduletrigger": "schedule_trigger",
}


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _functional_class(node_type: str) -> str:
    lower = node_type.lower()
    for fragment, cls in FUNCTIONAL_CLASS.items():
        if fragment in lower:
            return cls
    if "trigger" in lower:
        return "trigger"
    if "langchain" in lower:
        return "ai_component"
    if lower.startswith("n8n-nodes-"):
        return "community_or_custom_node"
    return "unknown_function"


def _node_index(nodes: list[dict[str, Any]]) -> dict[str, str]:
    index: dict[str, str] = {}
    for node in nodes:
        name = str(node.get("name") or node.get("id") or "")
        nid = str(node.get("id") or name)
        cls = _functional_class(str(node.get("type", "")))
        index[name] = cls
        index[nid] = cls
    return index


def _connection_edges(
    data: dict[str, Any],
    index: dict[str, str],
    *,
    use_class: bool,
) -> list[tuple[str, str]]:
    edges: list[tuple[str, str]] = []
    connections = data.get("connections") or {}
    if not isinstance(connections, dict):
        return edges

    def _val(key: str) -> str:
        if use_class:
            return index.get(key, "unknown_function")
        return key

    for source, outputs in connections.items():
        if not isinstance(outputs, dict):
            continue
        src = _val(str(source))
        for output_list in outputs.values():
            if not isinstance(output_list, list):
                continue
            for branch in output_list:
                if not isinstance(branch, list):
                    continue
                for conn in branch:
                    if isinstance(conn, dict):
                        tgt = _val(str(conn.get("node", "")))
                        edges.append((src, tgt))
    return sorted(set(edges))


def topology_hashes(data: dict[str, Any]) -> tuple[str, str]:
    nodes = [n for n in (data.get("nodes") or []) if isinstance(n, dict)]
    index = _node_index(nodes)
    aware_nodes = sorted(
        (
            str(n.get("type", "")),
            str(n.get("typeVersion", "")),
            _functional_class(str(n.get("type", ""))),
        )
        for n in nodes
    )
    neutral_nodes = sorted(_functional_class(str(n.get("type", ""))) for n in nodes)
    aware_payload = {"nodes": aware_nodes, "edges": _connection_edges(data, index, use_class=False)}
    neutral_payload = {
        "classes": neutral_nodes,
        "edges": _connection_edges(data, index, use_class=True),
    }
    return _sha256_text(json.dumps(aware_payload, sort_keys=True)), _sha256_text(
        json.dumps(neutral_payload, sort_keys=True)
    )
