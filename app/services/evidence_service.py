"""Evidence service (Commercial MVP P0.4).

Atomic claims linked to exact Source versions.
No Business Verdict, Agent Run, LLM, or Source fetch.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_text
from app.db.base import utc_now
from app.db.models.evidence import EvidenceSourceLinkTable, InvestigationEvidenceTable
from app.db.repositories.evidence import EvidenceRepository, EvidenceSourceLinkRepository
from app.db.repositories.investigations import InvestigationRepository
from app.db.repositories.sources import (
    InvestigationSourceLinkRepository,
    SourceRepository,
)
from app.domain.evidence_fingerprint import (
    compute_evidence_fingerprint,
    excerpt_hash,
    validate_accept_links,
    validate_atomic_claim,
    validate_source_requirement,
    verdict_readiness_contribution,
)
from app.schemas.contracts import (
    EvidenceAssessmentState,
    EvidenceConfidenceLevel,
    EvidenceCreateRequest,
    EvidenceInvestigationArea,
    EvidenceLifecycleStatus,
    EvidenceLocatorType,
    EvidenceMateriality,
    EvidencePreparedByType,
    EvidenceReviewNoteRequest,
    EvidenceSourceLinkInput,
    EvidenceSourceStance,
    EvidenceSummary,
    EvidenceSupersedeRequest,
    EvidenceType,
    EvidenceUpdateRequest,
    SourceStatus,
)
from app.services.projects_service import ProjectService
from app.services.transaction import transactional

_LIFECYCLE: dict[EvidenceLifecycleStatus, frozenset[EvidenceLifecycleStatus]] = {
    EvidenceLifecycleStatus.DRAFT: frozenset(
        {
            EvidenceLifecycleStatus.UNDER_REVIEW,
            EvidenceLifecycleStatus.ARCHIVED,
            EvidenceLifecycleStatus.REJECTED,
        }
    ),
    EvidenceLifecycleStatus.UNDER_REVIEW: frozenset(
        {
            EvidenceLifecycleStatus.DRAFT,
            EvidenceLifecycleStatus.ACCEPTED,
            EvidenceLifecycleStatus.REJECTED,
            EvidenceLifecycleStatus.ARCHIVED,
        }
    ),
    EvidenceLifecycleStatus.ACCEPTED: frozenset(
        {
            EvidenceLifecycleStatus.SUPERSEDED,
            EvidenceLifecycleStatus.ARCHIVED,
        }
    ),
    EvidenceLifecycleStatus.REJECTED: frozenset(
        {
            EvidenceLifecycleStatus.SUPERSEDED,
            EvidenceLifecycleStatus.ARCHIVED,
        }
    ),
    EvidenceLifecycleStatus.SUPERSEDED: frozenset(),
    EvidenceLifecycleStatus.ARCHIVED: frozenset(),
}


class EvidenceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._evidence = EvidenceRepository(session)
        self._links = EvidenceSourceLinkRepository(session)
        self._investigations = InvestigationRepository(session)
        self._sources = SourceRepository(session)
        self._inv_source_links = InvestigationSourceLinkRepository(session)
        self._projects = ProjectService(session)

    async def _ensure_project(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    async def _ensure_investigation(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
    ):
        return await self._investigations.get_by_id_for_owner(
            investigation_id,
            owner_id,
            project_id,
        )

    async def _assert_source_usable(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        source_id: UUID,
    ) -> None:
        source = await self._sources.get_by_id_for_owner(source_id, owner_id, project_id)
        if source is None:
            raise InvalidStateError("source_not_found")
        if source.project_id != project_id:
            raise InvalidStateError("cross_project_source")
        if source.status in (
            SourceStatus.ARCHIVED,
            SourceStatus.REJECTED,
            SourceStatus.SUPERSEDED,
        ):
            raise InvalidStateError("source_not_available")
        attached = await self._inv_source_links.get_link(
            owner_id,
            project_id,
            investigation_id,
            source_id,
        )
        if attached is None and not source.reusable_within_project:
            raise InvalidStateError("source_not_available")

    async def _replace_links(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        evidence_id: UUID,
        source_links: list[EvidenceSourceLinkInput],
    ) -> list[EvidenceSourceLinkTable]:
        await self._links.delete_for_evidence(evidence_id)
        await self._session.flush()
        created: list[EvidenceSourceLinkTable] = []
        for item in source_links:
            await self._assert_source_usable(
                owner_id,
                project_id,
                investigation_id,
                item.source_id,
            )
            excerpt = sanitize_text(item.excerpt).strip()[:2000] if item.excerpt else None
            row = EvidenceSourceLinkTable(
                owner_id=owner_id,
                project_id=project_id,
                investigation_id=investigation_id,
                evidence_id=evidence_id,
                source_id=item.source_id,
                stance=item.stance,
                locator_type=item.locator_type,
                locator_value=(
                    sanitize_text(item.locator_value).strip()[:500]
                    if item.locator_value
                    else None
                ),
                excerpt=excerpt,
                excerpt_hash=excerpt_hash(excerpt),
                note=sanitize_text(item.note).strip()[:2000] if item.note else None,
                added_by=owner_id,
            )
            created.append(await self._links.create(row))
        return created

    def _audit(
        self,
        row: InvestigationEvidenceTable,
        *,
        action: str,
        previous: str,
        new: str,
        note: str | None,
        reviewer: UUID,
    ) -> None:
        meta = dict(row.metadata_json or {})
        events = list(meta.get("review_events") or [])
        if not isinstance(events, list):
            events = []
        events.append(
            {
                "action": action,
                "previous": previous,
                "new": new,
                "note": sanitize_text(note or "").strip()[:500],
                "reviewer": str(reviewer),
                "at": utc_now().isoformat(),
            }
        )
        meta["review_events"] = events[-50:]
        meta["creates_business_verdict"] = False
        meta["creates_agent_run"] = False
        row.metadata_json = meta

    async def create(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        request: EvidenceCreateRequest,
    ) -> InvestigationEvidenceTable | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        if await self._ensure_investigation(owner_id, project_id, investigation_id) is None:
            return None

        claim = validate_atomic_claim(
            request.claim,
            assessment_state=request.assessment_state,
        )
        validate_source_requirement(
            assessment_state=request.assessment_state,
            source_links=request.source_links,
        )
        fingerprint = compute_evidence_fingerprint(
            project_id=project_id,
            investigation_id=investigation_id,
            claim=claim,
            evidence_type=request.evidence_type,
            investigation_area=request.investigation_area.value,
            source_links=request.source_links,
        )
        dup = await self._evidence.find_live_by_fingerprint(
            owner_id,
            project_id,
            investigation_id,
            fingerprint,
        )
        if dup is not None:
            raise InvalidStateError("duplicate_evidence")

        row = InvestigationEvidenceTable(
            owner_id=owner_id,
            project_id=project_id,
            investigation_id=investigation_id,
            claim=claim,
            evidence_type=request.evidence_type,
            investigation_area=request.investigation_area,
            lifecycle_status=EvidenceLifecycleStatus.DRAFT,
            assessment_state=request.assessment_state,
            confidence_level=request.confidence_level,
            materiality=request.materiality,
            review_note=request.review_note,
            why_it_matters=request.why_it_matters,
            recommended_source_type=request.recommended_source_type,
            prepared_by_type=EvidencePreparedByType.USER,
            version=1,
            input_fingerprint=fingerprint,
            metadata_json={
                "creates_business_verdict": False,
                "creates_agent_run": False,
                "creates_llm_request": False,
            },
        )
        async with transactional(self._session):
            created = await self._evidence.create(row)
            await self._replace_links(
                owner_id=owner_id,
                project_id=project_id,
                investigation_id=investigation_id,
                evidence_id=created.id,
                source_links=request.source_links,
            )
            return created

    async def update(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        evidence_id: UUID,
        request: EvidenceUpdateRequest,
    ) -> InvestigationEvidenceTable | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        row = await self._evidence.get_by_id_for_owner(
            evidence_id, owner_id, project_id, investigation_id
        )
        if row is None:
            return None
        if row.lifecycle_status != EvidenceLifecycleStatus.DRAFT:
            raise InvalidStateError("immutable_evidence")

        claim = row.claim
        evidence_type = EvidenceType(row.evidence_type)
        area = EvidenceInvestigationArea(row.investigation_area)
        assessment = EvidenceAssessmentState(row.assessment_state)
        links_input: list[EvidenceSourceLinkInput] | None = request.source_links

        if request.claim is not None:
            claim = validate_atomic_claim(
                request.claim,
                assessment_state=request.assessment_state or assessment,
            )
        if request.evidence_type is not None:
            evidence_type = request.evidence_type
        if request.investigation_area is not None:
            area = request.investigation_area
        if request.assessment_state is not None:
            assessment = request.assessment_state

        existing_links = await self._links.list_for_evidence(
            evidence_id, owner_id, project_id
        )
        if links_input is None:
            links_input = [
                EvidenceSourceLinkInput(
                    source_id=link.source_id,
                    stance=EvidenceSourceStance(link.stance),
                    locator_type=EvidenceLocatorType(link.locator_type),
                    locator_value=link.locator_value,
                    excerpt=link.excerpt,
                    note=link.note,
                )
                for link in existing_links
            ]
        validate_source_requirement(
            assessment_state=assessment,
            source_links=links_input,
        )
        fingerprint = compute_evidence_fingerprint(
            project_id=project_id,
            investigation_id=investigation_id,
            claim=claim,
            evidence_type=evidence_type,
            investigation_area=area.value,
            source_links=links_input,
        )
        dup = await self._evidence.find_live_by_fingerprint(
            owner_id,
            project_id,
            investigation_id,
            fingerprint,
        )
        if dup is not None and dup.id != evidence_id:
            raise InvalidStateError("fingerprint_conflict")

        async with transactional(self._session):
            row.claim = claim
            row.evidence_type = evidence_type
            row.investigation_area = area
            row.assessment_state = assessment
            if request.confidence_level is not None:
                row.confidence_level = request.confidence_level
            if request.materiality is not None:
                row.materiality = request.materiality
            if request.review_note is not None:
                row.review_note = request.review_note
            if request.why_it_matters is not None:
                row.why_it_matters = request.why_it_matters
            if request.recommended_source_type is not None:
                row.recommended_source_type = request.recommended_source_type
            row.input_fingerprint = fingerprint
            row.updated_at = utc_now()
            await self._replace_links(
                owner_id=owner_id,
                project_id=project_id,
                investigation_id=investigation_id,
                evidence_id=evidence_id,
                source_links=links_input,
            )
            return await self._evidence.update(row)

    async def get(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        evidence_id: UUID,
    ) -> tuple[InvestigationEvidenceTable, list[EvidenceSourceLinkTable]] | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        row = await self._evidence.get_by_id_for_owner(
            evidence_id, owner_id, project_id, investigation_id
        )
        if row is None:
            return None
        links = await self._links.list_for_evidence(evidence_id, owner_id, project_id)
        return row, links

    async def list_evidence(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        **filters: object,
    ) -> list[tuple[InvestigationEvidenceTable, list[EvidenceSourceLinkTable]]] | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        if await self._ensure_investigation(owner_id, project_id, investigation_id) is None:
            return None
        rows = await self._evidence.list_for_investigation(
            owner_id,
            project_id,
            investigation_id,
            **filters,  # type: ignore[arg-type]
        )
        out: list[tuple[InvestigationEvidenceTable, list[EvidenceSourceLinkTable]]] = []
        for row in rows:
            links = await self._links.list_for_evidence(row.id, owner_id, project_id)
            out.append((row, links))
        return out

    async def summary(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
    ) -> EvidenceSummary | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        if await self._ensure_investigation(owner_id, project_id, investigation_id) is None:
            return None
        rows = await self._evidence.list_all_for_summary(
            owner_id, project_id, investigation_id
        )
        by_assessment: dict[str, int] = {}
        by_area: dict[str, int] = {}
        by_confidence: dict[str, int] = {}
        by_materiality: dict[str, int] = {}
        accepted = 0
        unsupported_critical = 0
        conflicting_critical = 0
        outdated_critical = 0
        missing_critical = 0
        for row in rows:
            by_assessment[row.assessment_state] = by_assessment.get(row.assessment_state, 0) + 1
            by_area[row.investigation_area] = by_area.get(row.investigation_area, 0) + 1
            by_confidence[row.confidence_level] = by_confidence.get(row.confidence_level, 0) + 1
            by_materiality[row.materiality] = by_materiality.get(row.materiality, 0) + 1
            if row.lifecycle_status == EvidenceLifecycleStatus.ACCEPTED:
                accepted += 1
            critical = row.materiality == EvidenceMateriality.CRITICAL
            if critical and row.assessment_state == EvidenceAssessmentState.MISSING:
                missing_critical += 1
                unsupported_critical += 1
            if critical and row.assessment_state == EvidenceAssessmentState.CONFLICTING:
                conflicting_critical += 1
            if critical and row.assessment_state == EvidenceAssessmentState.OUTDATED:
                outdated_critical += 1
        contribution = verdict_readiness_contribution(
            missing_critical=missing_critical,
            conflicting_critical=conflicting_critical,
            outdated_critical=outdated_critical,
            accepted_count=accepted,
        )
        return EvidenceSummary(
            total=len(rows),
            by_assessment_state=by_assessment,
            by_area=by_area,
            by_confidence=by_confidence,
            by_materiality=by_materiality,
            accepted_count=accepted,
            unsupported_critical_claims=unsupported_critical,
            conflicting_critical_claims=conflicting_critical,
            outdated_critical_claims=outdated_critical,
            missing_critical_claims=missing_critical,
            verdict_readiness_contribution=contribution,
            creates_business_verdict=False,
        )

    def _transition(
        self,
        row: InvestigationEvidenceTable,
        target: EvidenceLifecycleStatus,
    ) -> None:
        current = EvidenceLifecycleStatus(row.lifecycle_status)
        if target not in _LIFECYCLE.get(current, frozenset()):
            raise InvalidStateError("invalid_transition")

    async def submit_review(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        evidence_id: UUID,
        body: EvidenceReviewNoteRequest | None = None,
    ) -> InvestigationEvidenceTable | None:
        return await self._lifecycle_action(
            owner_id,
            project_id,
            investigation_id,
            evidence_id,
            EvidenceLifecycleStatus.UNDER_REVIEW,
            action="submit_review",
            note=body.note if body else None,
        )

    async def accept(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        evidence_id: UUID,
        body: EvidenceReviewNoteRequest | None = None,
    ) -> InvestigationEvidenceTable | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        row = await self._evidence.get_by_id_for_owner(
            evidence_id, owner_id, project_id, investigation_id
        )
        if row is None:
            return None
        links = await self._links.list_for_evidence(evidence_id, owner_id, project_id)
        validate_accept_links(
            assessment_state=EvidenceAssessmentState(row.assessment_state),
            stances=[EvidenceSourceStance(link.stance) for link in links],
        )
        previous_lifecycle = row.lifecycle_status
        self._transition(row, EvidenceLifecycleStatus.ACCEPTED)
        async with transactional(self._session):
            if row.assessment_state == EvidenceAssessmentState.UNVERIFIED:
                row.assessment_state = EvidenceAssessmentState.CONFIRMED
            self._audit(
                row,
                action="accept",
                previous=str(previous_lifecycle),
                new=EvidenceLifecycleStatus.ACCEPTED.value,
                note=body.note if body else None,
                reviewer=owner_id,
            )
            row.lifecycle_status = EvidenceLifecycleStatus.ACCEPTED
            row.reviewed_by = owner_id
            row.reviewed_at = utc_now()
            if body and body.note:
                row.review_note = sanitize_text(body.note).strip()[:2000]
            row.updated_at = utc_now()
            return await self._evidence.update(row)

    async def reject(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        evidence_id: UUID,
        body: EvidenceReviewNoteRequest | None = None,
    ) -> InvestigationEvidenceTable | None:
        return await self._lifecycle_action(
            owner_id,
            project_id,
            investigation_id,
            evidence_id,
            EvidenceLifecycleStatus.REJECTED,
            action="reject",
            note=body.note if body else None,
        )

    async def mark_conflicting(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        evidence_id: UUID,
        body: EvidenceReviewNoteRequest | None = None,
    ) -> InvestigationEvidenceTable | None:
        return await self._assessment_action(
            owner_id,
            project_id,
            investigation_id,
            evidence_id,
            EvidenceAssessmentState.CONFLICTING,
            action="mark_conflicting",
            note=body.note if body else None,
        )

    async def mark_outdated(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        evidence_id: UUID,
        body: EvidenceReviewNoteRequest | None = None,
    ) -> InvestigationEvidenceTable | None:
        return await self._assessment_action(
            owner_id,
            project_id,
            investigation_id,
            evidence_id,
            EvidenceAssessmentState.OUTDATED,
            action="mark_outdated",
            note=body.note if body else None,
        )

    async def archive(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        evidence_id: UUID,
        body: EvidenceReviewNoteRequest | None = None,
    ) -> InvestigationEvidenceTable | None:
        return await self._lifecycle_action(
            owner_id,
            project_id,
            investigation_id,
            evidence_id,
            EvidenceLifecycleStatus.ARCHIVED,
            action="archive",
            note=body.note if body else None,
        )

    async def supersede(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        evidence_id: UUID,
        request: EvidenceSupersedeRequest,
    ) -> InvestigationEvidenceTable | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        old = await self._evidence.get_by_id_for_owner(
            evidence_id, owner_id, project_id, investigation_id
        )
        if old is None:
            return None
        if old.lifecycle_status not in (
            EvidenceLifecycleStatus.ACCEPTED,
            EvidenceLifecycleStatus.REJECTED,
        ):
            raise InvalidStateError("invalid_transition")
        claim = validate_atomic_claim(
            request.claim,
            assessment_state=request.assessment_state,
        )
        validate_source_requirement(
            assessment_state=request.assessment_state,
            source_links=request.source_links,
        )
        fingerprint = compute_evidence_fingerprint(
            project_id=project_id,
            investigation_id=investigation_id,
            claim=claim,
            evidence_type=request.evidence_type,
            investigation_area=request.investigation_area.value,
            source_links=request.source_links,
        )
        async with transactional(self._session):
            old_status = old.lifecycle_status
            self._transition(old, EvidenceLifecycleStatus.SUPERSEDED)
            self._audit(
                old,
                action="supersede",
                previous=str(old_status),
                new=EvidenceLifecycleStatus.SUPERSEDED.value,
                note=request.review_note,
                reviewer=owner_id,
            )
            old.lifecycle_status = EvidenceLifecycleStatus.SUPERSEDED
            old.updated_at = utc_now()
            await self._evidence.update(old)
            created = InvestigationEvidenceTable(
                owner_id=owner_id,
                project_id=project_id,
                investigation_id=investigation_id,
                claim=claim,
                evidence_type=request.evidence_type,
                investigation_area=request.investigation_area,
                lifecycle_status=EvidenceLifecycleStatus.DRAFT,
                assessment_state=request.assessment_state,
                confidence_level=request.confidence_level,
                materiality=request.materiality,
                review_note=request.review_note,
                why_it_matters=request.why_it_matters,
                recommended_source_type=request.recommended_source_type,
                prepared_by_type=EvidencePreparedByType.USER,
                version=old.version + 1,
                input_fingerprint=fingerprint,
                supersedes_evidence_id=old.id,
                metadata_json={"creates_business_verdict": False},
            )
            new_row = await self._evidence.create(created)
            await self._replace_links(
                owner_id=owner_id,
                project_id=project_id,
                investigation_id=investigation_id,
                evidence_id=new_row.id,
                source_links=request.source_links,
            )
            return new_row

    async def attach_source(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        evidence_id: UUID,
        source_id: UUID,
        body: EvidenceSourceLinkInput,
    ) -> EvidenceSourceLinkTable | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        row = await self._evidence.get_by_id_for_owner(
            evidence_id, owner_id, project_id, investigation_id
        )
        if row is None:
            return None
        if row.lifecycle_status != EvidenceLifecycleStatus.DRAFT:
            raise InvalidStateError("immutable_evidence")
        if body.source_id != source_id:
            raise InvalidStateError("invalid_source_stance")
        async with transactional(self._session):
            await self._assert_source_usable(
                owner_id, project_id, investigation_id, source_id
            )
            excerpt = sanitize_text(body.excerpt).strip()[:2000] if body.excerpt else None
            link = EvidenceSourceLinkTable(
                owner_id=owner_id,
                project_id=project_id,
                investigation_id=investigation_id,
                evidence_id=evidence_id,
                source_id=source_id,
                stance=body.stance,
                locator_type=body.locator_type,
                locator_value=body.locator_value,
                excerpt=excerpt,
                excerpt_hash=excerpt_hash(excerpt),
                note=body.note,
                added_by=owner_id,
            )
            created = await self._links.create(link)
            # refresh fingerprint
            links = await self._links.list_for_evidence(evidence_id, owner_id, project_id)
            inputs = [
                EvidenceSourceLinkInput(
                    source_id=item.source_id,
                    stance=EvidenceSourceStance(item.stance),
                    locator_type=EvidenceLocatorType(item.locator_type),
                    locator_value=item.locator_value,
                    excerpt=item.excerpt,
                    note=item.note,
                )
                for item in links
            ]
            row.input_fingerprint = compute_evidence_fingerprint(
                project_id=project_id,
                investigation_id=investigation_id,
                claim=row.claim,
                evidence_type=EvidenceType(row.evidence_type),
                investigation_area=str(row.investigation_area),
                source_links=inputs,
            )
            row.updated_at = utc_now()
            await self._evidence.update(row)
            return created

    async def _lifecycle_action(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        evidence_id: UUID,
        target: EvidenceLifecycleStatus,
        *,
        action: str,
        note: str | None,
        mutate: InvestigationEvidenceTable | None = None,
    ) -> InvestigationEvidenceTable | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        row = mutate or await self._evidence.get_by_id_for_owner(
            evidence_id, owner_id, project_id, investigation_id
        )
        if row is None:
            return None
        previous = row.lifecycle_status
        self._transition(row, target)
        async with transactional(self._session):
            self._audit(
                row,
                action=action,
                previous=str(previous),
                new=target.value,
                note=note,
                reviewer=owner_id,
            )
            row.lifecycle_status = target
            if target in (
                EvidenceLifecycleStatus.ACCEPTED,
                EvidenceLifecycleStatus.REJECTED,
            ):
                row.reviewed_by = owner_id
                row.reviewed_at = utc_now()
            if note:
                row.review_note = sanitize_text(note).strip()[:2000]
            row.updated_at = utc_now()
            return await self._evidence.update(row)

    async def _assessment_action(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        evidence_id: UUID,
        assessment: EvidenceAssessmentState,
        *,
        action: str,
        note: str | None,
    ) -> InvestigationEvidenceTable | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        row = await self._evidence.get_by_id_for_owner(
            evidence_id, owner_id, project_id, investigation_id
        )
        if row is None:
            return None
        if row.lifecycle_status in (
            EvidenceLifecycleStatus.SUPERSEDED,
            EvidenceLifecycleStatus.ARCHIVED,
        ):
            raise InvalidStateError("immutable_evidence")
        previous = row.assessment_state
        async with transactional(self._session):
            self._audit(
                row,
                action=action,
                previous=str(previous),
                new=assessment.value,
                note=note,
                reviewer=owner_id,
            )
            row.assessment_state = assessment
            if note:
                row.review_note = sanitize_text(note).strip()[:2000]
            row.updated_at = utc_now()
            return await self._evidence.update(row)

    @staticmethod
    def creates_business_verdict() -> bool:
        return False

    @staticmethod
    def creates_agent_run() -> bool:
        return False

    @staticmethod
    def creates_llm_request() -> bool:
        return False

    @staticmethod
    def completes_investigation() -> bool:
        return False

    @staticmethod
    def fetches_external() -> bool:
        return False
