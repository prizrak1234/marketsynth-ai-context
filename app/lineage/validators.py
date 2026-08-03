"""Lineage continuity validation (SKILL-01.7)."""

from __future__ import annotations

from collections import defaultdict

from app.lineage.contracts import (
    LineageEdgeType,
    LineageFinding,
    LineageFindingCode,
    LineageFindingSeverity,
    LineageGraph,
    LineageNodeType,
    LineageValidationResult,
)

ACYCLIC_EDGE_TYPES = frozenset(
    {
        LineageEdgeType.VALIDATED_BY,
        LineageEdgeType.PROJECTED_TO,
        LineageEdgeType.EXECUTED_AS,
        LineageEdgeType.PRODUCED,
        LineageEdgeType.AUDITED_BY,
        LineageEdgeType.IMPORTED_AS,
    }
)


def _finding(
    code: LineageFindingCode,
    severity: LineageFindingSeverity,
    message: str,
    *,
    node_id: str | None = None,
    edge_id: str | None = None,
    blocking: bool = False,
) -> LineageFinding:
    return LineageFinding(
        code=code,
        severity=severity,
        message=message,
        node_id=node_id,
        edge_id=edge_id,
        blocking=blocking,
    )


def validate_lineage_continuity(graph: LineageGraph) -> LineageValidationResult:
    findings: list[LineageFinding] = []
    node_by_id = {node.node_id: node for node in graph.nodes}
    node_ids = set(node_by_id)

    for edge in graph.edges:
        if edge.from_node_id not in node_ids:
            findings.append(
                _finding(
                    LineageFindingCode.MISSING_PARENT,
                    LineageFindingSeverity.ERROR,
                    f"Edge references missing from-node: {edge.from_node_id}",
                    edge_id=edge.edge_id,
                    blocking=True,
                )
            )
        if edge.to_node_id not in node_ids:
            findings.append(
                _finding(
                    LineageFindingCode.MISSING_PARENT,
                    LineageFindingSeverity.ERROR,
                    f"Edge references missing to-node: {edge.to_node_id}",
                    edge_id=edge.edge_id,
                    blocking=True,
                )
            )

    metadata_by_id: dict[str, str | None] = {}
    for node in graph.nodes:
        prior = metadata_by_id.get(node.node_id)
        if prior is not None and prior != node.metadata_hash:
            findings.append(
                _finding(
                    LineageFindingCode.DUPLICATE_NODE_CONFLICT,
                    LineageFindingSeverity.ERROR,
                    f"Conflicting metadata for node {node.node_id}",
                    node_id=node.node_id,
                    blocking=True,
                )
            )
        metadata_by_id[node.node_id] = node.metadata_hash

    tenant_ids = {node.tenant_id for node in graph.nodes if node.tenant_id}
    if graph.context and graph.context.tenant_id:
        tenant_ids.add(graph.context.tenant_id)
    non_global_tenants = {
        node.tenant_id
        for node in graph.nodes
        if node.tenant_id and not node.global_scope
    }
    if len(non_global_tenants) > 1:
        findings.append(
            _finding(
                LineageFindingCode.TENANT_MISMATCH,
                LineageFindingSeverity.CRITICAL,
                "Graph contains multiple tenant contexts.",
                blocking=True,
            )
        )

    for edge in graph.edges:
        from_node = node_by_id.get(edge.from_node_id)
        to_node = node_by_id.get(edge.to_node_id)
        if from_node is None or to_node is None:
            continue
        if (
            from_node.tenant_id
            and to_node.tenant_id
            and from_node.tenant_id != to_node.tenant_id
            and not (from_node.global_scope or to_node.global_scope)
        ):
            findings.append(
                _finding(
                    LineageFindingCode.TENANT_MISMATCH,
                    LineageFindingSeverity.CRITICAL,
                    "Cross-tenant edge detected.",
                    edge_id=edge.edge_id,
                    blocking=True,
                )
            )

    if graph.context and graph.context.skill_id and graph.context.skill_version:
        for node in graph.nodes:
            if node.skill_id and node.skill_id != graph.context.skill_id:
                findings.append(
                    _finding(
                        LineageFindingCode.SKILL_IDENTITY_MISMATCH,
                        LineageFindingSeverity.ERROR,
                        f"Skill id mismatch on node {node.node_id}",
                        node_id=node.node_id,
                        blocking=True,
                    )
                )

    validation_nodes = [
        node for node in graph.nodes if node.node_type == LineageNodeType.PACKAGE_VALIDATION
    ]
    package_nodes = [
        node for node in graph.nodes if node.node_type == LineageNodeType.SKILL_PACKAGE
    ]
    for validation in validation_nodes:
        if not validation.package_hash:
            findings.append(
                _finding(
                    LineageFindingCode.SOURCE_REFERENCE_MISSING,
                    LineageFindingSeverity.ERROR,
                    "Package validation missing package hash.",
                    node_id=validation.node_id,
                    blocking=True,
                )
            )
        matching = [node for node in package_nodes if node.package_hash == validation.package_hash]
        if validation.package_hash and not matching:
            findings.append(
                _finding(
                    LineageFindingCode.ORPHAN_NODE,
                    LineageFindingSeverity.WARNING,
                    "Validation node has no matching skill package node.",
                    node_id=validation.node_id,
                )
            )

    registry_nodes = [
        node for node in graph.nodes if node.node_type == LineageNodeType.REGISTRY_PROJECTION
    ]
    for registry in registry_nodes:
        validation_match = [
            node
            for node in validation_nodes
            if node.skill_id == registry.skill_id
            and node.skill_version == registry.skill_version
        ]
        if (
            registry.package_hash
            and validation_match
            and validation_match[0].package_hash != registry.package_hash
        ):
            findings.append(
                _finding(
                    LineageFindingCode.HASH_MISMATCH,
                    LineageFindingSeverity.ERROR,
                    "Registry projection package hash mismatch.",
                    node_id=registry.node_id,
                    blocking=True,
                )
            )

    quarantine_nodes = [
        node for node in graph.nodes if node.node_type == LineageNodeType.QUARANTINE_IMPORT
    ]
    for quarantine in quarantine_nodes:
        if quarantine.lifecycle_status and quarantine.lifecycle_status != "quarantined":
            findings.append(
                _finding(
                    LineageFindingCode.LIFECYCLE_SEMANTICS_CONFLICT,
                    LineageFindingSeverity.ERROR,
                    "Quarantine import must preserve quarantined effective status.",
                    node_id=quarantine.node_id,
                    blocking=True,
                )
            )

    result_ids = {
        node.node_id
        for node in graph.nodes
        if node.node_type == LineageNodeType.CONNECTOR_RESULT
    }
    for result_id in result_ids:
        connected = any(
            edge.to_node_id == result_id and edge.edge_type == LineageEdgeType.EXECUTED_AS
            for edge in graph.edges
        )
        if not connected:
            findings.append(
                _finding(
                    LineageFindingCode.CONNECTOR_REQUEST_MISSING,
                    LineageFindingSeverity.ERROR,
                    "Connector result lacks request edge.",
                    node_id=result_id,
                    blocking=True,
                )
            )

    evidence_nodes = [
        node for node in graph.nodes if node.node_type == LineageNodeType.CONNECTOR_EVIDENCE
    ]
    for evidence in evidence_nodes:
        linked = any(
            edge.from_node_id == evidence.node_id or edge.to_node_id == evidence.node_id
            for edge in graph.edges
        )
        if not linked:
            findings.append(
                _finding(
                    LineageFindingCode.EVIDENCE_MISSING,
                    LineageFindingSeverity.ERROR,
                    "Connector evidence is orphaned.",
                    node_id=evidence.node_id,
                    blocking=True,
                )
            )

    audit_nodes = [
        node for node in graph.nodes if node.node_type == LineageNodeType.UNIFIED_AUDIT_REPORT
    ]
    for audit in audit_nodes:
        linked = any(
            edge.to_node_id == audit.node_id or edge.from_node_id == audit.node_id
            for edge in graph.edges
        )
        if not linked:
            findings.append(
                _finding(
                    LineageFindingCode.AUDIT_SOURCE_MISSING,
                    LineageFindingSeverity.WARNING,
                    "Audit report has no linked sources.",
                    node_id=audit.node_id,
                )
            )

    approval_nodes = {
        node.node_id
        for node in graph.nodes
        if node.node_type == LineageNodeType.APPROVAL_REFERENCE
    }
    allowed_approval_edges = {LineageEdgeType.AUTHORIZED_BY, LineageEdgeType.EXECUTED_AS}
    for result_id in result_ids:
        for edge in graph.edges:
            if (
                edge.to_node_id == result_id
                and edge.from_node_id in approval_nodes
                and edge.edge_type not in allowed_approval_edges
            ):
                findings.append(
                    _finding(
                        LineageFindingCode.INVALID_EDGE,
                        LineageFindingSeverity.ERROR,
                        "Approval reference edge continuity invalid.",
                        edge_id=edge.edge_id,
                        blocking=True,
                    )
                )

    for edge_type in ACYCLIC_EDGE_TYPES:
        if _has_cycle(graph, edge_type):
            findings.append(
                _finding(
                    LineageFindingCode.CYCLE_DETECTED,
                    LineageFindingSeverity.ERROR,
                    f"Cycle detected for edge type {edge_type.value}.",
                    blocking=True,
                )
            )

    archived_nodes = [
        node
        for node in graph.nodes
        if node.lifecycle_status in {"archived", "deprecated"}
    ]
    for node in archived_nodes:
        if not node.skill_id or not node.skill_version or not node.package_hash:
            findings.append(
                _finding(
                    LineageFindingCode.ARCHIVED_VERSION_UNRESOLVABLE,
                    LineageFindingSeverity.WARNING,
                    "Archived version missing resolvable identity.",
                    node_id=node.node_id,
                )
            )

    blocking = any(finding.blocking for finding in findings)
    valid = not blocking and not any(
        finding.severity in {LineageFindingSeverity.ERROR, LineageFindingSeverity.CRITICAL}
        for finding in findings
    )
    return LineageValidationResult(
        valid=valid,
        findings=tuple(findings),
        node_count=len(graph.nodes),
        edge_count=len(graph.edges),
    )


def filter_graph_for_tenant(graph: LineageGraph, tenant_id: str) -> LineageGraph:
    visible_nodes = tuple(
        node
        for node in graph.nodes
        if node.global_scope or node.tenant_id is None or node.tenant_id == tenant_id
    )
    visible_ids = {node.node_id for node in visible_nodes}
    visible_edges = tuple(
        edge
        for edge in graph.edges
        if edge.from_node_id in visible_ids and edge.to_node_id in visible_ids
    )
    filtered = graph.model_copy(update={"nodes": visible_nodes, "edges": visible_edges})
    return filtered.model_copy(update={"graph_hash": graph.graph_hash})


def _has_cycle(graph: LineageGraph, edge_type: LineageEdgeType) -> bool:
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in graph.edges:
        if edge.edge_type == edge_type:
            adjacency[edge.from_node_id].append(edge.to_node_id)

    visited: set[str] = set()
    stack: set[str] = set()

    def dfs(node_id: str) -> bool:
        if node_id in stack:
            return True
        if node_id in visited:
            return False
        visited.add(node_id)
        stack.add(node_id)
        for neighbor in adjacency.get(node_id, []):
            if dfs(neighbor):
                return True
        stack.remove(node_id)
        return False

    return any(dfs(node_id) for node_id in adjacency)
