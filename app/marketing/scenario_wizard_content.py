"""Wizard-only content asset conversion for non-copywriter scenarios (Phase AI.138)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_text
from app.db.repositories.content_assets import ContentAssetRepository
from app.marketing.contracts import ContentAssetStatus, ContentAssetType, ContentAssetVersionSource
from app.marketing.copywriter_asset_conversion import (
    assert_copywriter_output_eligible,
    build_content_asset_fields_from_copywriter,
)
from app.schemas.contracts import MarketingSpecialistType
from app.services.content_asset_service import ContentAssetService

_MAX_BODY = 8000
_MAX_TITLE = 512
_SALES_COPY_OUTPUT_TYPE = "sales_copy"


def build_content_asset_fields_from_sales_copy(
    *,
    title: str,
    content: str,
    structured_data: dict[str, Any] | None,
) -> dict[str, Any]:
    structured = structured_data or {}
    headline = sanitize_text(str(structured.get("headline", ""))).strip()
    asset_title = sanitize_text(title).strip() or headline or "Sales copy"
    asset_title = asset_title[:_MAX_TITLE]
    body = sanitize_text(content).strip()[:_MAX_BODY]
    metadata = {
        "conversion_source": "scenario_wizard_sales_copy",
        "headline": headline[:500] if headline else None,
        "cta": sanitize_text(str(structured.get("cta", ""))).strip()[:500] or None,
    }
    return {
        "asset_type": ContentAssetType.TELEGRAM_POST,
        "title": asset_title,
        "body": body,
        "metadata": {key: value for key, value in metadata.items() if value},
    }


async def create_content_asset_from_wizard_output(
    session: AsyncSession,
    owner_id: UUID,
    project_id: UUID,
    *,
    output_id: UUID,
    specialist: MarketingSpecialistType,
    status: str,
    output_type: str,
    title: str,
    content: str,
    structured_data: dict[str, Any] | None,
    marketing_plan_id: UUID | None,
    execution_run_id: UUID,
    wizard_run_id: UUID,
):
    assets = ContentAssetRepository(session)
    existing = await assets.get_by_source_specialist_output_id(owner_id, project_id, output_id)
    if existing is not None:
        return existing

    if specialist == MarketingSpecialistType.COPYWRITER:
        assert_copywriter_output_eligible(
            specialist=specialist,
            status=status,
            output_type=output_type,
        )
        fields = build_content_asset_fields_from_copywriter(
            title=title,
            content=content,
            structured_data=structured_data,
        )
        source_specialist_type = MarketingSpecialistType.COPYWRITER.value
    elif specialist == MarketingSpecialistType.SALES_COPYWRITER:
        if status != "approved":
            raise InvalidStateError(
                "Sales copywriter output must be approved before creating a content asset",
            )
        if output_type != _SALES_COPY_OUTPUT_TYPE:
            raise InvalidStateError("Specialist output is not a sales_copy package")
        fields = build_content_asset_fields_from_sales_copy(
            title=title,
            content=content,
            structured_data=structured_data,
        )
        source_specialist_type = MarketingSpecialistType.SALES_COPYWRITER.value
    else:
        raise InvalidStateError(
            "Wizard content asset requires copywriter or sales_copywriter output",
        )

    metadata = dict(fields["metadata"])
    metadata["wizard_run_id"] = str(wizard_run_id)

    created = await ContentAssetService(session).create(
        owner_id,
        project_id,
        asset_type=fields["asset_type"],
        title=fields["title"],
        body=fields["body"],
        metadata=metadata,
        status=ContentAssetStatus.DRAFT,
        source_marketing_plan_id=marketing_plan_id,
        source_execution_run_id=execution_run_id,
        source_specialist_output_id=output_id,
        source_specialist_type=source_specialist_type,
        created_by_source=ContentAssetVersionSource.HTTP_API,
    )
    if created is None:
        raise InvalidStateError("Failed to create content asset from wizard output")
    return created
