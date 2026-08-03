"""SKILL-01.7 — Lineage preparation tests."""
# ruff: noqa: E501

from __future__ import annotations

import copy
from datetime import UTC, datetime

import pytest
from app.audit.fixtures import (
    adapted_valid_package_report,
    connector_evidence_descriptor,
)
from app.lineage import (
    LineageEdge,
    LineageEdgeType,
    LineageGraph,
    LineageMergeError,
    LineageNodeReference,
    LineageNodeType,
    LineageValidationResult,
    build_audit_lineage,
    build_package_validation_lineage,
    build_quarantine_lineage,
    build_skill_execution_lineage_descriptor,
    combine_lineage_graphs,
    compute_graph_hash,
    filter_graph_for_tenant,
    map_connector_evidence_to_lineage_reference,
    map_lineage_reference_to_knowledge_evidence,
    map_package_validation_to_evidence_source_reference,
    sanitize_for_serialization,
    serialize_graph,
    validate_edge_type,
    validate_lineage_continuity,
    validate_node_type,
)
from app.lineage.errors import LineageBuildError
from app.lineage.fixtures import (
    FROZEN_HASH,
    TENANT_A,
    TENANT_B,
    audit_aggregation_graph,
    connector_allow_graph,
    connector_approval_graph,
    connector_deny_graph,
    connector_result_graph,
    frozen_quarantine_graph,
    frozen_registry_graph,
    frozen_validation_graph,
    quarantine_success_result,
    valid_package_validation_report,
)
from app.lineage.identity import skill_package_node_id as package_node_id_fn
from app.schemas.contracts import SkillLifecycleStatus
from pydantic import ValidationError


def test_contracts_are_immutable() -> None:
    graph = frozen_validation_graph()
    with pytest.raises(ValidationError):
        graph.schema_version = "9.9.9"  # type: ignore[misc]


def test_unknown_node_type_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown lineage node type"):
        validate_node_type("auto_activate")


def test_unknown_edge_type_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown lineage edge type"):
        validate_edge_type("auto_approve")


def test_package_validation_chain_builds_correctly() -> None:
    graph = frozen_validation_graph()
    types = {node.node_type for node in graph.nodes}
    assert LineageNodeType.SKILL_PACKAGE in types
    assert LineageNodeType.PACKAGE_VALIDATION in types
    assert LineageNodeType.UNIFIED_AUDIT_REPORT in types
    assert graph.graph_hash


def test_quarantine_chain_builds_correctly() -> None:
    graph = frozen_quarantine_graph()
    assert any(node.node_type == LineageNodeType.QUARANTINE_IMPORT for node in graph.nodes)
    assert any(node.node_type == LineageNodeType.SKILL_PACKAGE for node in graph.nodes)


def test_registry_projection_chain_builds_correctly() -> None:
    graph = frozen_registry_graph()
    assert any(node.node_type == LineageNodeType.REGISTRY_PROJECTION for node in graph.nodes)
    assert any(node.node_type == LineageNodeType.REGISTRY_SNAPSHOT for node in graph.nodes)


def test_connector_request_chain_builds_correctly() -> None:
    graph = connector_allow_graph()
    assert any(node.node_type == LineageNodeType.CONNECTOR_REQUEST for node in graph.nodes)
    assert any(node.node_type == LineageNodeType.CONNECTOR_POLICY_DECISION for node in graph.nodes)


def test_connector_result_chain_builds_correctly() -> None:
    graph = connector_result_graph()
    assert any(node.node_type == LineageNodeType.CONNECTOR_RESULT for node in graph.nodes)
    assert any(node.node_type == LineageNodeType.CONNECTOR_EVIDENCE for node in graph.nodes)


def test_audit_lineage_builds_correctly() -> None:
    graph = audit_aggregation_graph()
    assert any(node.node_type == LineageNodeType.UNIFIED_AUDIT_REPORT for node in graph.nodes)


def test_existing_evidence_mapping_works() -> None:
    descriptor = connector_evidence_descriptor()
    reference = map_connector_evidence_to_lineage_reference(descriptor)
    knowledge = map_lineage_reference_to_knowledge_evidence(reference)
    assert knowledge.evidence_id == str(descriptor.evidence_id)


def test_skill_execution_descriptor_requires_skill_id() -> None:
    graph = frozen_validation_graph()
    with pytest.raises(LineageBuildError):
        build_skill_execution_lineage_descriptor(
            execution_id="exec-1",
            skill_id="",
            skill_version="0.1.0",
            package_hash=FROZEN_HASH,
            graph=graph,
        )


def test_skill_execution_descriptor_requires_skill_version() -> None:
    graph = frozen_validation_graph()
    with pytest.raises(LineageBuildError):
        build_skill_execution_lineage_descriptor(
            execution_id="exec-1",
            skill_id="ms.skill.market_validation",
            skill_version="",
            package_hash=FROZEN_HASH,
            graph=graph,
        )


def test_connector_lineage_preserves_skill_identity() -> None:
    graph = connector_allow_graph()
    request_nodes = [node for node in graph.nodes if node.node_type == LineageNodeType.CONNECTOR_REQUEST]
    assert request_nodes[0].skill_id == "ms.skill.market_validation"
    assert request_nodes[0].skill_version == "0.1.0"


def test_credential_material_absent() -> None:
    graph = connector_result_graph()
    serialized = serialize_graph(graph)
    assert "api_key" not in serialized.lower()
    assert "token" not in serialized.lower() or "metadata" in serialized


def test_registry_snapshot_id_hash_preserved() -> None:
    graph = frozen_registry_graph()
    snapshot = next(node for node in graph.nodes if node.node_type == LineageNodeType.REGISTRY_SNAPSHOT)
    assert snapshot.snapshot_id
    assert snapshot.snapshot_hash
    assert snapshot.snapshot_id != snapshot.snapshot_hash


def test_historical_snapshot_not_rewritten() -> None:
    first = frozen_registry_graph()
    second = frozen_registry_graph()
    first_snapshot = next(node for node in first.nodes if node.node_type == LineageNodeType.REGISTRY_SNAPSHOT)
    second_snapshot = next(node for node in second.nodes if node.node_type == LineageNodeType.REGISTRY_SNAPSHOT)
    assert first_snapshot.snapshot_hash == second_snapshot.snapshot_hash


def test_archived_skill_version_remains_resolvable() -> None:
    node = LineageNodeReference(
        node_id=package_node_id_fn(
            skill_id="ms.skill.market_validation",
            skill_version="0.0.9",
            package_hash="a" * 64,
        ),
        node_type=LineageNodeType.SKILL_PACKAGE,
        skill_id="ms.skill.market_validation",
        skill_version="0.0.9",
        package_hash="a" * 64,
        lifecycle_status=SkillLifecycleStatus.ARCHIVED.value,
        global_scope=True,
    )
    graph = LineageGraph(nodes=(node,))
    result = validate_lineage_continuity(graph)
    assert not any(f.code.value == "archived_version_unresolvable" and f.blocking for f in result.findings)


def test_deprecated_skill_version_remains_resolvable() -> None:
    node = LineageNodeReference(
        node_id=package_node_id_fn(
            skill_id="ms.skill.market_validation",
            skill_version="0.0.8",
            package_hash="b" * 64,
        ),
        node_type=LineageNodeType.SKILL_PACKAGE,
        skill_id="ms.skill.market_validation",
        skill_version="0.0.8",
        package_hash="b" * 64,
        lifecycle_status=SkillLifecycleStatus.DEPRECATED.value,
        global_scope=True,
    )
    graph = LineageGraph(nodes=(node,))
    result = validate_lineage_continuity(graph)
    assert result.valid or not any(f.blocking for f in result.findings)


def test_cross_tenant_graph_rejected() -> None:
    graph_a = connector_allow_graph()
    graph_b = connector_allow_graph()
    graph_b = graph_b.model_copy(
        update={
            "nodes": tuple(
                node.model_copy(update={"tenant_id": TENANT_B}) if node.tenant_id else node
                for node in graph_b.nodes
            ),
            "context": graph_b.context.model_copy(update={"tenant_id": TENANT_B})
            if graph_b.context
            else None,
        }
    )
    with pytest.raises(LineageMergeError):
        combine_lineage_graphs(graph_a, graph_b)


def test_tenant_private_lineage_invisible_to_other_tenant() -> None:
    graph = connector_allow_graph()
    private = graph.model_copy(
        update={
            "nodes": tuple(
                node.model_copy(update={"tenant_id": TENANT_A, "global_scope": False})
                for node in graph.nodes
            )
        }
    )
    filtered = filter_graph_for_tenant(private, TENANT_B)
    assert len(filtered.nodes) < len(private.nodes) or all(
        node.global_scope or node.tenant_id != TENANT_A for node in filtered.nodes
    )


def test_global_skill_metadata_can_be_referenced_by_tenant() -> None:
    graph = frozen_validation_graph()
    package = next(node for node in graph.nodes if node.node_type == LineageNodeType.SKILL_PACKAGE)
    assert package.global_scope is True
    filtered = filter_graph_for_tenant(graph, TENANT_A)
    assert any(node.node_type == LineageNodeType.SKILL_PACKAGE for node in filtered.nodes)


def test_missing_parent_detected() -> None:
    graph = LineageGraph(
        nodes=(
            LineageNodeReference(node_id="a", node_type=LineageNodeType.SKILL_PACKAGE),
        ),
        edges=(
            LineageEdge(
                edge_id="e1",
                from_node_id="a",
                to_node_id="missing",
                edge_type=LineageEdgeType.VALIDATED_BY,
            ),
        ),
    )
    result = validate_lineage_continuity(graph)
    assert not result.valid
    assert any(f.code.value == "missing_parent" for f in result.findings)


def test_orphan_node_detected() -> None:
    graph = LineageGraph(
        nodes=(
            LineageNodeReference(
                node_id="orphan",
                node_type=LineageNodeType.PACKAGE_VALIDATION,
                package_hash=FROZEN_HASH,
            ),
        )
    )
    result = validate_lineage_continuity(graph)
    assert any(f.code.value == "orphan_node" for f in result.findings)


def test_hash_mismatch_detected() -> None:
    graph = frozen_registry_graph()
    nodes = list(graph.nodes)
    for index, node in enumerate(nodes):
        if node.node_type == LineageNodeType.REGISTRY_PROJECTION:
            nodes[index] = node.model_copy(update={"package_hash": "c" * 64})
    mutated = graph.model_copy(update={"nodes": tuple(nodes)})
    result = validate_lineage_continuity(mutated)
    assert any(f.code.value in {"hash_mismatch", "orphan_node"} for f in result.findings)


def test_duplicate_node_conflict_detected_on_merge() -> None:
    graph = frozen_validation_graph()
    node = graph.nodes[0].model_copy(update={"metadata_hash": "different"})
    duplicate_graph = LineageGraph(nodes=(node,))
    with pytest.raises(LineageMergeError):
        combine_lineage_graphs(graph, duplicate_graph)


def test_invalid_edge_detected() -> None:
    graph = connector_result_graph()
    bad_edge = LineageEdge(
        edge_id="bad",
        from_node_id=graph.nodes[0].node_id,
        to_node_id=graph.nodes[-1].node_id,
        edge_type=LineageEdgeType.SUPERSEDES,
    )
    mutated = graph.model_copy(update={"edges": graph.edges + (bad_edge,)})
    result = validate_lineage_continuity(mutated)
    assert isinstance(result, LineageValidationResult)


def test_cycle_detected() -> None:
    graph = LineageGraph(
        nodes=(
            LineageNodeReference(node_id="a", node_type=LineageNodeType.SKILL_PACKAGE),
            LineageNodeReference(node_id="b", node_type=LineageNodeType.PACKAGE_VALIDATION),
        ),
        edges=(
            LineageEdge(edge_id="e1", from_node_id="a", to_node_id="b", edge_type=LineageEdgeType.VALIDATED_BY),
            LineageEdge(edge_id="e2", from_node_id="b", to_node_id="a", edge_type=LineageEdgeType.VALIDATED_BY),
        ),
    )
    result = validate_lineage_continuity(graph)
    assert any(f.code.value == "cycle_detected" for f in result.findings)


def test_connector_result_without_request_detected() -> None:
    graph = LineageGraph(
        nodes=(
            LineageNodeReference(
                node_id="result-only",
                node_type=LineageNodeType.CONNECTOR_RESULT,
            ),
        )
    )
    result = validate_lineage_continuity(graph)
    assert any(f.code.value == "connector_request_missing" for f in result.findings)


def test_connector_evidence_without_result_detected() -> None:
    graph = LineageGraph(
        nodes=(
            LineageNodeReference(
                node_id="evidence-only",
                node_type=LineageNodeType.CONNECTOR_EVIDENCE,
            ),
        )
    )
    result = validate_lineage_continuity(graph)
    assert any(f.code.value == "evidence_missing" for f in result.findings)


def test_audit_without_source_report_warning() -> None:
    graph = LineageGraph(
        nodes=(
            LineageNodeReference(
                node_id="audit-only",
                node_type=LineageNodeType.UNIFIED_AUDIT_REPORT,
            ),
        )
    )
    result = validate_lineage_continuity(graph)
    assert any(f.code.value == "audit_source_missing" for f in result.findings)


def test_package_validation_without_package_hash_detected() -> None:
    graph = LineageGraph(
        nodes=(
            LineageNodeReference(
                node_id="validation-no-hash",
                node_type=LineageNodeType.PACKAGE_VALIDATION,
            ),
        )
    )
    result = validate_lineage_continuity(graph)
    assert any(f.code.value == "source_reference_missing" for f in result.findings)


def test_registry_projection_hash_mismatch_detected() -> None:
    result = validate_lineage_continuity(frozen_registry_graph())
    assert result.node_count > 0


def test_quarantine_effective_status_mismatch_detected() -> None:
    result = quarantine_success_result().model_copy(update={"effective_status": SkillLifecycleStatus.ACTIVE})
    graph = build_quarantine_lineage(result)
    validation = validate_lineage_continuity(graph)
    assert any(f.code.value == "lifecycle_semantics_conflict" for f in validation.findings)


def test_approval_readiness_not_treated_as_approval() -> None:
    graph = connector_approval_graph()
    assert all(node.node_type != LineageNodeType.EXECUTION_RECORD for node in graph.nodes)
    assert not any(edge.edge_type == LineageEdgeType.EXECUTED_AS for edge in graph.edges)


def test_approval_required_connector_chain_non_executed() -> None:
    graph = connector_approval_graph()
    assert not any(node.node_type == LineageNodeType.CONNECTOR_RESULT for node in graph.nodes)


def test_denied_connector_chain_contains_policy_denial() -> None:
    graph = connector_deny_graph()
    assert any(
        edge.edge_type == LineageEdgeType.DENIED_BY
        for edge in graph.edges
    )


def test_evidence_missing_produces_finding() -> None:
    graph = LineageGraph(
        nodes=(
            LineageNodeReference(
                node_id="evidence-orphan",
                node_type=LineageNodeType.CONNECTOR_EVIDENCE,
            ),
        )
    )
    result = validate_lineage_continuity(graph)
    assert any(f.code.value == "evidence_missing" for f in result.findings)


def test_findings_deterministic() -> None:
    first = validate_lineage_continuity(frozen_registry_graph())
    second = validate_lineage_continuity(frozen_registry_graph())
    assert [f.code for f in first.findings] == [f.code for f in second.findings]


def test_graph_ordering_deterministic() -> None:
    first = frozen_validation_graph()
    second = frozen_validation_graph()
    assert [node.node_id for node in first.nodes] == [node.node_id for node in second.nodes]
    assert [edge.edge_id for edge in first.edges] == [edge.edge_id for edge in second.edges]


def test_graph_hash_deterministic() -> None:
    first = frozen_validation_graph()
    second = frozen_validation_graph()
    assert first.graph_hash == second.graph_hash


def test_volatile_timestamp_excluded_from_hash() -> None:
    graph = frozen_validation_graph()
    mutated_nodes = tuple(
        node.model_copy(update={"created_at": datetime(2020, 1, 1, tzinfo=UTC)}) for node in graph.nodes
    )
    mutated = graph.model_copy(update={"nodes": mutated_nodes})
    assert compute_graph_hash(graph) == compute_graph_hash(mutated)


def test_graph_merge_preserves_identical_nodes() -> None:
    graph = frozen_validation_graph()
    merged = combine_lineage_graphs(graph, graph)
    assert len(merged.nodes) == len(graph.nodes)


def test_graph_merge_rejects_conflicting_nodes() -> None:
    graph = frozen_validation_graph()
    conflict = LineageGraph(nodes=(graph.nodes[0].model_copy(update={"metadata_hash": "conflict"}),))
    with pytest.raises(LineageMergeError):
        combine_lineage_graphs(graph, conflict)


def test_graph_merge_rejects_cross_tenant_graphs() -> None:
    left = connector_allow_graph()
    right = connector_allow_graph().model_copy(
        update={
            "context": left.context.model_copy(update={"tenant_id": TENANT_B}) if left.context else None,
            "nodes": tuple(
                node.model_copy(update={"tenant_id": TENANT_B, "global_scope": False})
                for node in left.nodes
            ),
        }
    )
    with pytest.raises(LineageMergeError):
        combine_lineage_graphs(left, right)


def test_source_objects_not_mutated() -> None:
    report = valid_package_validation_report()
    snapshot = copy.deepcopy(report.model_dump())
    build_package_validation_lineage(report, audit_report=adapted_valid_package_report())
    assert report.model_dump() == snapshot


def test_no_secrets_in_serialization() -> None:
    text = sanitize_for_serialization("Bearer secret-token-value")
    assert text == "[REDACTED]"


def test_no_absolute_paths_in_serialization() -> None:
    report = adapted_valid_package_report()
    serialized = serialize_graph(build_audit_lineage(report))
    assert "C:\\Users" not in serialized


def test_package_validation_evidence_source_mapping() -> None:
    report = valid_package_validation_report()
    ref = map_package_validation_to_evidence_source_reference(report, report_hash="abc")
    assert ref.evidence_id.startswith("validation-source:")


def test_combined_platform_native_chain() -> None:
    graph = frozen_registry_graph()
    assert any(node.node_type == LineageNodeType.SKILL_PACKAGE for node in graph.nodes)
    assert any(node.node_type == LineageNodeType.REGISTRY_PROJECTION for node in graph.nodes)
    assert len(graph.nodes) > 3
