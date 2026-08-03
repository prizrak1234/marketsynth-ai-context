"""Pure lineage graph builders (SKILL-01.7)."""

from __future__ import annotations

from app.audit.contracts import UnifiedAuditReport
from app.connectors.contracts import (
    ConnectorEvidenceDescriptor,
    ConnectorExecutionRequest,
    ConnectorExecutionResult,
    ConnectorPolicyDecision,
)
from app.lineage.contracts import (
    AuditLineageDescriptor,
    LineageContext,
    LineageEdge,
    LineageEdgeType,
    LineageGraph,
    LineageNodeReference,
    LineageNodeType,
    LineageSourceReference,
    SkillExecutionLineageDescriptor,
)
from app.lineage.errors import LineageBuildError, LineageMergeError
from app.lineage.identity import (
    approval_reference_node_id,
    audit_report_node_id,
    connector_evidence_node_id,
    connector_policy_node_id,
    connector_request_node_id,
    connector_result_node_id,
    evidence_node_id,
    metadata_hash,
    model_metadata_hash,
    package_validation_node_id,
    quarantine_import_node_id,
    registry_projection_node_id,
    registry_snapshot_node_id,
    skill_package_node_id,
)
from app.lineage.serialization import compute_graph_hash, sorted_edges, sorted_nodes
from app.skills.quarantine_contracts import QuarantineImportResult
from app.skills.registry_contracts import SkillRegistryProjectionResult, SkillRegistrySnapshot
from app.skills.validation_contracts import SkillPackageValidationReport


def _edge(edge_id: str, from_id: str, to_id: str, edge_type: LineageEdgeType) -> LineageEdge:
    return LineageEdge(
        edge_id=edge_id,
        from_node_id=from_id,
        to_node_id=to_id,
        edge_type=edge_type,
    )


def _finalize_graph(
    *,
    nodes: list[LineageNodeReference],
    edges: list[LineageEdge],
    context: LineageContext | None = None,
    source_references: tuple[LineageSourceReference, ...] = (),
) -> LineageGraph:
    graph = LineageGraph(
        nodes=sorted_nodes(tuple(nodes)),
        edges=sorted_edges(tuple(edges)),
        context=context,
        source_references=source_references,
    )
    return graph.model_copy(update={"graph_hash": compute_graph_hash(graph)})


def build_package_validation_lineage(
    report: SkillPackageValidationReport,
    *,
    audit_report: UnifiedAuditReport | None = None,
    tenant_id: str | None = None,
    project_id: str | None = None,
) -> LineageGraph:
    if report.skill_id is None or report.skill_version is None or report.package_hash is None:
        raise LineageBuildError(
            "Package validation lineage requires skill identity and package hash."
        )

    report_hash = (
        audit_report.report_hash
        if audit_report is not None
        else metadata_hash(
            {
                "validator_version": report.validator_version,
                "package_hash": report.package_hash,
                "valid": report.valid,
            }
        )
    )
    package_node_id = skill_package_node_id(
        skill_id=report.skill_id,
        skill_version=report.skill_version,
        package_hash=report.package_hash,
    )
    validation_node_id = package_validation_node_id(
        validator_version=report.validator_version,
        package_hash=report.package_hash,
        report_hash=report_hash,
    )

    nodes = [
        LineageNodeReference(
            node_id=package_node_id,
            node_type=LineageNodeType.SKILL_PACKAGE,
            skill_id=report.skill_id,
            skill_version=report.skill_version,
            package_hash=report.package_hash,
            lifecycle_status=report.status.value if report.status else None,
            tenant_id=tenant_id,
            project_id=project_id,
            created_at=report.created_at,
            source_system="skill_package_validator",
            metadata_hash=model_metadata_hash(report),
            global_scope=True,
        ),
        LineageNodeReference(
            node_id=validation_node_id,
            node_type=LineageNodeType.PACKAGE_VALIDATION,
            skill_id=report.skill_id,
            skill_version=report.skill_version,
            package_hash=report.package_hash,
            report_hash=report_hash,
            tenant_id=tenant_id,
            project_id=project_id,
            created_at=report.created_at,
            source_system="skill_package_validator",
            metadata_hash=report_hash,
        ),
    ]
    edges = [
        _edge(
            f"{package_node_id}->validated_by->{validation_node_id}",
            package_node_id,
            validation_node_id,
            LineageEdgeType.VALIDATED_BY,
        )
    ]

    source_refs: list[LineageSourceReference] = [
        LineageSourceReference(
            source_system="skill_package_validator",
            source_id=report.package_hash,
            source_hash=model_metadata_hash(report),
        )
    ]

    if audit_report is not None:
        audit_node_id = audit_report_node_id(report_hash=audit_report.report_hash)
        nodes.append(
            LineageNodeReference(
                node_id=audit_node_id,
                node_type=LineageNodeType.UNIFIED_AUDIT_REPORT,
                skill_id=report.skill_id,
                skill_version=report.skill_version,
                package_hash=report.package_hash,
                report_hash=audit_report.report_hash,
                tenant_id=tenant_id,
                project_id=project_id,
                created_at=audit_report.generated_at,
                source_system="unified_audit_report",
                metadata_hash=audit_report.report_hash,
            )
        )
        edges.append(
            _edge(
                f"{validation_node_id}->audited_by->{audit_node_id}",
                validation_node_id,
                audit_node_id,
                LineageEdgeType.AUDITED_BY,
            )
        )
        source_refs.append(
            LineageSourceReference(
                source_system="unified_audit_report",
                source_id=audit_report.report_hash,
                source_hash=audit_report.report_hash,
            )
        )

    context = LineageContext(
        tenant_id=tenant_id,
        project_id=project_id,
        skill_id=report.skill_id,
        skill_version=report.skill_version,
    )
    return _finalize_graph(
        nodes=nodes,
        edges=edges,
        context=context,
        source_references=tuple(source_refs),
    )


def build_quarantine_lineage(
    result: QuarantineImportResult,
    *,
    audit_report: UnifiedAuditReport | None = None,
) -> LineageGraph:
    if result.import_id is None or result.materialized_package_hash is None:
        raise LineageBuildError("Quarantine lineage requires import_id and materialized hash.")

    tenant_id = result.provenance.tenant_id if result.provenance else None
    project_id = result.provenance.project_id if result.provenance else None
    quarantine_node_id = quarantine_import_node_id(
        import_id=result.import_id,
        materialized_hash=result.materialized_package_hash,
    )

    nodes: list[LineageNodeReference] = [
        LineageNodeReference(
            node_id=quarantine_node_id,
            node_type=LineageNodeType.QUARANTINE_IMPORT,
            package_hash=result.materialized_package_hash,
            lifecycle_status=result.effective_status.value if result.effective_status else None,
            tenant_id=tenant_id,
            project_id=project_id,
            created_at=result.created_at,
            source_system="quarantine_import_adapter",
            metadata_hash=model_metadata_hash(result),
        )
    ]
    edges: list[LineageEdge] = []
    source_refs = [
        LineageSourceReference(
            source_system="quarantine_import_adapter",
            source_id=result.import_id,
            source_hash=model_metadata_hash(result),
        )
    ]

    if result.package_validation_report is not None:
        validation_graph = build_package_validation_lineage(
            result.package_validation_report,
            audit_report=audit_report,
            tenant_id=tenant_id,
            project_id=project_id,
        )
        nodes.extend(validation_graph.nodes)
        edges.extend(validation_graph.edges)
        source_refs.extend(validation_graph.source_references)
        quarantine_edges = [
            _edge(
                f"{quarantine_node_id}->imported_as->{node.node_id}",
                quarantine_node_id,
                node.node_id,
                LineageEdgeType.IMPORTED_AS,
            )
            for node in validation_graph.nodes
            if node.node_type == LineageNodeType.SKILL_PACKAGE
        ]
        edges.extend(quarantine_edges)

    context = LineageContext(tenant_id=tenant_id, project_id=project_id)
    return _finalize_graph(
        nodes=nodes, edges=edges, context=context, source_references=tuple(source_refs)
    )


def build_registry_projection_lineage(
    projection: SkillRegistryProjectionResult,
    *,
    snapshot: SkillRegistrySnapshot | None = None,
    validation_graph: LineageGraph | None = None,
) -> LineageGraph:
    version = projection.version_record
    if version is None:
        raise LineageBuildError("Registry projection lineage requires version_record.")

    registry_node_id = registry_projection_node_id(
        skill_id=version.skill_id,
        skill_version=version.version,
        package_hash=version.package_hash,
    )
    nodes: list[LineageNodeReference] = [
        LineageNodeReference(
            node_id=registry_node_id,
            node_type=LineageNodeType.REGISTRY_PROJECTION,
            skill_id=version.skill_id,
            skill_version=version.version,
            package_hash=version.package_hash,
            lifecycle_status=version.lifecycle_status.value,
            tenant_id=version.owner_tenant_id,
            created_at=version.recorded_at,
            source_system="skill_registry_projection",
            metadata_hash=model_metadata_hash(version),
            global_scope=version.owner_tenant_id is None,
        )
    ]
    edges: list[LineageEdge] = []
    source_refs: list[LineageSourceReference] = [
        LineageSourceReference(
            source_system="skill_registry_projection",
            source_id=f"{version.skill_id}:{version.version}",
            source_hash=model_metadata_hash(projection),
        )
    ]

    if snapshot is not None:
        snapshot_node_id = registry_snapshot_node_id(snapshot_id=snapshot.snapshot_id)
        nodes.append(
            LineageNodeReference(
                node_id=snapshot_node_id,
                node_type=LineageNodeType.REGISTRY_SNAPSHOT,
                snapshot_id=snapshot.snapshot_id,
                snapshot_hash=snapshot.snapshot_hash,
                created_at=snapshot.generated_at,
                source_system="skill_registry_snapshot",
                metadata_hash=snapshot.snapshot_hash,
                global_scope=True,
            )
        )
        edges.append(
            _edge(
                f"{registry_node_id}->included_in->{snapshot_node_id}",
                registry_node_id,
                snapshot_node_id,
                LineageEdgeType.INCLUDED_IN,
            )
        )

    if validation_graph is not None:
        nodes.extend(validation_graph.nodes)
        edges.extend(validation_graph.edges)
        source_refs.extend(validation_graph.source_references)
        for node in validation_graph.nodes:
            if node.node_type == LineageNodeType.PACKAGE_VALIDATION:
                edges.append(
                    _edge(
                        f"{node.node_id}->projected_to->{registry_node_id}",
                        node.node_id,
                        registry_node_id,
                        LineageEdgeType.PROJECTED_TO,
                    )
                )

    context = LineageContext(skill_id=version.skill_id, skill_version=version.version)
    return _finalize_graph(
        nodes=nodes, edges=edges, context=context, source_references=tuple(source_refs)
    )


def build_connector_request_lineage(
    request: ConnectorExecutionRequest,
    policy: ConnectorPolicyDecision,
    *,
    audit_report: UnifiedAuditReport | None = None,
) -> LineageGraph:
    request_node_id = connector_request_node_id(request_id=str(request.request_id))
    policy_node_id = connector_policy_node_id(
        request_id=str(request.request_id),
        outcome=policy.outcome.value,
    )

    nodes = [
        LineageNodeReference(
            node_id=request_node_id,
            node_type=LineageNodeType.CONNECTOR_REQUEST,
            tenant_id=str(request.tenant_id),
            project_id=str(request.project_id),
            skill_id=request.skill_id,
            skill_version=request.skill_version,
            connector_id=request.connector_id,
            connector_version=request.connector_version,
            tool_id=request.tool_id,
            created_at=request.requested_at,
            source_system="connector_gateway",
            metadata_hash=model_metadata_hash(request),
        ),
        LineageNodeReference(
            node_id=policy_node_id,
            node_type=LineageNodeType.CONNECTOR_POLICY_DECISION,
            tenant_id=str(request.tenant_id),
            project_id=str(request.project_id),
            skill_id=request.skill_id,
            skill_version=request.skill_version,
            connector_id=request.connector_id,
            connector_version=request.connector_version,
            tool_id=request.tool_id,
            created_at=request.requested_at,
            source_system="connector_policy_engine",
            metadata_hash=model_metadata_hash(policy),
        ),
    ]
    edges = [
        _edge(
            f"{request_node_id}->requested_by->{policy_node_id}",
            request_node_id,
            policy_node_id,
            LineageEdgeType.REQUESTED_BY,
        )
    ]
    if policy.outcome.value == "deny":
        edges.append(
            _edge(
                f"{policy_node_id}->denied_by->{request_node_id}",
                policy_node_id,
                request_node_id,
                LineageEdgeType.DENIED_BY,
            )
        )
    if request.approval_reference:
        approval_id = approval_reference_node_id(approval_reference=request.approval_reference)
        nodes.append(
            LineageNodeReference(
                node_id=approval_id,
                node_type=LineageNodeType.APPROVAL_REFERENCE,
                tenant_id=str(request.tenant_id),
                project_id=str(request.project_id),
                external_reference_id=request.approval_reference,
                source_system="approval_reference",
                metadata_hash=request.approval_reference,
            )
        )
        edges.append(
            _edge(
                f"{request_node_id}->authorized_by->{approval_id}",
                request_node_id,
                approval_id,
                LineageEdgeType.AUTHORIZED_BY,
            )
        )

    if request.skill_id and request.skill_version:
        skill_node_id = skill_package_node_id(
            skill_id=request.skill_id,
            skill_version=request.skill_version,
            package_hash="unknown",
        )
        nodes.append(
            LineageNodeReference(
                node_id=skill_node_id,
                node_type=LineageNodeType.SKILL_VERSION,
                skill_id=request.skill_id,
                skill_version=request.skill_version,
                tenant_id=str(request.tenant_id),
                source_system="skill_registry",
                global_scope=True,
            )
        )
        edges.append(
            _edge(
                f"{skill_node_id}->requested_by->{request_node_id}",
                skill_node_id,
                request_node_id,
                LineageEdgeType.REQUESTED_BY,
            )
        )

    if audit_report is not None:
        audit_node_id = audit_report_node_id(report_hash=audit_report.report_hash)
        nodes.append(
            LineageNodeReference(
                node_id=audit_node_id,
                node_type=LineageNodeType.UNIFIED_AUDIT_REPORT,
                report_hash=audit_report.report_hash,
                tenant_id=str(request.tenant_id),
                project_id=str(request.project_id),
                source_system="unified_audit_report",
                metadata_hash=audit_report.report_hash,
            )
        )
        edges.append(
            _edge(
                f"{policy_node_id}->audited_by->{audit_node_id}",
                policy_node_id,
                audit_node_id,
                LineageEdgeType.AUDITED_BY,
            )
        )

    context = LineageContext(
        tenant_id=str(request.tenant_id),
        project_id=str(request.project_id),
        skill_id=request.skill_id,
        skill_version=request.skill_version,
    )
    return _finalize_graph(nodes=nodes, edges=edges, context=context)


def build_connector_result_lineage(
    request: ConnectorExecutionRequest,
    result: ConnectorExecutionResult,
    *,
    policy: ConnectorPolicyDecision | None = None,
    evidence: ConnectorEvidenceDescriptor | None = None,
    audit_report: UnifiedAuditReport | None = None,
) -> LineageGraph:
    from app.connectors.contracts import ConnectorPolicyOutcome

    effective_policy = policy or ConnectorPolicyDecision(
        outcome=ConnectorPolicyOutcome.ALLOW,
        reason="allowed",
    )
    request_graph = build_connector_request_lineage(
        request,
        effective_policy,
        audit_report=audit_report,
    )
    output_hash = model_metadata_hash(result.output_payload)[:16]
    result_node_id = connector_result_node_id(
        request_id=str(request.request_id),
        result_status=result.status.value,
        output_hash=output_hash,
    )
    request_node_id = connector_request_node_id(request_id=str(request.request_id))

    nodes = list(request_graph.nodes)
    edges = list(request_graph.edges)
    nodes.append(
        LineageNodeReference(
            node_id=result_node_id,
            node_type=LineageNodeType.CONNECTOR_RESULT,
            tenant_id=str(request.tenant_id),
            project_id=str(request.project_id),
            skill_id=request.skill_id,
            skill_version=request.skill_version,
            connector_id=result.connector_id,
            connector_version=result.connector_version,
            tool_id=result.tool_id,
            created_at=result.finished_at,
            source_system="connector_gateway",
            metadata_hash=model_metadata_hash(result),
        )
    )
    edges.append(
        _edge(
            f"{request_node_id}->executed_as->{result_node_id}",
            request_node_id,
            result_node_id,
            LineageEdgeType.EXECUTED_AS,
        )
    )

    descriptor = evidence or result.evidence_descriptor
    if descriptor is not None:
        evidence_node_id = connector_evidence_node_id(evidence_id=str(descriptor.evidence_id))
        nodes.append(
            LineageNodeReference(
                node_id=evidence_node_id,
                node_type=LineageNodeType.CONNECTOR_EVIDENCE,
                tenant_id=str(descriptor.tenant_id),
                project_id=str(descriptor.project_id),
                skill_id=descriptor.skill_id,
                skill_version=descriptor.skill_version,
                connector_id=descriptor.connector_id,
                connector_version=descriptor.connector_version,
                tool_id=descriptor.tool_id,
                evidence_id=str(descriptor.evidence_id),
                created_at=descriptor.finished_at,
                source_system="connector_evidence_descriptor",
                metadata_hash=descriptor.output_hash,
            )
        )
        edges.extend(
            [
                _edge(
                    f"{result_node_id}->produced->{evidence_node_id}",
                    result_node_id,
                    evidence_node_id,
                    LineageEdgeType.PRODUCED,
                ),
                _edge(
                    f"{evidence_node_id}->evidenced_by->{result_node_id}",
                    evidence_node_id,
                    result_node_id,
                    LineageEdgeType.EVIDENCED_BY,
                ),
            ]
        )

    return _finalize_graph(nodes=nodes, edges=edges, context=request_graph.context)


def build_audit_lineage(audit_report: UnifiedAuditReport) -> LineageGraph:
    audit_node_id = audit_report_node_id(report_hash=audit_report.report_hash)
    nodes = [
        LineageNodeReference(
            node_id=audit_node_id,
            node_type=LineageNodeType.UNIFIED_AUDIT_REPORT,
            tenant_id=audit_report.target.tenant_id,
            project_id=audit_report.target.project_id,
            skill_id=audit_report.target.target_id,
            skill_version=audit_report.target.target_version,
            package_hash=audit_report.target.package_hash,
            report_hash=audit_report.report_hash,
            connector_id=audit_report.target.connector_id,
            tool_id=audit_report.target.tool_id,
            created_at=audit_report.generated_at,
            source_system="unified_audit_report",
            metadata_hash=audit_report.report_hash,
        )
    ]
    edges: list[LineageEdge] = []
    for _index, source_ref in enumerate(audit_report.source_reports):
        source_node_id = (
            f"audit-source:{source_ref.source_system.value}:{source_ref.source_report_id}"
        )
        nodes.append(
            LineageNodeReference(
                node_id=source_node_id,
                node_type=LineageNodeType.EXISTING_EVIDENCE,
                report_hash=source_ref.source_hash,
                source_system=source_ref.source_system.value,
                metadata_hash=source_ref.source_hash,
            )
        )
        edges.append(
            _edge(
                f"{source_node_id}->references->{audit_node_id}",
                source_node_id,
                audit_node_id,
                LineageEdgeType.REFERENCES,
            )
        )

    for evidence_ref in audit_report.evidence_references:
        evidence_id = evidence_node_id(evidence_id=evidence_ref.evidence_id)
        nodes.append(
            LineageNodeReference(
                node_id=evidence_id,
                node_type=LineageNodeType.EXISTING_EVIDENCE,
                evidence_id=evidence_ref.evidence_id,
                source_system=evidence_ref.evidence_kind,
                metadata_hash=evidence_ref.output_hash or evidence_ref.input_hash,
            )
        )
        edges.append(
            _edge(
                f"{audit_node_id}->evidenced_by->{evidence_id}",
                audit_node_id,
                evidence_id,
                LineageEdgeType.EVIDENCED_BY,
            )
        )

    descriptor = AuditLineageDescriptor(
        audit_id=str(audit_report.audit_id),
        report_hash=audit_report.report_hash,
        target_node_ids=tuple(
            node.node_id
            for node in nodes
            if node.node_type != LineageNodeType.EXISTING_EVIDENCE
        ),
        source_report_ids=tuple(ref.source_report_id for ref in audit_report.source_reports),
        source_hashes=tuple(ref.source_hash for ref in audit_report.source_reports),
        evidence_ids=tuple(ref.evidence_id for ref in audit_report.evidence_references),
        generated_by=audit_report.provenance.generated_by,
        generation_mode=audit_report.provenance.generation_mode.value,
        owner_decision_required=audit_report.provenance.owner_decision_required,
        human_review_completed=False,
    )

    context = LineageContext(
        tenant_id=audit_report.target.tenant_id,
        project_id=audit_report.target.project_id,
        skill_id=audit_report.target.target_id,
        skill_version=audit_report.target.target_version,
    )
    graph = _finalize_graph(nodes=nodes, edges=edges, context=context)
    _ = descriptor  # descriptor is contract output for callers; graph is primary artifact
    return graph


def build_skill_execution_lineage_descriptor(
    *,
    execution_id: str,
    skill_id: str,
    skill_version: str,
    package_hash: str,
    graph: LineageGraph,
    status: str = "prepared",
) -> SkillExecutionLineageDescriptor:
    if not skill_id or not skill_version:
        raise LineageBuildError("Skill execution lineage requires skill_id and skill_version.")

    audit_ids = tuple(
        node.node_id
        for node in graph.nodes
        if node.node_type == LineageNodeType.UNIFIED_AUDIT_REPORT
    )
    connector_ids = tuple(
        node.node_id
        for node in graph.nodes
        if node.node_type == LineageNodeType.CONNECTOR_REQUEST
    )
    snapshot_node = next(
        (node for node in graph.nodes if node.node_type == LineageNodeType.REGISTRY_SNAPSHOT),
        None,
    )
    return SkillExecutionLineageDescriptor(
        execution_id=execution_id,
        skill_id=skill_id,
        skill_version=skill_version,
        package_hash=package_hash,
        registry_snapshot_id=snapshot_node.snapshot_id if snapshot_node else None,
        registry_snapshot_hash=snapshot_node.snapshot_hash if snapshot_node else None,
        tenant_id=graph.context.tenant_id if graph.context else None,
        project_id=graph.context.project_id if graph.context else None,
        connector_request_ids=connector_ids,
        audit_report_ids=audit_ids,
        status=status,
    )


def combine_lineage_graphs(*graphs: LineageGraph) -> LineageGraph:
    if not graphs:
        raise LineageMergeError("At least one graph is required.")

    tenant_ids = {
        graph.context.tenant_id
        for graph in graphs
        if graph.context and graph.context.tenant_id
    }
    if len(tenant_ids) > 1:
        raise LineageMergeError("Cross-tenant lineage graphs cannot be merged.")

    node_map: dict[str, LineageNodeReference] = {}
    for graph in graphs:
        for node in graph.nodes:
            existing = node_map.get(node.node_id)
            if existing is not None and existing.metadata_hash != node.metadata_hash:
                raise LineageMergeError(f"Duplicate node conflict for {node.node_id}.")
            node_map[node.node_id] = node

    edge_map: dict[str, LineageEdge] = {}
    for graph in graphs:
        for edge in graph.edges:
            edge_map[edge.edge_id] = edge

    source_map: dict[str, LineageSourceReference] = {}
    for graph in graphs:
        for source in graph.source_references:
            source_map[f"{source.source_system}:{source.source_id}"] = source

    context = next((graph.context for graph in graphs if graph.context is not None), None)
    return _finalize_graph(
        nodes=list(node_map.values()),
        edges=list(edge_map.values()),
        context=context,
        source_references=tuple(source_map.values()),
    )
