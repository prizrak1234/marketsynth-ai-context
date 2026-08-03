#!/usr/bin/env python3
"""Seed one owner-accepted neutral image asset for VS.2A paid smoke (local only)."""

from __future__ import annotations

import asyncio
import shutil
from uuid import uuid4

from app.core.config import get_settings
from app.db.base import utc_now
from app.db.models.generated_visual_asset import GeneratedVisualAssetTable
from app.db.models.user import UserTable
from app.db.models.user_request import UserRequestTable
from app.db.session import close_db, get_session_factory, init_db
from app.media_generation.signed_asset_urls import resolve_capability_proof_path
from app.schemas.contracts import (
    GeneratedVisualAssetStatus,
    GeneratedVisualAssetType,
    GeneratedVisualGenerationMode,
    UserRequestStatus,
    UserRole,
)
from sqlalchemy import select


async def main() -> None:
    settings = get_settings()
    await init_db(settings)
    proof = resolve_capability_proof_path(settings, "smoke_keyframe_road_static.png")
    factory = get_session_factory()
    async with factory() as session:
        owner = (
            await session.execute(
                select(UserTable).where(UserTable.role == UserRole.OWNER).limit(1)
            )
        ).scalar_one_or_none()
        if owner is None:
            raise SystemExit("No owner user found — create/login an owner first.")

        asset_id = uuid4()
        storage_dir = settings.image_generation_storage_dir
        if not storage_dir.startswith("/") and storage_dir[1:3] != ":\\":
            from pathlib import Path

            storage_dir = str((Path(__file__).resolve().parents[1] / storage_dir).resolve())
        dest = f"{storage_dir}/{asset_id}.png"
        shutil.copy2(proof, dest)

        ur = UserRequestTable(
            owner_id=owner.id,
            text="VS.2A smoke neutral road keyframe",
            normalized_text="VS.2A smoke neutral road keyframe",
            status=UserRequestStatus.COMPLETED,
        )
        session.add(ur)
        await session.flush()
        session.add(
            GeneratedVisualAssetTable(
                id=asset_id,
                owner_id=owner.id,
                user_request_id=ur.id,
                skill_code="design.image_generation",
                skill_version="1.0",
                provider="local_seed",
                generation_mode=GeneratedVisualGenerationMode.MOCK,
                asset_type=GeneratedVisualAssetType.USER_RESULT,
                prompt_summary="Neutral road landscape — VS.2A smoke source (no faces)",
                mime_type="image/png",
                content_path=dest,
                storage_uri=f"/generated-visual-assets/{asset_id}/content",
                status=GeneratedVisualAssetStatus.SUCCEEDED,
                user_accepted=True,
                review_notes="vs2a_smoke_neutral_accepted",
                created_at=utc_now(),
            )
        )
        await session.commit()
        print(f"VS.2A smoke source asset_id={asset_id} owner_id={owner.id}")

    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
