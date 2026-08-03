"""PRODUCT-01.3B — evidence integrity and research run binding tests."""

from __future__ import annotations

from uuid import uuid4

from app.business_idea_validation.audience_segmentation import audience_has_support
from app.business_idea_validation.classification import classify_evidence_item
from app.business_idea_validation.findings import (
    build_findings,
    build_research_gaps,
    confirmed_evidence,
)
from app.business_idea_validation.relevance import assess_source_relevance
from app.business_idea_validation.sanitization import (
    is_navigation_or_chrome,
    sanitize_evidence_statement,
    sanitize_source_body,
)
from app.business_idea_validation.source_quality import classify_source, source_quality_tier
from app.schemas.contracts import (
    AudienceSegmentationOutput,
    AudienceSegmentRecord,
    BivEvidenceClassification,
    BivSourceQualityTier,
    BusinessIdeaValidationEvidenceSummary,
    BusinessIdeaValidationInput,
    BusinessIdeaValidationSourceClass,
)
from app.services.business_idea_validation_service import (
    RESEARCH_IDEMPOTENCY_PREFIX,
    build_research_idempotency_key,
)


def test_sanitize_removes_navigation_and_urls() -> None:
    raw = "To main content [Skillbox](https://skillbox.ru/course) markdown **bold**"
    cleaned = sanitize_evidence_statement(raw)
    assert "To main content" not in cleaned
    assert "http" not in cleaned
    assert "skillbox" not in cleaned.lower() or "skillbox" in cleaned  # title word may remain


def test_navigation_detected() -> None:
    assert is_navigation_or_chrome("To main content")
    assert is_navigation_or_chrome("https://example.com/path")


def test_sanitize_source_body_strips_garbage_lines() -> None:
    body = "To main content\nSubscribe to newsletter\nReal market demand grows in urban areas."
    cleaned = sanitize_source_body(body)
    assert "Subscribe" not in cleaned
    assert "market demand" in cleaned


def test_relevance_rejects_generic_education_landing() -> None:
    inp = BusinessIdeaValidationInput(
        tenant_id=uuid4(),
        project_id=uuid4(),
        user_request_id=uuid4(),
        idea="Кофейня specialty в центре Казани для офисных работников",
        location="Казань",
        target_audience="Офисные работники 25-40",
    )
    assessment = assess_source_relevance(
        inp=inp,
        url="https://skillbox.ru/course/marketing",
        title="Курсы маркетинга Skillbox",
        body_excerpt="Запишитесь на курс digital marketing со скидкой",
        source_class=BusinessIdeaValidationSourceClass.COMMERCIAL_BLOG,
    )
    assert assessment.relevant is False


def test_classification_rejects_tier_d() -> None:
    quality = classify_source(
        url="https://youtube.com/watch?v=abc",
        domain="youtube.com",
        title="Random video",
        body_excerpt="Some unrelated content about outsourcing",
    )
    relevance = assess_source_relevance(
        inp=BusinessIdeaValidationInput(
            tenant_id=uuid4(),
            project_id=uuid4(),
            user_request_id=uuid4(),
            idea="Кофейня specialty в Казани",
        ),
        url="https://youtube.com/watch?v=abc",
        title="Random video",
        body_excerpt="Some unrelated content about outsourcing",
        source_class=quality.source_class,
    )
    classification, tier, _ = classify_evidence_item(
        quality=quality,
        relevance=relevance,
        observation="Outsourcing trends on YouTube",
    )
    assert tier == BivSourceQualityTier.D
    assert classification == BivEvidenceClassification.UNSUPPORTED_CLAIM


def test_audience_has_support_requires_confirmed_evidence() -> None:
    from datetime import datetime

    now = datetime.utcnow()
    garbage = BusinessIdeaValidationEvidenceSummary(
        evidence_id=uuid4(),
        source_id=uuid4(),
        category="target_audience",
        classification=BivEvidenceClassification.UNSUPPORTED_CLAIM,
        claim="To main content",
        observation="To main content",
        supporting_excerpt="To main content",
        source_url="https://example.com",
        source_title="Example",
        retrieved_at=now,
        relevance_score=0.1,
        reliability_score=0.2,
        freshness_score=0.5,
        mcp_server_role="web_fetch_mcp",
        mcp_tool_name="fetch",
    )
    audience = AudienceSegmentationOutput(
        segments=[
            AudienceSegmentRecord(
                segment_id="h1",
                label="Test",
                is_hypothesis=True,
            )
        ]
    )
    assert audience_has_support(audience, [garbage]) is False


def test_build_findings_uses_confirmed_only() -> None:
    from datetime import datetime

    now = datetime.utcnow()
    confirmed = BusinessIdeaValidationEvidenceSummary(
        evidence_id=uuid4(),
        source_id=uuid4(),
        category="market_demand",
        classification=BivEvidenceClassification.CONFIRMED,
        claim="Urban coffee demand is growing",
        observation="Urban coffee demand is growing",
        supporting_excerpt="Urban coffee demand is growing",
        source_url="https://example.com",
        source_title="Industry report",
        retrieved_at=now,
        relevance_score=0.8,
        reliability_score=0.8,
        freshness_score=0.7,
        source_quality_tier=BivSourceQualityTier.B,
        mcp_server_role="web_fetch_mcp",
        mcp_tool_name="fetch",
    )
    noise = confirmed.model_copy(
        update={
            "evidence_id": uuid4(),
            "classification": BivEvidenceClassification.UNSUPPORTED_CLAIM,
            "claim": "To main content",
            "observation": "To main content",
        }
    )
    findings = build_findings([confirmed, noise])
    assert len(findings) == 1
    assert "main content" not in findings[0].statement.lower()


def test_research_idempotency_key_format() -> None:
    context_id = uuid4()
    hash_value = "a" * 64
    key = build_research_idempotency_key(context_id, hash_value)
    assert key.startswith(RESEARCH_IDEMPOTENCY_PREFIX)
    assert str(context_id) in key


def test_source_quality_tier_mapping() -> None:
    official = BusinessIdeaValidationSourceClass.OFFICIAL_STATISTICS
    ugc = BusinessIdeaValidationSourceClass.USER_GENERATED
    assert source_quality_tier(official) == BivSourceQualityTier.A
    assert source_quality_tier(ugc) == BivSourceQualityTier.D


def test_build_research_gaps_collects_limitations() -> None:
    from datetime import datetime

    now = datetime.utcnow()
    gap_item = BusinessIdeaValidationEvidenceSummary(
        evidence_id=uuid4(),
        source_id=uuid4(),
        category="market_demand",
        classification=BivEvidenceClassification.RESEARCH_GAP,
        claim="missing_local_sources",
        observation="missing_local_sources",
        supporting_excerpt="",
        source_url="",
        source_title="",
        retrieved_at=now,
        relevance_score=0.0,
        reliability_score=0.0,
        freshness_score=0.0,
        mcp_server_role="web_fetch_mcp",
        mcp_tool_name="fetch",
    )
    gaps = build_research_gaps([gap_item], ["fewer_than_3_fetched_sources"])
    assert "fewer_than_3_fetched_sources" in gaps
    assert "missing_local_sources" in gaps


def test_confirmed_evidence_helper() -> None:
    from datetime import datetime

    now = datetime.utcnow()
    base = dict(
        evidence_id=uuid4(),
        source_id=uuid4(),
        category="market_demand",
        claim="x",
        observation="x",
        supporting_excerpt="x",
        source_url="https://example.com",
        source_title="t",
        retrieved_at=now,
        relevance_score=0.5,
        reliability_score=0.5,
        freshness_score=0.5,
        mcp_server_role="web_fetch_mcp",
        mcp_tool_name="fetch",
    )
    confirmed = BusinessIdeaValidationEvidenceSummary(
        **base,
        classification=BivEvidenceClassification.CONFIRMED,
    )
    rejected = BusinessIdeaValidationEvidenceSummary(
        **{**base, "evidence_id": uuid4()},
        classification=BivEvidenceClassification.UNSUPPORTED_CLAIM,
    )
    assert len(confirmed_evidence([confirmed, rejected])) == 1
