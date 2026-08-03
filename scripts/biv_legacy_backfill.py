"""Batch backfill legacy BIV runs with commercial contracts (CWF.1 stabilization)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.business_idea_validation.output_enrichment import enrich_output_commercial
from app.core.config import get_settings
from app.db.models.business_idea_validation_run import BusinessIdeaValidationRunTable
from app.db.session import get_session_factory, init_db, reset_db_state
from app.schemas.contracts import BusinessIdeaValidationOutput, BusinessIdeaValidationRunStatus


def _log(msg: str) -> None:
    ts = datetime.now(UTC).isoformat()
    print(f"[{ts}] {msg}", flush=True)


async def _run(args: argparse.Namespace) -> int:
    settings = get_settings()
    if settings.app_env == "production" and not args.allow_production:
        print("Refusing backfill in production without --allow-production", file=sys.stderr)
        return 2

    reset_db_state()
    await init_db(settings)
    factory = get_session_factory()

    migrated = 0
    skipped = 0
    failed = 0
    last_id: UUID | None = args.resume_after

    async with factory() as session:
        while True:
            stmt = (
                select(BusinessIdeaValidationRunTable)
                .where(
                    BusinessIdeaValidationRunTable.status
                    == BusinessIdeaValidationRunStatus.SUCCEEDED,
                )
                .order_by(BusinessIdeaValidationRunTable.created_at.asc())
                .limit(args.batch_size)
            )
            if last_id is not None:
                stmt = stmt.where(BusinessIdeaValidationRunTable.id > last_id)
            result = await session.execute(stmt)
            rows = list(result.scalars().all())
            if not rows:
                break

            for row in rows:
                last_id = row.id
                if not row.result_json:
                    skipped += 1
                    _log(f"skip run_id={row.id} reason=no_result_json")
                    continue
                try:
                    output = BusinessIdeaValidationOutput.model_validate(row.result_json)
                    needs = (
                        output.customer_report is None
                        or output.commercial_verdict is None
                        or not output.evidence_items
                    )
                    if not needs:
                        skipped += 1
                        continue

                    snapshot = row.result_json.copy()
                    enriched = enrich_output_commercial(output)
                    if args.dry_run:
                        _log(f"dry-run would_migrate run_id={row.id}")
                        migrated += 1
                        continue

                    row.result_json = enriched.model_dump(mode="json")
                    row.result_json["_backfill_snapshot"] = snapshot
                    row.updated_at = datetime.now(UTC)
                    session.add(row)
                    await session.flush()
                    migrated += 1
                    _log(f"migrated run_id={row.id}")
                except Exception as exc:  # noqa: BLE001
                    failed += 1
                    _log(f"failed run_id={row.id} error={exc!s}")

            if not args.dry_run:
                await session.commit()

            if len(rows) < args.batch_size:
                break

    summary = {
        "migrated": migrated,
        "skipped": skipped,
        "failed": failed,
        "dry_run": args.dry_run,
        "resume_after": str(last_id) if last_id else None,
    }
    _log(f"summary {json.dumps(summary)}")
    return 1 if failed else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="BIV legacy batch backfill")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--resume-after", type=UUID, default=None)
    parser.add_argument("--allow-production", action="store_true")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
