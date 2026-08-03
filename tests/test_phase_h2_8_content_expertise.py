"""Phase H2.8 — Content expertise, evidence & editorial quality."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.domain.content_domain_classifier import classify_content_domain
from app.schemas.contracts import (
    ContentClaim,
    ContentClaimAction,
    ContentClaimEvidenceState,
    ContentClaimType,
    ContentDomainClassification,
    ContentDomainCode,
    ContentDraftResult,
    ContentDraftReviewStatus,
    ContentFactualityMode,
    ContentQualityGateDecision,
    SpecialistSkillCode,
)
from app.services.content_claim_verification import (
    apply_claim_actions,
    cta_duplicated_in_body,
    verify_content_claims,
)
from app.services.content_editorial_review import run_editorial_review
from app.services.content_quality_gate import run_strict_quality_gate
from app.specialist_skills.registry import get_skill
from tests.kg2_helpers import publish_drilling_governed_knowledge

_OWNER_DRILLING_PROMPT = (
    "Напиши пост для Telegram о важности фиксации слабых сигналов до "
    "инцидента на буровой.\n"
    "Аудитория — буровые супервайзеры.\n"
    "Тон — профессиональный.\n"
    "Цель — вызвать обсуждение.\n"
    "В конце задай вопрос."
)

_TELEGRAM_INPUTS = {
    "topic": "фиксация слабых сигналов до инцидента на буровой",
    "audience": "буровые супервайзеры",
    "objective": "вызвать обсуждение",
    "tone": "профессиональный",
    "length": "standard",
    "CTA": "Как вы фиксируете слабые сигналы на смене?",
}


def _enable_content_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONTENT_DRAFT_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("CONTENT_DRAFT_LLM_PROVIDER", "mock")
    monkeypatch.setenv("CONTENT_DRAFT_LLM_MODEL", "mock-model")
    from app.core.config import get_settings

    get_settings.cache_clear()


def _sample_draft(**overrides: object) -> ContentDraftResult:
    base = dict(
        skill_code=SpecialistSkillCode.CONTENT_TELEGRAM_POST.value,
        hook="Слабые сигналы на буровой",
        body=(
            "На смене супервайзер замечает отклонение параметров: torque растёт, "
            "flow check показывает долив. Это не инцидент, но near-miss, который "
            "стоит зафиксировать до эскалации. Тренд по сменам помогает увидеть "
            "повторяющиеся наблюдения и вовремя передать информацию бригаде."
        ),
        cta="Как вы фиксируете слабые сигналы на смене?",
        variants=[],
        assumptions=[],
        factual_claims=[],
        warnings=[],
        knowledge_refs=["ms.domain.drilling.weak_signals@1.0"],
        generation_mode="real",
        review_status=ContentDraftReviewStatus.PENDING,
        status="draft",
    )
    base.update(overrides)
    return ContentDraftResult(**base)


# --------------------------------------------------------------------------
# Domain classification
# --------------------------------------------------------------------------


def test_domain_classifier_owner_drilling_prompt() -> None:
    domain = classify_content_domain(_OWNER_DRILLING_PROMPT)
    assert domain.primary == ContentDomainCode.DRILLING_OPERATIONS
    assert ContentDomainCode.INDUSTRIAL_SAFETY in domain.secondary
    assert "Буровые операции" in domain.labels


def test_domain_classifier_unknown_becomes_general_marketing() -> None:
    domain = classify_content_domain("Напиши короткий пост про скидки")
    assert domain.primary == ContentDomainCode.GENERAL_MARKETING


# --------------------------------------------------------------------------
# Internal skills registered (not user-facing routes)
# --------------------------------------------------------------------------


def test_internal_h28_skills_registered() -> None:
    claim = get_skill(SpecialistSkillCode.CONTENT_CLAIM_VERIFICATION)
    editorial = get_skill(SpecialistSkillCode.CONTENT_EDITORIAL_REVIEW)
    assert claim is not None
    assert editorial is not None
    assert claim.code == SpecialistSkillCode.CONTENT_CLAIM_VERIFICATION
    assert editorial.code == SpecialistSkillCode.CONTENT_EDITORIAL_REVIEW


# --------------------------------------------------------------------------
# Claim verification
# --------------------------------------------------------------------------


def test_unsupported_percentage_removed() -> None:
    draft = _sample_draft(
        body=(
            "На буровой 67% инцидентов можно предотвратить, если фиксировать слабые сигналы. "
            "Супервайзер отслеживает torque и flow check на смене."
        ),
        factual_claims=[],
    )
    claims, foundation, warnings = verify_content_claims(
        draft,
        factuality_mode=ContentFactualityMode.GENERAL_EXPERT,
        knowledge_refs=draft.knowledge_refs,
    )
    apply_claim_actions(draft, claims)
    assert any(c.action == ContentClaimAction.REMOVE for c in claims)
    assert "67%" not in draft.body
    assert foundation.softened_or_removed_claims
    assert warnings


def test_declared_advisory_claim_allowed() -> None:
    draft = _sample_draft(factual_claims=["Опыт смен показывает важность ранней фиксации"])
    claims, _, _ = verify_content_claims(
        draft,
        factuality_mode=ContentFactualityMode.GENERAL_EXPERT,
        knowledge_refs=draft.knowledge_refs,
    )
    advisory = [c for c in claims if c.claim_type == ContentClaimType.ADVISORY]
    assert advisory
    assert advisory[0].action in {ContentClaimAction.ALLOW, ContentClaimAction.MARK_ASSUMPTION}


# --------------------------------------------------------------------------
# Editorial review
# --------------------------------------------------------------------------


def test_duplicate_cta_detected() -> None:
    draft = _sample_draft(
        body="... текст заканчивается вопросом: Как вы фиксируете слабые сигналы на смене?",
        cta="Как вы фиксируете слабые сигналы на смене?",
    )
    assert cta_duplicated_in_body(draft)
    issues, _ = run_editorial_review(
        draft,
        domain=ContentDomainClassification(
            primary=ContentDomainCode.DRILLING_OPERATIONS,
            secondary=[],
            confidence=0.9,
            labels=["Буровые операции"],
        ),
        audience="буровые супервайзеры",
    )
    assert "duplicated_final_cta" in issues


def test_generic_filler_flagged() -> None:
    draft = _sample_draft(
        body=(
            "В современном мире важно понимать, что это не просто рекомендация. "
            "Короткий абзац без отраслевой конкретики."
        ),
        cta="Что думаете?",
    )
    issues, scores = run_editorial_review(
        draft,
        domain=ContentDomainClassification(
            primary=ContentDomainCode.GENERAL_MARKETING,
            secondary=[],
            confidence=0.5,
            labels=["Маркетинг"],
        ),
    )
    assert "generic_filler" in issues
    assert scores["originality"] < 0.7


# --------------------------------------------------------------------------
# Strict quality gate thresholds
# --------------------------------------------------------------------------


def test_quality_gate_pass_at_085() -> None:
    draft = _sample_draft()
    issues, scores = run_editorial_review(
        draft,
        domain=ContentDomainClassification(
            primary=ContentDomainCode.DRILLING_OPERATIONS,
            secondary=[],
            confidence=0.9,
            labels=["Буровые операции"],
        ),
        audience="буровые супервайзеры",
    )
    claims, _, _ = verify_content_claims(
        draft,
        factuality_mode=ContentFactualityMode.GENERAL_EXPERT,
        knowledge_refs=draft.knowledge_refs,
    )
    gate = run_strict_quality_gate(
        draft,
        editorial_issues=issues,
        editorial_scores=scores,
        claims=claims,
    )
    assert gate.score >= 0.85
    assert gate.gate_decision == ContentQualityGateDecision.PASS
    assert gate.passed is True


def test_quality_gate_block_below_070() -> None:
    draft = _sample_draft(
        hook="",
        body="",
        cta="",
    )
    issues, scores = run_editorial_review(draft, domain=None)
    scores.update(
        {
            "depth": 0.1,
            "originality": 0.1,
            "audience_fit": 0.1,
            "clarity": 0.1,
            "domain_depth": 0.1,
            "professional_credibility": 0.1,
            "repetition": 0.1,
            "cta_quality": 0.1,
            "structure": 0.1,
            "platform_fit": 0.1,
            "instruction_adherence": 0.1,
            "language_quality": 0.1,
        }
    )
    claims: list[ContentClaim] = []
    gate = run_strict_quality_gate(
        draft,
        editorial_issues=issues,
        editorial_scores=scores,
        claims=claims,
    )
    assert gate.score < 0.70
    assert gate.gate_decision == ContentQualityGateDecision.BLOCK
    assert gate.passed is False


def test_quality_gate_revise_band_with_fixable_cta() -> None:
    draft = _sample_draft(
        body=(
            "На смене супервайзер отслеживает torque, flow check и долив. "
            "Слабые сигналы фиксируются до эскалации. "
            "Тренд по сменам помогает видеть повторяющиеся наблюдения. "
            "Как вы фиксируете слабые сигналы на смене?"
        ),
        cta="Как вы фиксируете слабые сигналы на смене?",
    )
    issues, scores = run_editorial_review(
        draft,
        domain=ContentDomainClassification(
            primary=ContentDomainCode.DRILLING_OPERATIONS,
            secondary=[],
            confidence=0.9,
            labels=["Буровые операции"],
        ),
        audience="буровые супервайзеры",
    )
    claims, _, _ = verify_content_claims(
        draft,
        factuality_mode=ContentFactualityMode.GENERAL_EXPERT,
        knowledge_refs=draft.knowledge_refs,
    )
    gate = run_strict_quality_gate(
        draft,
        editorial_issues=issues,
        editorial_scores=scores,
        claims=claims,
    )
    assert gate.gate_decision in {
        ContentQualityGateDecision.REVISE,
        ContentQualityGateDecision.BLOCK,
    }
    assert "duplicated_final_cta" in gate.critical_failures


def test_unsupported_statistic_critical_failure() -> None:
    draft = _sample_draft(body="Риск снижается на 67% при фиксации сигналов на буровой.")
    claims = [
        ContentClaim(
            statement="67%",
            claim_type=ContentClaimType.FACTUAL,
            evidence_state=ContentClaimEvidenceState.UNSUPPORTED,
            confidence=0.0,
            action=ContentClaimAction.REMOVE,
        )
    ]
    gate = run_strict_quality_gate(
        draft,
        editorial_issues=["unsupported_exact_statistic"],
        editorial_scores={"depth": 0.5, "originality": 0.8},
        claims=claims,
    )
    assert "unsupported_exact_statistic" in gate.critical_failures
    assert gate.gate_decision != ContentQualityGateDecision.PASS


# --------------------------------------------------------------------------
# API integration — domain pack, foundation, bounded revision
# --------------------------------------------------------------------------


def test_owner_drilling_request_attaches_domain_and_foundation(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_content_draft(monkeypatch)
    publish_drilling_governed_knowledge(
        client, auth_headers, code="h28.drilling.weak_signals"
    )
    created = client.post(
        "/user-requests",
        headers=auth_headers,
        json={"text": _OWNER_DRILLING_PROMPT},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    domain = body["skill_inputs"].get("_domain") or {}
    assert domain.get("primary") == "drilling_operations"
    assert "Буровые операции" in (domain.get("labels") or [])
    assert body["skill_inputs"].get("_governed_snapshot") is True
    assert body["knowledge_snapshot_id"]

    draft = body["content_draft"]
    assert draft is not None
    assert draft.get("revision_count", 0) <= 1
    assert draft.get("text_foundation") is not None
    assert "Проверка утверждений" in draft.get("expertise_labels", [])
    assert draft["quality_check"].get("gate_decision") in {"pass", "revise", "block"}
    refs = draft.get("knowledge_refs") or []
    materials = draft.get("materials_used") or []
    assert (
        any(ref.startswith("kg:") for ref in refs)
        or any("ms.domain.drilling" in ref for ref in refs)
        or any("Отраслевые" in m for m in materials)
    )
    # Mock path keeps diagnostic status; real weak drafts surface needs-work copy.
    if draft["generation_mode"] == "mock":
        assert draft["status"] == "draft"
    elif draft["quality_check"]["gate_decision"] != "pass":
        assert "доработк" in (body["assistant_message"] or "").lower()
        assert draft["status"] == "blocked"


def test_cross_owner_cannot_read_draft(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_content_draft(monkeypatch)
    publish_drilling_governed_knowledge(
        client, auth_headers, code="h28.drilling.cross_owner"
    )
    created = client.post(
        "/user-requests",
        headers=auth_headers,
        json={"text": _OWNER_DRILLING_PROMPT, "skill_inputs": _TELEGRAM_INPUTS},
    ).json()
    denied = client.get(f"/user-requests/{created['id']}", headers=other_auth_headers)
    assert denied.status_code == 404


def test_no_workflow_automation_side_effects(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_content_draft(monkeypatch)
    publish_drilling_governed_knowledge(
        client, auth_headers, code="h28.drilling.no_automation"
    )
    created = client.post(
        "/user-requests",
        headers=auth_headers,
        json={"text": _OWNER_DRILLING_PROMPT},
    ).json()
    blob = str(created).lower()
    assert "n8n" not in blob
    assert "make.com" not in blob
    assert created["content_draft"] is not None
    assert created.get("generation_status") not in ("published", "publishing")
