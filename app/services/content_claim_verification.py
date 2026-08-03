"""Claim verification for content drafts (Phase H2.8 — internal skill)."""

from __future__ import annotations

import re

from app.schemas.contracts import (
    ContentClaim,
    ContentClaimAction,
    ContentClaimEvidenceState,
    ContentClaimType,
    ContentDraftResult,
    ContentFactualityMode,
    ContentTextFoundation,
)

_PERCENT_RE = re.compile(
    r"\b(\d{1,3}(?:[.,]\d+)?)\s*%|\bна\s+(\d{1,3}(?:[.,]\d+)?)\s*процент",
    re.I,
)
_STAT_RE = re.compile(
    r"\b(\d{1,3}(?:[.,]\d+)?)\s*(?:раз|крат|fold)\b|\bсниж\w+\s+на\s+\d+",
    re.I,
)


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _similar(a: str, b: str) -> bool:
    na, nb = _normalize(a), _normalize(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    if len(na) > 20 and len(nb) > 20 and (na in nb or nb in na):
        return True
    return False


def extract_claim_candidates(result: ContentDraftResult) -> list[str]:
    candidates: list[str] = []
    for declared in result.factual_claims:
        if declared.strip():
            candidates.append(declared.strip())
    blob = " ".join([result.hook, result.body, result.cta])
    for m in _PERCENT_RE.finditer(blob):
        candidates.append(m.group(0))
    for m in _STAT_RE.finditer(blob):
        candidates.append(m.group(0))
    return candidates


def verify_content_claims(
    result: ContentDraftResult,
    *,
    factuality_mode: ContentFactualityMode,
    knowledge_refs: list[str],
    user_material_refs: list[str] | None = None,
) -> tuple[list[ContentClaim], ContentTextFoundation, list[str]]:
    """Return claims, foundation updates, and warnings."""
    user_material_refs = user_material_refs or []
    claims: list[ContentClaim] = []
    softened: list[str] = []
    warnings: list[str] = []
    approved_set = set(knowledge_refs)

    for stmt in extract_claim_candidates(result):
        claim = ContentClaim(
            statement=stmt,
            claim_type=ContentClaimType.FACTUAL,
            evidence_state=ContentClaimEvidenceState.UNSUPPORTED,
            confidence=0.0,
            action=ContentClaimAction.ALLOW,
        )

        if _PERCENT_RE.search(stmt) or _STAT_RE.search(stmt):
            has_source = bool(claim.source_refs) or any(
                ref in approved_set for ref in claim.source_refs
            )
            if factuality_mode == ContentFactualityMode.USER_MATERIALS_ONLY:
                has_source = bool(user_material_refs)
            if not has_source:
                claim.evidence_state = ContentClaimEvidenceState.UNSUPPORTED
                claim.action = ContentClaimAction.REMOVE
                claim.confidence = 0.0
                softened.append(stmt)
                warnings.append(f"unsupported_statistic_removed:{stmt[:80]}")
            else:
                claim.evidence_state = ContentClaimEvidenceState.APPROVED_KNOWLEDGE
                claim.action = ContentClaimAction.ALLOW
                claim.confidence = 0.85
        elif stmt in result.factual_claims:
            claim.evidence_state = ContentClaimEvidenceState.INFERRED
            claim.action = ContentClaimAction.MARK_ASSUMPTION
            claim.claim_type = ContentClaimType.ADVISORY
            claim.confidence = 0.6
        else:
            claim.evidence_state = ContentClaimEvidenceState.INFERRED
            claim.action = ContentClaimAction.ALLOW
            claim.claim_type = ContentClaimType.ADVISORY
            claim.confidence = 0.7

        claims.append(claim)

    foundation = ContentTextFoundation(
        domain_items=list(knowledge_refs),
        user_materials=list(user_material_refs),
        softened_or_removed_claims=softened,
        assumptions=list(result.assumptions),
    )
    return claims, foundation, warnings


def apply_claim_actions(result: ContentDraftResult, claims: list[ContentClaim]) -> None:
    """Mutate draft text for removed/softened claims."""
    body = result.body
    cta = result.cta
    for claim in claims:
        if claim.action != ContentClaimAction.REMOVE:
            continue
        stmt = claim.statement
        if stmt in body:
            body = body.replace(stmt, "").strip()
        if stmt in cta:
            cta = cta.replace(stmt, "").strip()
        if _PERCENT_RE.search(stmt):
            body = _PERCENT_RE.sub("", body)
            cta = _PERCENT_RE.sub("", cta)
    result.body = re.sub(r"\s{2,}", " ", body).strip()
    result.cta = re.sub(r"\s{2,}", " ", cta).strip()
    if claims and any(c.action == ContentClaimAction.REMOVE for c in claims):
        result.warnings = list(dict.fromkeys([*result.warnings, "claims_softened_or_removed"]))


def has_unsupported_exact_statistic(claims: list[ContentClaim]) -> bool:
    return any(
        c.action == ContentClaimAction.REMOVE
        and (_PERCENT_RE.search(c.statement) or _STAT_RE.search(c.statement))
        for c in claims
    )


def cta_duplicated_in_body(result: ContentDraftResult) -> bool:
    if not result.cta or not result.body:
        return False
    if not result.cta.strip().endswith("?"):
        return False
    tail = result.body.strip()[-min(200, len(result.body)) :]
    return _similar(result.cta, tail) or result.cta.strip() in tail
