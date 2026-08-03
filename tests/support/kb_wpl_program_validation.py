"""Test helpers for KB-WPL-01.9 integrated program freeze audit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
PROGRAM_BUNDLE = REPO_ROOT / "packages" / "knowledge" / "kb_wpl_program" / "0.1.0"

FROZEN_PROGRAM_BUNDLE_HASH = (
    "43e2cab328dec889ee7fe755bf208311522baec1dd761ef4bb9eac73a53aa4a4"
)
FROZEN_PROGRAM_SEMANTIC_HASH = (
    "9abd421e96a2402d86d2b44c98431a132b60ef68f3c93448db895228acdaa462"
)

EXPECTED_COMPONENT_IDS = (
    "kb-wpl-01.0",
    "kb-wpl-01.1",
    "kb-wpl-01.2",
    "kb-wpl-01.2.1",
    "kb-wpl-01.3",
    "kb-wpl-01.4",
    "kb-wpl-01.5",
    "kb-wpl-01.6",
    "kb-wpl-01.7",
    "kb-wpl-01.8",
)

WPL_KNOWLEDGE_MODULES = (
    "workflow_catalog",
    "workflow_patterns",
    "n8n_engineering",
    "knowledge_linking",
    "presentation_architecture",
    "capability_model",
    "discovery",
)

FORBIDDEN_IMPORTS = frozenset(
    {
        "requests",
        "httpx",
        "aiohttp",
        "socket",
        "mcp",
        "subprocess",
        "n8n",
    }
)

FORBIDDEN_EXEC_METHODS = frozenset(
    {
        "install",
        "activate",
        "execute",
        "deploy",
        "publish",
        "run_workflow",
        "activate_connector",
    }
)


def load_integrated_manifest() -> dict[str, Any]:
    return json.loads((PROGRAM_BUNDLE / "integrated_manifest.json").read_text(encoding="utf-8"))


def load_component_index() -> dict[str, Any]:
    return json.loads((PROGRAM_BUNDLE / "component_index.json").read_text(encoding="utf-8"))


def load_invariant_map() -> dict[str, Any]:
    return json.loads((PROGRAM_BUNDLE / "invariant_map.json").read_text(encoding="utf-8"))


def load_hash_registry() -> dict[str, Any]:
    return json.loads((PROGRAM_BUNDLE / "hash_registry.json").read_text(encoding="utf-8"))


def load_accepted_limitations() -> dict[str, Any]:
    return json.loads((PROGRAM_BUNDLE / "accepted_limitations.json").read_text(encoding="utf-8"))


def load_deferred_work() -> dict[str, Any]:
    return json.loads((PROGRAM_BUNDLE / "deferred_work.json").read_text(encoding="utf-8"))


def load_freeze_findings() -> dict[str, Any]:
    return json.loads((PROGRAM_BUNDLE / "freeze_findings.json").read_text(encoding="utf-8"))


def recompute_program_semantic_hash(manifest: dict[str, Any]) -> str:
    exclude = {"generated_at", "semantic_hash", "bundle_hash"}
    subset = {k: v for k, v in manifest.items() if k not in exclude}
    payload = json.dumps(subset, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def scan_py_forbidden_imports(path: Path) -> list[str]:
    import ast

    offenders: list[str] = []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in FORBIDDEN_IMPORTS:
                    offenders.append(f"{path.name}:import {alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".")[0]
            if root in FORBIDDEN_IMPORTS:
                offenders.append(f"{path.name}:from {node.module}")
    return offenders
