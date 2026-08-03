"""KG.2 — Citation enforcement for citation_required skills (no LLM)."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.db.models.knowledge_governance import CitationRecordTable, KnowledgeAuditEventTable
from app.domain.knowledge_governance import citation_contract_is_complete
from app.schemas.contracts import CitationContract, KnowledgeConfidenceLevel


class CitationGateError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


CITATION_REQUIRED_SKILLS = frozenset(
    {
        "research.market_overview",
        "research.competitor_analysis",
        "research.audience_segmentation",
        "strategy.positioning",
        "strategy.offer_design",
        "content.telegram_post",  # industrial/expert content when pack requires
    }
)


def skill_requires_citations(skill_code: str, *, citation_flag: bool = False) -> bool:
    if citation_flag:
        return True
    return (skill_code or "") in CITATION_REQUIRED_SKILLS


async def enforce_and_persist_citations(
    session: AsyncSession,
    *,
    tenant_owner_id: UUID,
    user_request_id: UUID | None,
    snapshot_id: UUID | None,
    skill_code: str,
    claims: list[dict],
    citation_required: bool = True,
) -> list[CitationRecordTable]:
    """
    Persist CitationRecords. If citation_required and any claim missing source → block.
    claims items: claim_id, claim_text, knowledge_version_id?, semantic_chunk_id?, source_id?, confidence?
    """
    if not skill_requires_citations(skill_code, citation_flag=citation_required):
        return []

    if not claims:
        session.add(
            KnowledgeAuditEventTable(
                id=uuid4(),
                tenant_owner_id=tenant_owner_id,
                event_type="knowledge.citation_failed",
                actor_user_id=tenant_owner_id,
                payload={"reason": "no_claims", "skill_code": skill_code},
                created_at=utc_now(),
            )
        )
        await session.commit()
        raise CitationGateError(
            "citation_required",
            "Для навыка требуются citations, но утверждения не переданы.",
        )

    records: list[CitationRecordTable] = []
    blocked = False
    for claim in claims:
        source_id = (claim.get("source_id") or "").strip()
        version_id = claim.get("knowledge_version_id")
        conf = claim.get("confidence") or "unverified"
        status = "present"
        if not source_id and not version_id:
            status = "missing"
            blocked = True
        try:
            conf_enum = KnowledgeConfidenceLevel(str(conf))
        except ValueError:
            conf_enum = KnowledgeConfidenceLevel.UNVERIFIED
        contract = CitationContract(
            answer=str(claim.get("claim_text") or ""),
            evidence=[],
            source=source_id or str(version_id or ""),
            confidence=conf_enum,
        )
        if not citation_contract_is_complete(
            {
                "answer": contract.answer,
                "evidence": [{"evidence_id": "e"}] if source_id or version_id else [],
                "source": contract.source,
                "confidence": contract.confidence,
            }
        ):
            status = "missing"
            blocked = True

        rec = CitationRecordTable(
            id=uuid4(),
            tenant_owner_id=tenant_owner_id,
            user_request_id=user_request_id,
            snapshot_id=snapshot_id,
            claim_id=str(claim.get("claim_id") or uuid4())[:64],
            claim_text=str(claim.get("claim_text") or "")[:8000],
            knowledge_version_id=UUID(str(version_id)) if version_id else None,
            semantic_chunk_id=UUID(str(claim["semantic_chunk_id"]))
            if claim.get("semantic_chunk_id")
            else None,
            source_id=source_id or None,
            confidence=str(conf)[:32],
            citation_status=status,
            created_at=utc_now(),
        )
        session.add(rec)
        records.append(rec)

    if blocked:
        session.add(
            KnowledgeAuditEventTable(
                id=uuid4(),
                tenant_owner_id=tenant_owner_id,
                event_type="knowledge.citation_failed",
                actor_user_id=tenant_owner_id,
                payload={"skill_code": skill_code, "missing": True},
                created_at=utc_now(),
            )
        )
        await session.commit()
        raise CitationGateError(
            "citation_missing",
            "Утверждение без источника — Quality Gate blocked.",
        )

    await session.commit()
    return records
