"""PRODUCT-01.3A.3 — specificity gate UX (Variant B minimum blocking set)."""

from __future__ import annotations

import pytest
from app.business_idea_validation.analysis_context_gate import (
    BLOCKING_FIELDS,
    evaluate_specificity,
    is_specificity_sufficient,
)
from tests.test_product_01_3a_biv_intake_gate import _valid_fields


def _minimal_valid_fields(**overrides):
    base = _valid_fields(
        product_or_service="Онлайн-школа английского",
        target_customer="Взрослые 25–45",
        geography="Россия, онлайн",
        analysis_goal="Проверить спрос перед запуском",
    )
    data = base.model_dump()
    data.update(overrides)
    from app.schemas.contracts import AnalysisContextFields

    return AnalysisContextFields(**data)


def test_minimal_valid_context_has_no_missing_fields() -> None:
    fields = _minimal_valid_fields()
    missing, warnings = evaluate_specificity(fields)
    assert missing == []
    assert is_specificity_sufficient(fields)


def test_missing_required_field_lists_exact_keys() -> None:
    fields = _minimal_valid_fields(analysis_goal="")
    missing, _ = evaluate_specificity(fields)
    assert missing == ["analysis_goal"]


def test_multiple_missing_fields_exact_list() -> None:
    fields = _minimal_valid_fields(
        product_or_service="",
        idea_description="x",
        target_customer="",
        geography="",
        analysis_goal="",
    )
    missing, _ = evaluate_specificity(fields)
    assert set(missing) == {
        "idea_description",
        "product_or_service",
        "target_customer",
        "geography",
        "analysis_goal",
    }


def test_pricing_and_competitors_unknown_do_not_block() -> None:
    fields = _minimal_valid_fields(
        pricing_or_revenue_model="неизвестно",
        known_competitors="неизвестно",
        current_stage="",
        budget_context="",
    )
    missing, warnings = evaluate_specificity(fields)
    assert missing == []
    assert is_specificity_sufficient(fields)
    assert "research_gap_pricing_or_revenue_model" in warnings
    assert "research_gap_known_competitors" in warnings
    assert "research_gap_current_stage" in warnings
    assert "research_gap_budget_context" in warnings


def test_blocking_fields_constant_matches_gate() -> None:
    from app.schemas.contracts import AnalysisContextFields

    for key in BLOCKING_FIELDS:
        data = _minimal_valid_fields().model_dump()
        if key == "product_or_service":
            data["idea_description"] = "x"
            data["product_or_service"] = ""
        elif key == "target_customer":
            data["target_customer"] = ""
            data["target_customer_unknown"] = False
        elif key == "geography":
            data["geography"] = ""
            data["geography_unknown"] = False
        else:
            data[key] = ""
        probe = AnalysisContextFields(**data)
        missing, _ = evaluate_specificity(probe)
        assert key in missing


@pytest.mark.asyncio
async def test_confirm_minimal_valid_context(db_session) -> None:
    from app.core.config import get_settings
    from app.schemas.contracts import (
        AnalysisContextConfirmRequest,
        AnalysisContextCreateDraftRequest,
    )
    from app.services.analysis_context_service import AnalysisContextService
    from tests.conftest import _create_user_with_api_key
    from tests.test_product_01_3a_biv_intake_gate import _seed_project_db

    _key, user = await _create_user_with_api_key()
    project = await _seed_project_db(db_session, user.id)
    svc = AnalysisContextService(db_session, get_settings())
    draft = await svc.create_draft(
        user.id,
        project.id,
        AnalysisContextCreateDraftRequest(**_minimal_valid_fields().model_dump()),
    )
    assert draft.missing_fields == []
    confirmed = await svc.confirm(
        user.id,
        project.id,
        draft.context_id,
        AnalysisContextConfirmRequest(),
    )
    assert confirmed.confirmed_by_user is True
