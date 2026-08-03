#!/usr/bin/env python3
"""Dev-only: inspect and optionally purge E2E user_requests for chat golden path."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, func, select

from app.core.config import get_settings
from app.db.models.user import UserTable
from app.db.models.user_request import UserRequestTable
from app.db.session import get_session_factory, init_db, reset_db_state


async def _resolve_owner(session, email: str) -> UUID:
    result = await session.execute(select(UserTable).where(UserTable.email == email.lower()))
    user = result.scalar_one_or_none()
    if user is None:
        raise SystemExit(f"user_not_found={email}")
    return user.id


async def _inspect(owner_id: UUID) -> dict:
    factory = get_session_factory()
    async with factory() as session:
        total = await session.scalar(
            select(func.count()).select_from(UserRequestTable).where(
                UserRequestTable.owner_id == owner_id,
            ),
        )
        rows = await session.execute(
            select(UserRequestTable)
            .where(UserRequestTable.owner_id == owner_id)
            .order_by(UserRequestTable.created_at.asc()),
        )
        items = list(rows.scalars().all())
        text_counts = Counter(r.normalized_text for r in items)
        dup_texts = {t: c for t, c in text_counts.items() if c > 1}
        null_chat_route = sum(1 for r in items if r.chat_route is None)
        null_idem = sum(1 for r in items if r.idempotency_key is None)
        by_text: dict[str, list[str]] = defaultdict(list)
        for row in items:
            by_text[row.normalized_text[:80]].append(str(row.id))
        return {
            "total_rows": int(total or 0),
            "duplicate_text_groups": len(dup_texts),
            "duplicate_text_samples": [
                {"text": k[:80], "count": v} for k, v in list(dup_texts.items())[:10]
            ],
            "null_chat_route_rows": null_chat_route,
            "null_idempotency_rows": null_idem,
            "row_ids_by_text_sample": {
                k: v[:5] for k, v in list(by_text.items())[:5]
            },
        }


async def _purge(owner_id: UUID) -> int:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            delete(UserRequestTable).where(UserRequestTable.owner_id == owner_id),
        )
        await session.commit()
        return int(result.rowcount or 0)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default="chat-golden-path-dev@marketsynth.test")
    parser.add_argument("--purge", action="store_true", help="Delete all user_requests for E2E user")
    parser.add_argument(
        "--snapshot-dir",
        default="artifacts/chat-golden-path/repair",
    )
    args = parser.parse_args()

    reset_db_state()
    await init_db(get_settings())
    factory = get_session_factory()
    async with factory() as session:
        owner_id = await _resolve_owner(session, args.email)

    report = await _inspect(owner_id)
    print(json.dumps(report, ensure_ascii=False, indent=2))

    snap_dir = Path(args.snapshot_dir)
    snap_dir.mkdir(parents=True, exist_ok=True)
    snap_path = snap_dir / f"snapshot-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    snap_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"snapshot={snap_path}")

    if args.purge:
        deleted = await _purge(owner_id)
        print(f"purged_rows={deleted}")


if __name__ == "__main__":
    asyncio.run(main())
