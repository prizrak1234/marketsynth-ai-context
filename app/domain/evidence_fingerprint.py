"""Evidence claim validation and fingerprint (Commercial MVP P0.4).

Evidence = atomic verifiable claim linked to Sources.
Not LLM response, supervisor finding, or Business Verdict.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any
from uuid import UUID

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_text
from app.schemas.contracts import (
    EvidenceAssessmentState,
    EvidenceConfidenceLevel,
    EvidenceSourceLinkInput,
    EvidenceSourceStance,
    EvidenceType,
)

_VERDICT_PATTERNS = (
    r"\bстоит запускать\b",
    r"\bshould launch\b",
    r"\bgo\b",
    r"\bno[_ -]?go\b",
    r"\bbusiness verdict\b",
    r"\bрекомендуем\b",
    r"\brecommend(ed|ation)?\b",
    r"\bпоэтому проект\b",
)

_MULTI_CLAIM_HINTS = (
    r";\s*",
    r"\.\s+[А-ЯA-Z]",
)


def normalize_claim(claim: str) -> str:
    return re.sub(r"\s+", " ", sanitize_text(claim).strip())


def validate_atomic_claim(claim: str, *, assessment_state: EvidenceAssessmentState) -> str:
    text = normalize_claim(claim)
    if len(text) < 8:
        raise InvalidStateError("non_atomic_claim")
    if len(text) > 2000:
        raise InvalidStateError("non_atomic_claim")
    lower = text.lower()
    for pat in _VERDICT_PATTERNS:
        if re.search(pat, lower, flags=re.IGNORECASE):
            raise InvalidStateError("non_atomic_claim")
    # Multiple distinct sentences tend to be non-atomic (allow for missing why notes separately)
    if assessment_state != EvidenceAssessmentState.MISSING:
        sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
        if len(sentences) > 2:
            raise InvalidStateError("non_atomic_claim")
        if " и поэтому " in lower or " therefore " in lower:
            raise InvalidStateError("non_atomic_claim")
    return text


def excerpt_hash(excerpt: str | None) -> str | None:
    if not excerpt:
        return None
    cleaned = sanitize_text(excerpt).strip()[:2000]
    if not cleaned:
        return None
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()


def compute_evidence_fingerprint(
    *,
    project_id: UUID,
    investigation_id: UUID,
    claim: str,
    evidence_type: EvidenceType,
    investigation_area: str,
    source_links: list[EvidenceSourceLinkInput],
) -> str:
    links = sorted(
        [
            {
                "source_id": str(link.source_id),
                "stance": link.stance.value,
                "locator_type": link.locator_type.value,
                "locator_value": (link.locator_value or "").strip() or None,
            }
            for link in source_links
        ],
        key=lambda item: (item["source_id"], item["stance"], item["locator_type"] or ""),
    )
    payload: dict[str, Any] = {
        "project_id": str(project_id),
        "investigation_id": str(investigation_id),
        "claim": normalize_claim(claim).lower(),
        "evidence_type": evidence_type.value,
        "investigation_area": investigation_area,
        "source_links": links,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_source_requirement(
    *,
    assessment_state: EvidenceAssessmentState,
    source_links: list[EvidenceSourceLinkInput],
) -> None:
    if assessment_state == EvidenceAssessmentState.MISSING:
        return
    if not source_links:
        raise InvalidStateError("missing_source")


def validate_accept_links(
    *,
    assessment_state: EvidenceAssessmentState,
    stances: list[EvidenceSourceStance],
) -> None:
    if assessment_state == EvidenceAssessmentState.MISSING:
        return
    if not any(
        s in (EvidenceSourceStance.SUPPORTS, EvidenceSourceStance.CONTRADICTS)
        for s in stances
    ):
        raise InvalidStateError("missing_source")


def verdict_readiness_contribution(
    *,
    missing_critical: int,
    conflicting_critical: int,
    outdated_critical: int,
    accepted_count: int,
) -> str:
    if missing_critical > 0 or conflicting_critical > 0:
        return "blocked"
    if accepted_count == 0 or outdated_critical > 0:
        return "partial"
    return "sufficient"
