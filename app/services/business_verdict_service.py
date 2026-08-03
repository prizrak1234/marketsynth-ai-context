"""BusinessVerdict service (Commercial MVP P0.5).

Durable commercial viability decision on immutable Evidence snapshot.
No Strategy create, Agent Run, LLM, execution/publication approval.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_text
from app.db.base import utc_now
from app.db.models.business_verdict import (
    BusinessVerdictEvidenceLinkTable,
    BusinessVerdictEvidenceSnapshotTable,
    BusinessVerdictTable,
)
from app.db.models.evidence import InvestigationEvidenceTable
from app.db.models.investigation import InvestigationTable
from app.db.repositories.business_verdicts import (
    BusinessVerdictEvidenceLinkRepository,
    BusinessVerdictEvidenceSnapshotRepository,
    BusinessVerdictRepository,
)
from app.db.repositories.evidence import EvidenceRepository
from app.db.repositories.investigations import InvestigationRepository
from app.domain.business_verdict_engine import (
    compute_snapshot_hash,
    compute_strategy_eligibility,
    investigation_allows_go,
    map_readiness_from_contribution,
    recommend_confidence,
    recommend_deterministic_verdict_type,
    snapshot_stats,
    validate_evidence_roles_for_type,
    validate_go_confidence,
    validate_verdict_type_against_readiness,
)
from app.domain.evidence_fingerprint import verdict_readiness_contribution
from app.schemas.contracts import (
    BusinessVerdictConfidenceLevel,
    BusinessVerdictCreate,
    BusinessVerdictEvidenceLinkCreate,
    BusinessVerdictEvidenceRole,
    BusinessVerdictLifecycleStatus,
    BusinessVerdictPreparedByType,
    BusinessVerdictReviewRequest,
    BusinessVerdictUpdate,
    EvidenceAssessmentState,
    EvidenceLifecycleStatus,
    EvidenceMateriality,
    InvestigationStatus,
    VerdictAssumption,
    VerdictChangeTrigger,
    VerdictCondition,
    VerdictConditionStatus,
    VerdictCriticalRisk,
    VerdictFinding,
    VerdictKind,
    VerdictReadinessStatus,
    VerdictSensitivity,
)
from app.services.projects_service import ProjectService
from app.services.transaction import transactional

_LIFECYCLE: dict[
    BusinessVerdictLifecycleStatus, frozenset[BusinessVerdictLifecycleStatus]
] = {
    BusinessVerdictLifecycleStatus.DRAFT: frozenset(
        {
            BusinessVerdictLifecycleStatus.UNDER_REVIEW,
            BusinessVerdictLifecycleStatus.ARCHIVED,
            BusinessVerdictLifecycleStatus.SUPERSEDED,
        }
    ),
    BusinessVerdictLifecycleStatus.UNDER_REVIEW: frozenset(
        {
            BusinessVerdictLifecycleStatus.DRAFT,
            BusinessVerdictLifecycleStatus.APPROVED,
            BusinessVerdictLifecycleStatus.REJECTED,
            BusinessVerdictLifecycleStatus.SUPERSEDED,
        }
    ),
    BusinessVerdictLifecycleStatus.APPROVED: frozenset(
        {
            BusinessVerdictLifecycleStatus.SUPERSEDED,
            BusinessVerdictLifecycleStatus.ARCHIVED,
        }
    ),
    BusinessVerdictLifecycleStatus.REJECTED: frozenset(
        {
            BusinessVerdictLifecycleStatus.ARCHIVED,
            BusinessVerdictLifecycleStatus.SUPERSEDED,
        }
    ),
    BusinessVerdictLifecycleStatus.SUPERSEDED: frozenset(),
    BusinessVerdictLifecycleStatus.ARCHIVED: frozenset(),
}


def _dump_models(items: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items:
        if hasattr(item, "model_dump"):
            data = item.model_dump(mode="json")
        else:
            data = dict(item)
        out.append(data)
    return out


def _parse_conditions(raw: list[Any]) -> list[VerdictCondition]:
    return [VerdictCondition.model_validate(x) for x in raw]


def _parse_risks(raw: list[Any]) -> list[VerdictCriticalRisk]:
    return [VerdictCriticalRisk.model_validate(x) for x in raw]


class BusinessVerdictService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._projects = ProjectService(session)
        self._investigations = InvestigationRepository(session)
        self._evidence = EvidenceRepository(session)
        self._verdicts = BusinessVerdictRepository(session)
        self._snapshots = BusinessVerdictEvidenceSnapshotRepository(session)
        self._links = BusinessVerdictEvidenceLinkRepository(session)

    async def _ensure_project(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    async def _ensure_investigation(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
    ) -> InvestigationTable | None:
        return await self._investigations.get_by_id_for_owner(
            investigation_id, owner_id, project_id
        )

    def _transition(
        self,
        row: BusinessVerdictTable,
        target: BusinessVerdictLifecycleStatus,
    ) -> None:
        current = BusinessVerdictLifecycleStatus(row.lifecycle_status)
        allowed = _LIFECYCLE.get(current, frozenset())
        if target not in allowed:
            raise InvalidStateError("invalid_transition")
        if current == BusinessVerdictLifecycleStatus.APPROVED and target not in (
            BusinessVerdictLifecycleStatus.SUPERSEDED,
            BusinessVerdictLifecycleStatus.ARCHIVED,
        ):
            raise InvalidStateError("immutable_verdict")
        row.lifecycle_status = target
        row.updated_at = utc_now()

    async def _load_evidence_rows(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
    ) -> list[InvestigationEvidenceTable]:
        return await self._evidence.list_all_for_summary(
            owner_id, project_id, investigation_id
        )

    async def _resolve_or_create_snapshot(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        rows: list[InvestigationEvidenceTable],
    ) -> BusinessVerdictEvidenceSnapshotTable:
        stats = snapshot_stats(rows)
        contribution = verdict_readiness_contribution(
            missing_critical=stats["missing_critical_count"],
            conflicting_critical=stats["conflicting_critical_count"],
            outdated_critical=stats["outdated_critical_count"],
            accepted_count=stats["accepted_evidence_count"],
        )
        readiness = map_readiness_from_contribution(contribution)
        snap_hash = compute_snapshot_hash(
            project_id=project_id,
            investigation_id=investigation_id,
            evidence_versions=stats["evidence_versions"],
        )
        existing = await self._snapshots.find_reusable(
            owner_id, project_id, investigation_id, snap_hash
        )
        if existing is not None:
            return existing
        snap = BusinessVerdictEvidenceSnapshotTable(
            owner_id=owner_id,
            project_id=project_id,
            investigation_id=investigation_id,
            snapshot_hash=snap_hash,
            evidence_ids=stats["evidence_ids"],
            evidence_versions=stats["evidence_versions"],
            accepted_evidence_count=stats["accepted_evidence_count"],
            missing_critical_count=stats["missing_critical_count"],
            conflicting_critical_count=stats["conflicting_critical_count"],
            outdated_critical_count=stats["outdated_critical_count"],
            area_coverage=stats["area_coverage"],
            readiness_status=readiness,
            verdict_readiness_contribution=contribution,
        )
        return await self._snapshots.create(snap)

    async def _resolve_evidence_for_links(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        link_inputs: list[BusinessVerdictEvidenceLinkCreate],
        rows_by_id: dict[UUID, InvestigationEvidenceTable],
    ) -> list[tuple[BusinessVerdictEvidenceLinkCreate, InvestigationEvidenceTable]]:
        resolved: list[tuple[BusinessVerdictEvidenceLinkCreate, InvestigationEvidenceTable]] = []
        for link in link_inputs:
            row = rows_by_id.get(link.evidence_id)
            if row is None:
                # may belong to other investigation/project
                other = await self._evidence.get_by_id(link.evidence_id)
                if other is None:
                    raise InvalidStateError("evidence_snapshot_invalid")
                if other.project_id != project_id or other.owner_id != owner_id:
                    raise InvalidStateError("forbidden")
                if other.investigation_id != investigation_id:
                    raise InvalidStateError("evidence_snapshot_invalid")
                row = other
            if row.investigation_id != investigation_id or row.project_id != project_id:
                raise InvalidStateError("evidence_snapshot_invalid")
            if int(row.version) != int(link.evidence_version):
                raise InvalidStateError("stale_version")
            resolved.append((link, row))
        return resolved

    def _validate_payload(
        self,
        *,
        verdict_type: VerdictKind,
        confidence: BusinessVerdictConfidenceLevel,
        readiness: VerdictReadinessStatus,
        investigation_status: InvestigationStatus,
        snap: BusinessVerdictEvidenceSnapshotTable,
        roles: list[BusinessVerdictEvidenceRole],
        conditions: list[VerdictCondition],
        risks: list[VerdictCriticalRisk],
    ) -> None:
        validate_verdict_type_against_readiness(verdict_type, readiness)
        validate_go_confidence(confidence, verdict_type)
        if verdict_type == VerdictKind.GO and not investigation_allows_go(investigation_status):
            raise InvalidStateError("verdict_type_not_allowed")
        if verdict_type == VerdictKind.GO and readiness != VerdictReadinessStatus.READY_FOR_REVIEW:
            raise InvalidStateError("verdict_type_not_allowed")
        validate_evidence_roles_for_type(
            verdict_type=verdict_type,
            roles=roles,
            missing_critical=snap.missing_critical_count,
            conflicting_critical=snap.conflicting_critical_count,
            outdated_critical=snap.outdated_critical_count,
            conditions=conditions,
            critical_risks=risks,
        )

    async def _create_links(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        verdict_id: UUID,
        resolved: list[tuple[BusinessVerdictEvidenceLinkCreate, InvestigationEvidenceTable]],
    ) -> list[BusinessVerdictEvidenceLinkTable]:
        created: list[BusinessVerdictEvidenceLinkTable] = []
        for link, row in resolved:
            note = sanitize_text(link.note).strip() if link.note else None
            criterion = (
                sanitize_text(link.decision_criterion).strip()
                if link.decision_criterion
                else None
            )
            link_row = BusinessVerdictEvidenceLinkTable(
                owner_id=owner_id,
                project_id=project_id,
                verdict_id=verdict_id,
                evidence_id=row.id,
                evidence_version=row.version,
                role=link.role,
                decision_criterion=criterion or None,
                materiality_at_snapshot=EvidenceMateriality(row.materiality),
                assessment_state_at_snapshot=EvidenceAssessmentState(row.assessment_state),
                confidence_at_snapshot=row.confidence_level,
                note=note or None,
            )
            created.append(await self._links.create(link_row))
        return created

    def _append_review_event(
        self,
        row: BusinessVerdictTable,
        *,
        action: str,
        actor_id: UUID,
        note: str | None,
        previous: str,
        new_status: str,
    ) -> None:
        meta = dict(row.metadata_json or {})
        events = list(meta.get("review_events") or [])
        events.append(
            {
                "action": action,
                "actor_id": str(actor_id),
                "note": note,
                "previous_status": previous,
                "new_status": new_status,
                "evidence_snapshot_hash": row.evidence_snapshot_hash,
                "at": utc_now().isoformat(),
            }
        )
        meta["review_events"] = events
        row.metadata_json = meta

    async def create(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
        body: BusinessVerdictCreate,
    ) -> BusinessVerdictTable | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        inv = await self._ensure_investigation(owner_id, project_id, investigation_id)
        if inv is None:
            return None

        rows = await self._load_evidence_rows(owner_id, project_id, investigation_id)
        snap = await self._resolve_or_create_snapshot(
            owner_id, project_id, investigation_id, rows
        )
        rows_by_id = {r.id: r for r in rows}
        resolved = await self._resolve_evidence_for_links(
            owner_id, project_id, investigation_id, body.evidence_links, rows_by_id
        )
        conditions = list(body.conditions)
        risks = list(body.critical_risks)
        self._validate_payload(
            verdict_type=body.verdict_type,
            confidence=body.confidence_level,
            readiness=VerdictReadinessStatus(snap.readiness_status),
            investigation_status=InvestigationStatus(inv.status),
            snap=snap,
            roles=[link.role for link, _ in resolved],
            conditions=conditions,
            risks=risks,
        )

        supersedes_id = body.supersedes_verdict_id
        if supersedes_id is not None:
            prev = await self._verdicts.get_by_id_for_owner(
                supersedes_id, owner_id, project_id
            )
            if prev is None:
                raise InvalidStateError("verdict_not_found")
            if BusinessVerdictLifecycleStatus(prev.lifecycle_status) not in (
                BusinessVerdictLifecycleStatus.APPROVED,
                BusinessVerdictLifecycleStatus.REJECTED,
                BusinessVerdictLifecycleStatus.DRAFT,
                BusinessVerdictLifecycleStatus.UNDER_REVIEW,
            ):
                raise InvalidStateError("invalid_transition")

        version = await self._verdicts.next_version(owner_id, project_id)
        row = BusinessVerdictTable(
            owner_id=owner_id,
            project_id=project_id,
            investigation_id=investigation_id,
            investigation_version=inv.version,
            project_brief_id=inv.project_brief_id,
            project_brief_version=inv.project_brief_version,
            version=version,
            verdict_type=body.verdict_type,
            lifecycle_status=BusinessVerdictLifecycleStatus.DRAFT,
            confidence_level=body.confidence_level,
            evidence_snapshot_id=snap.id,
            evidence_snapshot_hash=snap.snapshot_hash,
            executive_conclusion=sanitize_text(body.executive_conclusion).strip()[:2000],
            executive_rationale=sanitize_text(body.executive_rationale).strip()[:8000],
            primary_business_implication=sanitize_text(
                body.primary_business_implication
            ).strip()[:2000],
            recommended_next_action=sanitize_text(
                body.recommended_next_action
            ).strip()[:2000],
            supporting_evidence_summary=(
                sanitize_text(body.supporting_evidence_summary).strip()[:4000]
                if body.supporting_evidence_summary
                else None
            ),
            counter_evidence_summary=(
                sanitize_text(body.counter_evidence_summary).strip()[:4000]
                if body.counter_evidence_summary
                else None
            ),
            conditions=_dump_models(conditions),
            critical_risks=_dump_models(risks),
            assumptions=_dump_models(list(body.assumptions)),
            change_triggers=_dump_models(list(body.change_triggers)),
            findings=_dump_models(list(body.findings)),
            readiness_snapshot=VerdictReadinessStatus(snap.readiness_status),
            prepared_by_type=body.prepared_by_type,
            prepared_by_reference=body.prepared_by_reference,
            supersedes_verdict_id=supersedes_id,
            metadata_json={
                "creates_strategy": False,
                "creates_execution_approval": False,
                "creates_publication_approval": False,
                "creates_agent_run": False,
                "review_events": [],
            },
        )
        async with transactional(self._session):
            row = await self._verdicts.create(row)
            await self._create_links(
                owner_id=owner_id,
                project_id=project_id,
                verdict_id=row.id,
                resolved=resolved,
            )
            return row

    async def build_deterministic_draft(
        self,
        owner_id: UUID,
        project_id: UUID,
        investigation_id: UUID,
    ) -> BusinessVerdictTable | None:
        """Explicit user action only — no page-load auto-create."""

        if not await self._ensure_project(owner_id, project_id):
            return None
        inv = await self._ensure_investigation(owner_id, project_id, investigation_id)
        if inv is None:
            return None

        rows = await self._load_evidence_rows(owner_id, project_id, investigation_id)
        snap = await self._resolve_or_create_snapshot(
            owner_id, project_id, investigation_id, rows
        )
        readiness = VerdictReadinessStatus(snap.readiness_status)

        accepted_supporting = [
            r
            for r in rows
            if r.lifecycle_status == EvidenceLifecycleStatus.ACCEPTED
            and r.assessment_state
            in (
                EvidenceAssessmentState.CONFIRMED,
                EvidenceAssessmentState.PARTIAL,
                EvidenceAssessmentState.UNVERIFIED,
            )
        ]
        weakening = [
            r
            for r in rows
            if r.assessment_state == EvidenceAssessmentState.CONFLICTING
            or (
                r.materiality == EvidenceMateriality.CRITICAL
                and r.assessment_state == EvidenceAssessmentState.MISSING
            )
        ]
        verdict_type = recommend_deterministic_verdict_type(
            readiness=readiness,
            investigation_status=InvestigationStatus(inv.status),
            missing_critical=snap.missing_critical_count,
            conflicting_critical=snap.conflicting_critical_count,
            outdated_critical=snap.outdated_critical_count,
            accepted_count=snap.accepted_evidence_count,
            area_coverage=dict(snap.area_coverage or {}),
            has_supporting_accepted=len(accepted_supporting) > 0,
            has_weakening=len(weakening) > 0,
            has_verdict_changing_risk=False,
        )
        confidence = recommend_confidence(
            readiness=readiness,
            missing_critical=snap.missing_critical_count,
            conflicting_critical=snap.conflicting_critical_count,
            outdated_critical=snap.outdated_critical_count,
            accepted_count=snap.accepted_evidence_count,
        )

        conditions: list[VerdictCondition] = []
        risks: list[VerdictCriticalRisk] = []
        assumptions: list[VerdictAssumption] = []
        triggers: list[VerdictChangeTrigger] = []
        findings: list[VerdictFinding] = []
        links: list[BusinessVerdictEvidenceLinkCreate] = []

        for r in accepted_supporting[:8]:
            links.append(
                BusinessVerdictEvidenceLinkCreate(
                    evidence_id=r.id,
                    evidence_version=r.version,
                    role=BusinessVerdictEvidenceRole.SUPPORTS,
                    decision_criterion="accepted_evidence",
                )
            )
        for r in weakening[:8]:
            role = (
                BusinessVerdictEvidenceRole.CONTRADICTS
                if r.assessment_state == EvidenceAssessmentState.CONFLICTING
                else BusinessVerdictEvidenceRole.WEAKENS
            )
            links.append(
                BusinessVerdictEvidenceLinkCreate(
                    evidence_id=r.id,
                    evidence_version=r.version,
                    role=role,
                    decision_criterion="critical_gap_or_conflict",
                )
            )
        if verdict_type == VerdictKind.CONDITIONAL_GO:
            conditions.append(
                VerdictCondition(
                    id="cond_validate_critical_gaps",
                    title="Закрыть критические evidence-gaps до Strategy",
                    required_action="Собрать недостающие critical Evidence и повторно зафиксировать snapshot",
                    owner_role="project_owner",
                    success_criterion="missing_critical_count = 0 и conflicting_critical_count = 0",
                    evidence_required=True,
                    target_milestone="before_strategy",
                    consequence_if_unmet="Вердикт должен быть пересмотрен; Strategy не считается безусловной",
                    status=VerdictConditionStatus.OPEN,
                )
            )
            if snap.missing_critical_count > 0 and not any(
                l.role == BusinessVerdictEvidenceRole.CONDITION_BASIS for l in links
            ):
                # condition_basis via supporting or missing gap linkage
                gap = next(
                    (
                        r
                        for r in rows
                        if r.materiality == EvidenceMateriality.CRITICAL
                        and r.assessment_state == EvidenceAssessmentState.MISSING
                    ),
                    None,
                )
                if gap is not None:
                    links.append(
                        BusinessVerdictEvidenceLinkCreate(
                            evidence_id=gap.id,
                            evidence_version=gap.version,
                            role=BusinessVerdictEvidenceRole.CONDITION_BASIS,
                            decision_criterion="missing_critical",
                        )
                    )
            triggers.append(
                VerdictChangeTrigger(
                    title="Критический conflict resolved",
                    current_state="open critical gaps or conditions",
                    threshold_or_event="accepted critical Evidence closes gaps",
                    possible_transition="CONDITIONAL_GO → GO",
                    required_review=True,
                )
            )
        if verdict_type == VerdictKind.NO_GO and not links:
            for r in rows[:3]:
                links.append(
                    BusinessVerdictEvidenceLinkCreate(
                        evidence_id=r.id,
                        evidence_version=r.version,
                        role=BusinessVerdictEvidenceRole.RISK_BASIS,
                        decision_criterion="no_go_basis",
                    )
                )
            risks.append(
                VerdictCriticalRisk(
                    title="Неприемлемый коммерческий риск при текущей форме",
                    description="Deterministic builder: ослабляющие/конфликтные сигналы превышают поддержку",
                    severity="critical",
                    probability="high",
                    business_consequence="Вероятны потери при запуске в текущем виде",
                    verdict_sensitivity=VerdictSensitivity.VERDICT_CHANGING,
                )
            )
        if verdict_type == VerdictKind.INSUFFICIENT_DATA and not links:
            for r in rows[:5]:
                links.append(
                    BusinessVerdictEvidenceLinkCreate(
                        evidence_id=r.id,
                        evidence_version=r.version,
                        role=BusinessVerdictEvidenceRole.CONTEXT,
                        decision_criterion="gap_inventory",
                    )
                )

        conclusions = {
            VerdictKind.GO: "Доказательная база допускает переход к Strategy в заявленных рамках.",
            VerdictKind.CONDITIONAL_GO: "Проект потенциально жизнеспособен только при выполнении явных условий.",
            VerdictKind.NO_GO: "Доступные Evidence указывают на неприемлемый риск продолжения в текущей форме.",
            VerdictKind.INSUFFICIENT_DATA: "Доказательной базы недостаточно для ответственного GO / CONDITIONAL_GO / NO_GO.",
        }
        next_actions = {
            VerdictKind.GO: "После human review: рассмотреть Strategy eligibility (не авто-создание).",
            VerdictKind.CONDITIONAL_GO: "Закрыть условия и подтвердить Evidence перед Strategy.",
            VerdictKind.NO_GO: "Pivot route / пересмотр Brief — Strategy заблокирована.",
            VerdictKind.INSUFFICIENT_DATA: "Вернуться в Investigation и собрать critical Evidence.",
        }

        body = BusinessVerdictCreate(
            verdict_type=verdict_type,
            confidence_level=confidence,
            executive_conclusion=conclusions[verdict_type],
            executive_rationale=(
                f"Deterministic draft from Evidence snapshot {snap.snapshot_hash[:12]}… "
                f"readiness={readiness.value}; contribution={snap.verdict_readiness_contribution}; "
                f"accepted={snap.accepted_evidence_count}; missing_critical={snap.missing_critical_count}; "
                f"conflicting_critical={snap.conflicting_critical_count}. "
                "Readiness does not equal verdict type."
            ),
            primary_business_implication=conclusions[verdict_type],
            recommended_next_action=next_actions[verdict_type],
            supporting_evidence_summary=f"Accepted supporting links: {len(accepted_supporting)}",
            counter_evidence_summary=f"Weakening/conflict signals: {len(weakening)}",
            evidence_links=links,
            conditions=conditions,
            critical_risks=risks,
            assumptions=assumptions,
            change_triggers=triggers,
            findings=findings,
            prepared_by_type=BusinessVerdictPreparedByType.DETERMINISTIC,
            prepared_by_reference="business_verdict_engine.recommend_deterministic_verdict_type",
        )
        # Bypass nested transactional by inlining create logic via public create
        # (create is also transactional — re-enter without decorator stack issues by calling body path)
        return await self.create(owner_id, project_id, investigation_id, body)

    async def list_verdicts(
        self,
        owner_id: UUID,
        project_id: UUID,
        **filters: Any,
    ) -> list[BusinessVerdictTable] | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        return await self._verdicts.list_for_project(owner_id, project_id, **filters)

    async def get(
        self,
        owner_id: UUID,
        project_id: UUID,
        verdict_id: UUID,
    ) -> BusinessVerdictTable | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        return await self._verdicts.get_by_id_for_owner(verdict_id, owner_id, project_id)

    async def get_latest(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> BusinessVerdictTable | None:
        if not await self._ensure_project(owner_id, project_id):
            return None
        approved = await self._verdicts.latest_approved(owner_id, project_id)
        if approved is not None:
            return approved
        return await self._verdicts.latest_any(owner_id, project_id)

    async def get_snapshot(
        self,
        owner_id: UUID,
        project_id: UUID,
        verdict_id: UUID,
    ) -> BusinessVerdictEvidenceSnapshotTable | None:
        row = await self.get(owner_id, project_id, verdict_id)
        if row is None:
            return None
        return await self._snapshots.get_by_id_for_owner(
            row.evidence_snapshot_id, owner_id, project_id
        )

    async def list_links(
        self,
        owner_id: UUID,
        project_id: UUID,
        verdict_id: UUID,
    ) -> list[BusinessVerdictEvidenceLinkTable]:
        return await self._links.list_for_verdict(verdict_id, owner_id, project_id)

    async def update_draft(
        self,
        owner_id: UUID,
        project_id: UUID,
        verdict_id: UUID,
        body: BusinessVerdictUpdate,
    ) -> BusinessVerdictTable | None:
        row = await self.get(owner_id, project_id, verdict_id)
        if row is None:
            return None
        if BusinessVerdictLifecycleStatus(row.lifecycle_status) != BusinessVerdictLifecycleStatus.DRAFT:
            raise InvalidStateError("immutable_verdict")
        inv = await self._ensure_investigation(owner_id, project_id, row.investigation_id)
        if inv is None:
            return None
        snap = await self._snapshots.get_by_id_for_owner(
            row.evidence_snapshot_id, owner_id, project_id
        )
        if snap is None:
            raise InvalidStateError("evidence_snapshot_invalid")

        if body.verdict_type is not None:
            row.verdict_type = body.verdict_type
        if body.confidence_level is not None:
            row.confidence_level = body.confidence_level
        if body.executive_conclusion is not None:
            row.executive_conclusion = sanitize_text(body.executive_conclusion).strip()[:2000]
        if body.executive_rationale is not None:
            row.executive_rationale = sanitize_text(body.executive_rationale).strip()[:8000]
        if body.primary_business_implication is not None:
            row.primary_business_implication = sanitize_text(
                body.primary_business_implication
            ).strip()[:2000]
        if body.recommended_next_action is not None:
            row.recommended_next_action = sanitize_text(
                body.recommended_next_action
            ).strip()[:2000]
        if body.supporting_evidence_summary is not None:
            row.supporting_evidence_summary = sanitize_text(
                body.supporting_evidence_summary
            ).strip()[:4000]
        if body.counter_evidence_summary is not None:
            row.counter_evidence_summary = sanitize_text(
                body.counter_evidence_summary
            ).strip()[:4000]
        if body.conditions is not None:
            row.conditions = _dump_models(list(body.conditions))
        if body.critical_risks is not None:
            row.critical_risks = _dump_models(list(body.critical_risks))
        if body.assumptions is not None:
            row.assumptions = _dump_models(list(body.assumptions))
        if body.change_triggers is not None:
            row.change_triggers = _dump_models(list(body.change_triggers))
        if body.findings is not None:
            row.findings = _dump_models(list(body.findings))

        links = await self._links.list_for_verdict(verdict_id, owner_id, project_id)
        self._validate_payload(
            verdict_type=VerdictKind(row.verdict_type),
            confidence=BusinessVerdictConfidenceLevel(row.confidence_level),
            readiness=VerdictReadinessStatus(row.readiness_snapshot),
            investigation_status=InvestigationStatus(inv.status),
            snap=snap,
            roles=[BusinessVerdictEvidenceRole(l.role) for l in links],
            conditions=_parse_conditions(row.conditions or []),
            risks=_parse_risks(row.critical_risks or []),
        )
        row.updated_at = utc_now()
        async with transactional(self._session):
            return await self._verdicts.update(row)

    async def submit_review(
        self,
        owner_id: UUID,
        project_id: UUID,
        verdict_id: UUID,
        actor_id: UUID,
        body: BusinessVerdictReviewRequest | None = None,
    ) -> BusinessVerdictTable | None:
        row = await self.get(owner_id, project_id, verdict_id)
        if row is None:
            return None
        previous = str(row.lifecycle_status)
        self._transition(row, BusinessVerdictLifecycleStatus.UNDER_REVIEW)
        row.submitted_by = actor_id
        row.submitted_at = utc_now()
        note = sanitize_text(body.note).strip() if body and body.note else None
        self._append_review_event(
            row,
            action="submit_review",
            actor_id=actor_id,
            note=note,
            previous=previous,
            new_status=BusinessVerdictLifecycleStatus.UNDER_REVIEW.value,
        )
        async with transactional(self._session):
            return await self._verdicts.update(row)

    async def approve(
        self,
        owner_id: UUID,
        project_id: UUID,
        verdict_id: UUID,
        actor_id: UUID,
        body: BusinessVerdictReviewRequest | None = None,
    ) -> BusinessVerdictTable | None:
        row = await self.get(owner_id, project_id, verdict_id)
        if row is None:
            return None
        previous = str(row.lifecycle_status)
        self._transition(row, BusinessVerdictLifecycleStatus.APPROVED)
        row.approved_by = actor_id
        row.approved_at = utc_now()
        note = sanitize_text(body.note).strip() if body and body.note else None
        self._append_review_event(
            row,
            action="approve",
            actor_id=actor_id,
            note=note,
            previous=previous,
            new_status=BusinessVerdictLifecycleStatus.APPROVED.value,
        )
        # Explicit firewall markers
        meta = dict(row.metadata_json or {})
        meta["creates_strategy"] = False
        meta["creates_execution_approval"] = False
        meta["creates_publication_approval"] = False
        meta["creates_agent_run"] = False
        row.metadata_json = meta
        async with transactional(self._session):
            return await self._verdicts.update(row)

    async def reject(
        self,
        owner_id: UUID,
        project_id: UUID,
        verdict_id: UUID,
        actor_id: UUID,
        body: BusinessVerdictReviewRequest,
    ) -> BusinessVerdictTable | None:
        row = await self.get(owner_id, project_id, verdict_id)
        if row is None:
            return None
        reason = sanitize_text(body.rejection_reason or body.note or "").strip()
        if not reason:
            raise InvalidStateError("invalid_transition")
        previous = str(row.lifecycle_status)
        self._transition(row, BusinessVerdictLifecycleStatus.REJECTED)
        row.rejection_reason = reason[:2000]
        self._append_review_event(
            row,
            action="reject",
            actor_id=actor_id,
            note=reason,
            previous=previous,
            new_status=BusinessVerdictLifecycleStatus.REJECTED.value,
        )
        async with transactional(self._session):
            return await self._verdicts.update(row)

    async def return_draft(
        self,
        owner_id: UUID,
        project_id: UUID,
        verdict_id: UUID,
        actor_id: UUID,
        body: BusinessVerdictReviewRequest | None = None,
    ) -> BusinessVerdictTable | None:
        row = await self.get(owner_id, project_id, verdict_id)
        if row is None:
            return None
        previous = str(row.lifecycle_status)
        self._transition(row, BusinessVerdictLifecycleStatus.DRAFT)
        note = sanitize_text(body.note).strip() if body and body.note else None
        self._append_review_event(
            row,
            action="return_draft",
            actor_id=actor_id,
            note=note,
            previous=previous,
            new_status=BusinessVerdictLifecycleStatus.DRAFT.value,
        )
        async with transactional(self._session):
            return await self._verdicts.update(row)

    async def archive(
        self,
        owner_id: UUID,
        project_id: UUID,
        verdict_id: UUID,
        actor_id: UUID,
        body: BusinessVerdictReviewRequest | None = None,
    ) -> BusinessVerdictTable | None:
        row = await self.get(owner_id, project_id, verdict_id)
        if row is None:
            return None
        previous = str(row.lifecycle_status)
        self._transition(row, BusinessVerdictLifecycleStatus.ARCHIVED)
        note = sanitize_text(body.note).strip() if body and body.note else None
        self._append_review_event(
            row,
            action="archive",
            actor_id=actor_id,
            note=note,
            previous=previous,
            new_status=BusinessVerdictLifecycleStatus.ARCHIVED.value,
        )
        async with transactional(self._session):
            return await self._verdicts.update(row)

    async def supersede(
        self,
        owner_id: UUID,
        project_id: UUID,
        verdict_id: UUID,
        actor_id: UUID,
        body: BusinessVerdictCreate,
    ) -> BusinessVerdictTable | None:
        prev = await self.get(owner_id, project_id, verdict_id)
        if prev is None:
            return None
        create_body = body.model_copy(update={"supersedes_verdict_id": prev.id})
        # create new draft then mark previous superseded if it was approved/rejected/draft
        new_row = await self.create(
            owner_id, project_id, prev.investigation_id, create_body
        )
        if new_row is None:
            return None
        previous = str(prev.lifecycle_status)
        # Reload prev after create commit
        prev = await self.get(owner_id, project_id, verdict_id)
        if prev is None:
            return new_row
        self._transition(prev, BusinessVerdictLifecycleStatus.SUPERSEDED)
        self._append_review_event(
            prev,
            action="superseded_by",
            actor_id=actor_id,
            note=str(new_row.id),
            previous=previous,
            new_status=BusinessVerdictLifecycleStatus.SUPERSEDED.value,
        )
        async with transactional(self._session):
            await self._verdicts.update(prev)
        return new_row

    def strategy_eligibility_for(
        self, row: BusinessVerdictTable
    ):
        return compute_strategy_eligibility(
            verdict_type=VerdictKind(row.verdict_type),
            lifecycle_status=BusinessVerdictLifecycleStatus(row.lifecycle_status),
            conditions=row.conditions or [],
        )
