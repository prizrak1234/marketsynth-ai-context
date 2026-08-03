"""Architecture invariants — Knowledge Governance (no VectorDB/LLM impl)."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from app.domain.knowledge_governance import (
    citation_contract_is_complete,
    evaluate_knowledge_freshness,
)
from app.schemas.contracts import (
    KNOWLEDGE_GOVERNANCE_TO_LEGACY_STATUS,
    BenchmarkCase,
    CitationContract,
    KnowledgeConfidenceLevel,
    KnowledgeEvidenceRef,
    KnowledgeFreshnessState,
    KnowledgeGovernanceManifest,
    KnowledgeGovernanceStatus,
    KnowledgeObject,
    KnowledgeValidationStage,
    SemanticChunk,
)

ROOT = Path(__file__).resolve().parents[1]


def test_knowledge_governance_docs_exist() -> None:
    required = [
        "docs/architecture/adr_knowledge_governance.md",
        "docs/architecture/knowledge_governance_volume.md",
        "docs/rfc_knowledge_governance.md",
        "docs/knowledge_governance_developer_guide.md",
        "docs/knowledge_governance_manifest.md",
        "docs/knowledge_governance_runtime_invariants.md",
        "docs/knowledge_governance_subsystem.md",
    ]
    for rel in required:
        assert (ROOT / rel).is_file(), rel


def test_agents_and_development_reference_knowledge_governance() -> None:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    development = (ROOT / "docs/DEVELOPMENT.md").read_text(encoding="utf-8")
    assert "adr_knowledge_governance.md" in agents
    assert "Knowledge Governance" in development
    assert "Citation Contract" in agents or "CitationContract" in agents


def test_lifecycle_statuses_complete() -> None:
    values = {s.value for s in KnowledgeGovernanceStatus}
    assert values == {
        "draft",
        "validated",
        "published",
        "deprecated",
        "archived",
        "superseded",
    }


def test_knowledge_object_required_fields() -> None:
    fields = set(KnowledgeObject.model_fields.keys())
    required = {
        "knowledge_id",
        "owner",
        "reviewer",
        "review_date",
        "next_review",
        "confidence",
        "freshness",
        "visibility",
        "tenant",
        "domain",
        "evidence_chain",
        "decision_chain",
        "version",
        "status",
    }
    assert required.issubset(fields)


def test_semantic_chunk_fields() -> None:
    fields = set(SemanticChunk.model_fields.keys())
    assert {
        "title",
        "intent",
        "rule",
        "condition",
        "exception",
        "references",
    }.issubset(fields)


def test_benchmark_case_fields() -> None:
    fields = set(BenchmarkCase.model_fields.keys())
    assert {
        "question",
        "expected_source",
        "expected_evidence",
        "expected_answer",
        "requires_expert",
        "acceptance_criteria",
    }.issubset(fields)


def test_validation_pipeline_stages_order() -> None:
    stages = [s.value for s in KnowledgeValidationStage]
    assert stages == [
        "knowledge_candidate",
        "human_review",
        "validation",
        "publication",
    ]


def test_citation_contract_invariant() -> None:
    incomplete = CitationContract(
        answer="",
        evidence=[],
        source="",
        confidence=KnowledgeConfidenceLevel.UNVERIFIED,
    )
    assert citation_contract_is_complete(incomplete) is False
    complete = CitationContract(
        answer="Ответ",
        evidence=[KnowledgeEvidenceRef(evidence_id="e1", source_uri="uri://x")],
        source="uri://x",
        confidence=KnowledgeConfidenceLevel.MEDIUM,
    )
    assert citation_contract_is_complete(complete) is True


def test_freshness_expired_and_deprecated() -> None:
    kid = uuid4()
    expired = evaluate_knowledge_freshness(
        knowledge_id=kid,
        status=KnowledgeGovernanceStatus.PUBLISHED,
        review_date=datetime(2020, 1, 1),
        next_review=datetime(2020, 2, 1),
        as_of=datetime(2026, 1, 1),
    )
    assert expired.expired is True
    assert expired.freshness == KnowledgeFreshnessState.EXPIRED

    deprecated = evaluate_knowledge_freshness(
        knowledge_id=kid,
        status=KnowledgeGovernanceStatus.DEPRECATED,
        review_date=datetime(2025, 1, 1),
        next_review=datetime(2027, 1, 1),
    )
    assert deprecated.deprecated is True
    assert deprecated.freshness == KnowledgeFreshnessState.DEPRECATED

    now = datetime.now()
    fresh = evaluate_knowledge_freshness(
        knowledge_id=kid,
        status=KnowledgeGovernanceStatus.PUBLISHED,
        review_date=now - timedelta(days=1),
        next_review=now + timedelta(days=30),
        as_of=now,
    )
    assert fresh.expired is False
    assert fresh.freshness == KnowledgeFreshnessState.FRESH


def test_legacy_status_mapping_complete() -> None:
    for status in KnowledgeGovernanceStatus:
        assert status.value in KNOWLEDGE_GOVERNANCE_TO_LEGACY_STATUS


def test_governance_manifest_contract_exists() -> None:
    fields = set(KnowledgeGovernanceManifest.model_fields.keys())
    assert "immutable_hash" in fields
    assert "knowledge_ids" in fields
    assert "policy_version" in fields


def test_no_vectordb_or_llm_client_in_governance_domain() -> None:
    text = (ROOT / "app/domain/knowledge_governance.py").read_text(encoding="utf-8").lower()
    for banned in ("pinecone", "chromadb", "faiss", "openai.", "litellm", "embedding"):
        assert banned not in text
    # Package must not exist as a VectorDB shim for this phase
    assert not (ROOT / "app/knowledge_governance_vectordb").exists()
    assert not (ROOT / "app/knowledge_runtime").exists()


def test_compliance_matrix_has_knowledge_governance_row() -> None:
    matrix = (
        ROOT / "docs/architecture/subsystem_compliance_matrix.md"
    ).read_text(encoding="utf-8")
    assert "Knowledge Governance" in matrix
