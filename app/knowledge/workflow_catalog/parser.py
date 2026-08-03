"""Static n8n workflow JSON parser — data only, no execution."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.knowledge.workflow_catalog.candidate_eligibility import (
    CandidateEvaluation,
    evaluate_candidate_eligibility,
)
from app.knowledge.workflow_catalog.classifiers import ClassificationResult, classify_workflow
from app.knowledge.workflow_catalog.contracts import (
    SOURCE_ARCHIVE_ID,
    CredentialReference,
    InvalidFileRecord,
    SecurityFindingRecord,
    WorkflowTemplateRecord,
)
from app.knowledge.workflow_catalog.normalization import (
    assess_documentation_quality,
    classify_functional_classes,
    extract_credential_references,
    extract_external_urls,
    extract_integrated_providers,
    normalize_name,
    redact_portable_text,
    sha256_bytes,
    side_effect_classes,
)
from app.knowledge.workflow_catalog.security_scan import scan_workflow
from app.knowledge.workflow_catalog.topology import topology_hashes


@dataclass
class ParseDiagnostics:
    node_count: int = 0
    connection_count: int = 0
    active_flag: bool = False
    sticky_note_present: bool = False
    documentation_quality: str = "none"
    functional_classes: list[str] = field(default_factory=list)
    expression_markers: bool = False
    pinned_data_present: bool = False
    topology_hash_aware: str = ""
    classification: ClassificationResult | None = None
    candidate_evaluation: CandidateEvaluation | None = None
    disabled_node_count: int = 0
    code_node_count: int = 0


@dataclass
class ParseOutcome:
    record: WorkflowTemplateRecord | None = None
    invalid: InvalidFileRecord | None = None
    diagnostics: ParseDiagnostics = field(default_factory=ParseDiagnostics)


def _is_n8n_workflow(data: Any) -> bool:
    return isinstance(data, dict) and isinstance(data.get("nodes"), list)


def _count_connections(data: dict[str, Any]) -> int:
    connections = data.get("connections") or {}
    count = 0
    if isinstance(connections, dict):
        for outputs in connections.values():
            if isinstance(outputs, dict):
                for branch in outputs.values():
                    if isinstance(branch, list):
                        for conn_list in branch:
                            if isinstance(conn_list, list):
                                count += len(conn_list)
    return count


def parse_workflow_data(
    data: dict[str, Any],
    *,
    source_path: str,
    source_path_hash: str,
    archive_id: str = SOURCE_ARCHIVE_ID,
    is_unique_or_canonical: bool = True,
) -> ParseOutcome:
    if not _is_n8n_workflow(data):
        return ParseOutcome(
            invalid=InvalidFileRecord(
                file_name=Path(source_path).name,
                source_path_hash=source_path_hash,
                reason="missing_nodes_array",
                error_type="invalid_shape",
            )
        )

    nodes = [n for n in data.get("nodes") or [] if isinstance(n, dict)]
    text = json.dumps(data, ensure_ascii=False)
    workflow_hash = sha256_bytes(text.encode("utf-8"))
    topology_aware, topology_neutral = topology_hashes(data)
    workflow_id = f"wf-{workflow_hash[:16]}"

    node_types = sorted({str(n.get("type", "unknown")) for n in nodes})
    cred_refs_raw = extract_credential_references(nodes)
    providers = extract_integrated_providers(nodes, node_types, text, cred_refs_raw)
    functional_classes = classify_functional_classes(node_types)
    triggers = [t for t in node_types if "trigger" in t.lower()]

    code_node_count = sum(
        1 for t in node_types if "code" in t.lower() and "n8n-nodes" in t
    )
    code_nodes = code_node_count > 0
    shell_nodes = any("executecommand" in t.lower() for t in node_types)
    db_nodes = any(
        k in t.lower()
        for t in node_types
        for k in ("postgres", "mysql", "mongodb", "redis")
    )
    ai_nodes = any("langchain" in t.lower() or "agent" in t.lower() for t in node_types)
    pub = any(
        k in t.lower()
        for t in node_types
        for k in (
            "telegram",
            "instagram",
            "facebook",
            "linkedin",
            "wordpress",
            "gmail",
            "twitter",
        )
    )
    billing = any(k in text.lower() for k in ("stripe", "payment", "billing", "paypal"))
    destructive = bool(
        re.search(r"\b(DROP\s+TABLE|DELETE\s+FROM|TRUNCATE\s+TABLE)\b", text, re.I)
    )
    sticky = any("stickynote" in t.lower() for t in node_types)
    documentation_quality = assess_documentation_quality(nodes, node_types)
    personal = "elevated" if re.search(r"@\w+\.\w+", text) else "unknown"
    if re.search(r"passport|identity|ssn|document scan", text, re.I):
        personal = "high"

    cred_refs = [CredentialReference.model_validate(c) for c in cred_refs_raw]
    ext_urls = extract_external_urls(text)
    side_effects = side_effect_classes(
        publication=pub,
        billing=billing,
        destructive=destructive,
        database=db_nodes,
        messaging=pub,
    )

    security: list[SecurityFindingRecord] = scan_workflow(
        workflow_id=workflow_id,
        text=text,
        node_types=node_types,
        nodes=nodes,
        archive_id=archive_id,
    )

    name = str(data.get("name") or Path(source_path).stem)
    description = str(data.get("description") or "")
    classification = classify_workflow(
        name,
        description,
        node_types,
        providers,
        side_effects,
        nodes=nodes,
        documentation_quality=documentation_quality,
    )

    provisional = WorkflowTemplateRecord(
        workflow_template_id=workflow_id,
        original_name=redact_portable_text(name)[:500],
        normalized_name=normalize_name(name),
        source_archive_id=archive_id,
        source_path_hash=source_path_hash,
        workflow_hash=workflow_hash,
        topology_hash=topology_neutral,
        description=redact_portable_text(description)[:500],
        use_case=normalize_name(name)[:200],
        categories=classification.categories,
        trigger_types=triggers or node_types[:3],
        node_types=node_types,
        providers=providers,
        credential_references=cred_refs,
        environment_references=sorted(set(re.findall(r"\$env\.[A-Z0-9_]+", text))),
        side_effects=side_effects,
        publication_actions=pub,
        billing_actions=billing,
        destructive_actions=destructive,
        personal_data_risk=personal,  # type: ignore[arg-type]
        code_nodes=code_nodes,
        shell_nodes=shell_nodes,
        database_nodes=db_nodes,
        AI_nodes=ai_nodes,
        external_urls=ext_urls,
        security_findings=security,
        provider_constraints=[],
        deprecated_components=[],
        adaptation_status="catalog_only",
        quarantine_status="quarantined",
        tenant_scope="global",
        provenance={
            "source_type": "external_archive",
            "archive_id": archive_id,
            "source_id": source_path_hash,
            "content_hash": workflow_hash,
            "program_phase": "KB-WPL-01.2.1",
        },
    )

    candidate_eval = evaluate_candidate_eligibility(
        provisional,
        classification,
        is_unique_or_canonical=is_unique_or_canonical,
        use_case_identifiable=bool(provisional.use_case.strip()),
        metadata_complete=bool(provisional.workflow_template_id and provisional.topology_hash),
    )

    record = provisional.model_copy(update={"adaptation_status": candidate_eval.adaptation_status})

    diag = ParseDiagnostics(
        node_count=len(nodes),
        connection_count=_count_connections(data),
        active_flag=data.get("active") is True,
        sticky_note_present=sticky,
        documentation_quality=documentation_quality,
        functional_classes=functional_classes,
        expression_markers="{{" in text or "$(" in text,
        pinned_data_present="pinData" in text,
        topology_hash_aware=topology_aware,
        classification=classification,
        candidate_evaluation=candidate_eval,
        disabled_node_count=sum(1 for n in nodes if n.get("disabled") is True),
        code_node_count=code_node_count,
    )
    return ParseOutcome(record=record, diagnostics=diag)


def parse_workflow_file(
    path: Path,
    *,
    archive_id: str = SOURCE_ARCHIVE_ID,
    is_unique_or_canonical: bool = True,
) -> ParseOutcome:
    rel = path.name
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return ParseOutcome(
            invalid=InvalidFileRecord(
                file_name=rel,
                source_path_hash=sha256_bytes(rel.encode("utf-8")),
                reason=str(exc),
                error_type="read_error",
            )
        )
    source_path_hash = sha256_bytes(raw)
    try:
        text = raw.decode("utf-8")
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return ParseOutcome(
            invalid=InvalidFileRecord(
                file_name=rel,
                source_path_hash=source_path_hash,
                reason=str(exc),
                error_type="json_decode_error",
            )
        )
    except UnicodeDecodeError as exc:
        return ParseOutcome(
            invalid=InvalidFileRecord(
                file_name=rel,
                source_path_hash=source_path_hash,
                reason=str(exc),
                error_type="unicode_error",
            )
        )
    if not isinstance(data, dict):
        return ParseOutcome(
            invalid=InvalidFileRecord(
                file_name=rel,
                source_path_hash=source_path_hash,
                reason="root_not_object",
                error_type="invalid_shape",
            )
        )
    return parse_workflow_data(
        data,
        source_path=rel,
        source_path_hash=source_path_hash,
        archive_id=archive_id,
        is_unique_or_canonical=is_unique_or_canonical,
    )
