"""Capability dependency graph validation."""

from __future__ import annotations

from typing import Any


def build_dependency_graph(dependencies: list[dict[str, Any]]) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {}
    for dep in dependencies:
        source = dep.get("source_capability_id")
        target = dep.get("target_capability_id")
        if not source or not target:
            continue
        graph.setdefault(source, set()).add(target)
    return graph


def detect_cycle(
    graph: dict[str, set[str]],
    *,
    required_only: bool = True,
    required_edges: set[tuple[str, str]] | None = None,
) -> list[str]:
    """Return cycle nodes if a cycle exists in required dependency edges."""
    edges = required_edges or set()
    if not edges:
        for node, targets in graph.items():
            for target in targets:
                edges.add((node, target))

    visited: set[str] = set()
    stack: set[str] = set()
    cycle_nodes: list[str] = []

    def visit(node: str) -> bool:
        if node in stack:
            cycle_nodes.append(node)
            return True
        if node in visited:
            return False
        visited.add(node)
        stack.add(node)
        for target in graph.get(node, set()):
            if (node, target) not in edges and required_only and required_edges is not None:
                continue
            if visit(target):
                if node not in cycle_nodes:
                    cycle_nodes.append(node)
                return True
        stack.remove(node)
        return False

    for node in graph:
        visit(node)
    return cycle_nodes


def validate_marketing_golden_path(dependencies: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    required_pairs = {
        ("marketing.product_context", "marketing.market_research"),
        ("marketing.market_research", "marketing.competitive_intelligence"),
        ("marketing.competitive_intelligence", "marketing.customer_intelligence"),
        ("marketing.customer_intelligence", "marketing.market_validation"),
        ("marketing.market_validation", "marketing.positioning"),
        ("marketing.positioning", "marketing.claim_substantiation"),
        ("marketing.claim_substantiation", "marketing.offer_architecture"),
    }
    present = {
        (d["source_capability_id"], d["target_capability_id"])
        for d in dependencies
        if d.get("dependency_type") == "required"
    }
    for pair in required_pairs:
        if pair not in present:
            errors.append(f"missing_golden_path:{pair[0]}->{pair[1]}")
    return errors


def validate_engineering_path(dependencies: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    required = (
        ("engineering.workflow_architecture", "engineering.deployment_review"),
    )
    present = {
        (d["source_capability_id"], d["target_capability_id"])
        for d in dependencies
        if d.get("dependency_type") == "required"
    }
    for pair in required:
        if pair not in present:
            errors.append(f"missing_engineering_path:{pair[0]}->{pair[1]}")
    return errors


def validate_knowledge_path(dependencies: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    required = (
        ("knowledge.source_ingestion", "knowledge.provenance_management"),
        ("knowledge.provenance_management", "knowledge.knowledge_linking"),
        ("knowledge.knowledge_linking", "knowledge.knowledge_candidate_review"),
    )
    present = {
        (d["source_capability_id"], d["target_capability_id"])
        for d in dependencies
        if d.get("dependency_type") == "required"
    }
    for pair in required:
        if pair not in present:
            errors.append(f"missing_knowledge_path:{pair[0]}->{pair[1]}")
    return errors
