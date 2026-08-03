"""Repository for BIV fetch ledger entries."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.biv_fetch_ledger import BivFetchLedgerTable
from app.schemas.contracts import BivFetchLedgerEntry


class BivFetchLedgerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, row: BivFetchLedgerTable) -> BivFetchLedgerTable:
        self._session.add(row)
        await self._session.flush()
        return row

    async def list_for_run(self, run_id: UUID) -> list[BivFetchLedgerTable]:
        stmt = (
            select(BivFetchLedgerTable)
            .where(BivFetchLedgerTable.run_id == run_id)
            .order_by(BivFetchLedgerTable.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def to_contract(row: BivFetchLedgerTable) -> BivFetchLedgerEntry:
        from app.schemas.contracts import BivFetchOutcomeCode

        return BivFetchLedgerEntry(
            fetch_id=row.id,
            run_id=row.run_id,
            correlation_id=row.correlation_id,
            query_id=row.query_id,
            source_url=row.source_url,
            normalized_url=row.normalized_url,
            provider=row.provider,
            attempt_number=row.attempt_number,
            started_at=row.started_at,
            finished_at=row.finished_at,
            latency_ms=row.latency_ms,
            http_status=row.http_status,
            outcome_code=BivFetchOutcomeCode(row.outcome_code),
            content_type=row.content_type,
            content_length=row.content_length,
            retryable=row.retryable,
            fallback_used=row.fallback_used,
            error_class=row.error_class,
            safe_error_message=row.safe_error_message,
            raw_content_stored=row.raw_content_stored,
            extracted_text_length=row.extracted_text_length,
            created_at=row.created_at,
        )
