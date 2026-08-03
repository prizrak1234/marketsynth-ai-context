"""Offer Builder orchestration service (PRODUCT-01)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.evidence import hash_payload
from app.core.config import Settings
from app.core.exceptions import InvalidStateError, NotFoundError
from app.db.base import utc_now
from app.db.models.commercial_upstream_snapshot import CommercialUpstreamSnapshotTable
from app.db.models.launch_pack_request import LaunchPackRequestTable
from app.db.models.offer_artifact import (
    OfferArtifactTable,
    OfferArtifactVersionTable,
    OfferReviewEventTable,
)
from app.db.repositories.launch_pack_requests import LaunchPackRequestRepository
from app.db.repositories.offer_artifacts import OfferArtifactRepository
from app.product.offer_builder.adapter import generate_offer_output
from app.product.offer_builder.contracts import (
    PACKAGE_HASH,
    SKILL_ID,
    SKILL_VERSION,
    OfferGenerationContext,
    UpstreamBundle,
)
from app.product.offer_builder.eligibility import (
    BLOCKER_TO_WORKFLOW,
    evaluate_eligibility,
    map_biv_verdict_to_mv,
)
from app.product.offer_builder.input_builder import build_skill_input, build_upstream_from_biv
from app.product.offer_builder.lineage import build_lineage_metadata
from app.product.offer_builder.output_validation import (
    validate_output_schema,
    validate_output_semantics,
)
from app.product.offer_builder.transitions import (
    assert_approve_allowed,
    assert_not_finalized,
    assert_review_allowed,
    assert_workflow_transition,
)
from app.schemas.contracts import (
    BusinessIdeaValidationProjectHydration,
    LaunchPackOfferWorkflowStatus,
    LaunchPackRequestStatus,
    OfferApprovalStatus,
    OfferArtifactDetail,
    OfferArtifactStatus,
    OfferGenerateRequest,
    OfferGenerateResponse,
    OfferRecoverResponse,
    OfferReviewDecisionCreate,
    OfferRevisionRequestCreate,
    OfferVersionHistoryItem,
    UpstreamSnapshotSummary,
    UpstreamSourceMode,
)
from app.services.business_idea_validation_service import BusinessIdeaValidationService
from app.services.transaction import transactional


class OfferBuilderService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._offers = OfferArtifactRepository(session)
        self._launch_packs = LaunchPackRequestRepository(session)
        self._biv = BusinessIdeaValidationService(session, settings)

    async def generate_for_launch_pack(
        self,
        owner_id: UUID,
        project_id: UUID,
        launch_pack_id: UUID,
        body: OfferGenerateRequest,
    ) -> OfferGenerateResponse:
        if not body.idempotency_key.strip():
            raise InvalidStateError("idempotency_key_required")

        existing = await self._offers.get_by_idempotency(owner_id, body.idempotency_key)
        if existing is not None:
            launch = await self._launch_packs.get_by_id(owner_id, launch_pack_id)
            detail = await self._detail_for_artifact(owner_id, existing)
            return OfferGenerateResponse(
                offer=detail,
                launch_pack_workflow_status=_workflow_from_launch(launch),
                lineage_reused=True,
            )

        launch = await self._require_launch_pack(owner_id, project_id, launch_pack_id)
        if launch.status != LaunchPackRequestStatus.REQUESTED:
            raise InvalidStateError("launch_pack_not_eligible")

        validation = await self._require_validation(owner_id, project_id)
        mv_verdict = map_biv_verdict_to_mv(validation.output.verdict)
        upstream = build_upstream_from_biv(
            owner_id=owner_id,
            project_id=project_id,
            output=validation.output,
            accepted_conditions=list(launch.accepted_conditions or []),
            mv_verdict=mv_verdict,
        )
        eligibility = evaluate_eligibility(biv_verdict=validation.output.verdict, upstream=upstream)
        if not eligibility.allowed:
            workflow_status = BLOCKER_TO_WORKFLOW.get(
                eligibility.blocker_code or "",
                LaunchPackOfferWorkflowStatus.BLOCKED_BY_VERDICT.value,
            )
            launch.offer_workflow_status = workflow_status
            launch.blocker_codes = [eligibility.blocker_code or "blocked_by_verdict"]
            launch.updated_at = utc_now()
            return OfferGenerateResponse(
                offer=None,
                launch_pack_workflow_status=LaunchPackOfferWorkflowStatus(launch.offer_workflow_status),
                blocker_code=eligibility.blocker_code,
            )

        existing_offer = await self._offers.get_by_launch_pack(owner_id, launch_pack_id)
        if existing_offer is not None:
            detail = await self._detail_for_artifact(owner_id, existing_offer)
            return OfferGenerateResponse(
                offer=detail,
                launch_pack_workflow_status=LaunchPackOfferWorkflowStatus.BUILDING_OFFER,
                lineage_reused=True,
            )

        async with transactional(self._session):
            launch = await self._offers.get_launch_pack_for_update(owner_id, launch_pack_id)
            if launch is None or launch.project_id != project_id:
                raise NotFoundError("launch_pack_not_found")
            if launch.status != LaunchPackRequestStatus.REQUESTED:
                raise InvalidStateError("launch_pack_not_eligible")

            existing_offer = await self._offers.get_by_launch_pack(owner_id, launch_pack_id)
            if existing_offer is not None:
                detail = await self._detail_for_artifact(owner_id, existing_offer)
                return OfferGenerateResponse(
                    offer=detail,
                    launch_pack_workflow_status=LaunchPackOfferWorkflowStatus.BUILDING_OFFER,
                    lineage_reused=True,
                )

            current_workflow = _parse_workflow(launch.offer_workflow_status)
            assert_workflow_transition(
                current_workflow,
                LaunchPackOfferWorkflowStatus.BUILDING_OFFER,
            )
            launch.offer_workflow_status = LaunchPackOfferWorkflowStatus.BUILDING_OFFER.value
            launch.updated_at = utc_now()

            now = utc_now()
            artifact = OfferArtifactTable(
                owner_id=owner_id,
                tenant_id=owner_id,
                project_id=project_id,
                launch_pack_request_id=launch_pack_id,
                business_verdict_id=launch.business_verdict_id,
                skill_id=SKILL_ID,
                skill_version=SKILL_VERSION,
                skill_package_hash=PACKAGE_HASH,
                approval_status=OfferApprovalStatus.PENDING,
                generation_idempotency_key=body.idempotency_key,
                created_at=now,
                updated_at=now,
            )
            await self._persist_upstream_snapshots(
                owner_id,
                project_id,
                launch_pack_id,
                upstream,
                biv_id=validation.output.business_verdict_id,
            )
            artifact = await self._offers.create_artifact(artifact)
            launch.offer_artifact_id = artifact.id
            launch.generation_idempotency_key = body.idempotency_key

            context = OfferGenerationContext(
                owner_id=owner_id,
                project_id=project_id,
                launch_pack_request_id=launch_pack_id,
                business_verdict_id=launch.business_verdict_id,
                user_request_id=launch.user_request_id,
                upstream=upstream,
                launch_objective=validation.user_request_text[:200],
            )
            try:
                output = generate_offer_output(context)
                validate_output_schema(output)
                semantic_errors = validate_output_semantics(
                    output,
                    mv_verdict=mv_verdict,
                    substantiated_claim_ids=set(upstream.substantiated_claim_ids),
                )
                if semantic_errors:
                    raise InvalidStateError("offer_output_semantic_invalid")

                skill_input = build_skill_input(upstream)
                input_hash = hash_payload(skill_input)
                preferred = _preferred_candidate(output)
                version = OfferArtifactVersionTable(
                    offer_artifact_id=artifact.id,
                    version_number=1,
                    status=OfferArtifactStatus.REVIEW_REQUIRED,
                    input_snapshot_hash=input_hash,
                    output_hash=output["output_hash"],
                    output_json=output,
                    offer_title=preferred.get("offer_name", ""),
                    offer_summary=preferred.get("offer_promise", ""),
                    lineage_metadata=build_lineage_metadata(
                        project_id=project_id,
                        launch_pack_request_id=launch_pack_id,
                        business_verdict_id=launch.business_verdict_id,
                        upstream_refs=_upstream_refs(upstream),
                        generation_request_id=artifact.id,
                        version_number=1,
                    ),
                    created_at=now,
                )
                version = await self._offers.create_version(version)
                artifact.current_version_id = version.id
                artifact.updated_at = utc_now()
                launch.offer_workflow_status = (
                    LaunchPackOfferWorkflowStatus.OFFER_REVIEW_REQUIRED.value
                )
                launch.blocker_codes = []
                launch.status = LaunchPackRequestStatus.IN_PROGRESS
            except Exception as exc:  # noqa: BLE001
                launch.offer_workflow_status = (
                    LaunchPackOfferWorkflowStatus.OFFER_GENERATION_FAILED.value
                )
                launch.blocker_codes = ["offer_generation_failed"]
                raise InvalidStateError("offer_generation_failed") from exc

        detail = await self._detail_for_artifact(owner_id, artifact)
        return OfferGenerateResponse(
            offer=detail,
            launch_pack_workflow_status=LaunchPackOfferWorkflowStatus.OFFER_REVIEW_REQUIRED,
        )

    async def get_offer(
        self,
        owner_id: UUID,
        offer_id: UUID,
    ) -> OfferArtifactDetail:
        artifact = await self._offers.get_by_id(owner_id, offer_id)
        if artifact is None:
            raise NotFoundError("offer_not_found")
        return await self._detail_for_artifact(owner_id, artifact)

    async def list_versions(
        self,
        owner_id: UUID,
        offer_id: UUID,
    ) -> list[OfferVersionHistoryItem]:
        artifact = await self._offers.get_by_id(owner_id, offer_id)
        if artifact is None:
            raise NotFoundError("offer_not_found")
        versions = await self._offers.list_versions(artifact.id)
        return [
            OfferVersionHistoryItem(
                id=v.id,
                version_number=v.version_number,
                status=v.status,
                output_hash=v.output_hash,
                offer_title=v.offer_title,
                created_at=v.created_at,
                approval_status=artifact.approval_status,
            )
            for v in versions
        ]

    async def approve(
        self,
        owner_id: UUID,
        offer_id: UUID,
        body: OfferReviewDecisionCreate,
    ) -> OfferArtifactDetail:
        async with transactional(self._session):
            artifact = await self._offers.get_by_id_for_update(owner_id, offer_id)
            if artifact is None:
                raise NotFoundError("offer_not_found")
            version = await self._offers.get_current_version(artifact)
            if version is None:
                raise NotFoundError("offer_not_found")

            if (
                artifact.approval_status == OfferApprovalStatus.APPROVED
                and version.output_hash == body.expected_output_hash
            ):
                return await self._detail_for_artifact(owner_id, artifact)

            if version.output_hash != body.expected_output_hash:
                raise InvalidStateError("stale_approval_hash")

            assert_approve_allowed(artifact.approval_status)
            assert_review_allowed(
                version_status=version.status,
                approval_status=artifact.approval_status,
            )

            launch = await self._launch_packs.get_by_id(owner_id, artifact.launch_pack_request_id)
            if launch is not None:
                assert_workflow_transition(
                    _parse_workflow(launch.offer_workflow_status),
                    LaunchPackOfferWorkflowStatus.OFFER_APPROVED,
                )

            now = utc_now()
            artifact.approval_status = OfferApprovalStatus.APPROVED
            artifact.approved_at = now
            artifact.updated_at = now
            version.status = OfferArtifactStatus.APPROVED
            await self._offers.create_review_event(
                OfferReviewEventTable(
                    offer_artifact_id=artifact.id,
                    offer_version_id=version.id,
                    reviewer_id=owner_id,
                    decision="approved",
                    expected_output_hash=body.expected_output_hash,
                    comment=body.comment,
                    created_at=now,
                )
            )
            if launch is not None:
                launch.offer_workflow_status = LaunchPackOfferWorkflowStatus.OFFER_APPROVED.value
                launch.updated_at = now

        return await self._detail_for_artifact(owner_id, artifact)

    async def reject(
        self,
        owner_id: UUID,
        offer_id: UUID,
        body: OfferReviewDecisionCreate,
    ) -> OfferArtifactDetail:
        async with transactional(self._session):
            artifact = await self._offers.get_by_id_for_update(owner_id, offer_id)
            if artifact is None:
                raise NotFoundError("offer_not_found")
            version = await self._offers.get_current_version(artifact)
            if version is None or version.output_hash != body.expected_output_hash:
                raise InvalidStateError("stale_approval_hash")

            assert_not_finalized(artifact.approval_status)
            assert_review_allowed(
                version_status=version.status,
                approval_status=artifact.approval_status,
            )

            launch = await self._launch_packs.get_by_id(owner_id, artifact.launch_pack_request_id)
            if launch is not None:
                assert_workflow_transition(
                    _parse_workflow(launch.offer_workflow_status),
                    LaunchPackOfferWorkflowStatus.OFFER_REJECTED,
                )

            now = utc_now()
            artifact.approval_status = OfferApprovalStatus.REJECTED
            artifact.updated_at = now
            version.status = OfferArtifactStatus.REJECTED
            await self._offers.create_review_event(
                OfferReviewEventTable(
                    offer_artifact_id=artifact.id,
                    offer_version_id=version.id,
                    reviewer_id=owner_id,
                    decision="rejected",
                    expected_output_hash=body.expected_output_hash,
                    comment=body.comment,
                    created_at=now,
                )
            )
            if launch is not None:
                launch.offer_workflow_status = LaunchPackOfferWorkflowStatus.OFFER_REJECTED.value
                launch.updated_at = now

        return await self._detail_for_artifact(owner_id, artifact)

    async def request_revision(
        self,
        owner_id: UUID,
        offer_id: UUID,
        body: OfferRevisionRequestCreate,
    ) -> OfferArtifactDetail:
        preview = await self._offers.get_by_id(owner_id, offer_id)
        if preview is None:
            raise NotFoundError("offer_not_found")
        validation = await self._biv.get_project_hydration(owner_id, preview.project_id)
        if validation is None:
            raise NotFoundError("validation_not_found")

        async with transactional(self._session):
            artifact = await self._offers.get_by_id_for_update(owner_id, offer_id)
            if artifact is None:
                raise NotFoundError("offer_not_found")
            version = await self._offers.get_current_version(artifact)
            if version is None or version.output_hash != body.expected_output_hash:
                raise InvalidStateError("stale_approval_hash")

            assert_not_finalized(artifact.approval_status)
            assert_review_allowed(
                version_status=version.status,
                approval_status=artifact.approval_status,
            )

            now = utc_now()
            launch = await self._launch_packs.get_by_id(owner_id, artifact.launch_pack_request_id)
            if launch is not None:
                assert_workflow_transition(
                    _parse_workflow(launch.offer_workflow_status),
                    LaunchPackOfferWorkflowStatus.REVISION_REQUIRED,
                )
                launch.offer_workflow_status = (
                    LaunchPackOfferWorkflowStatus.REVISION_REQUIRED.value
                )
                launch.updated_at = now

            mv_verdict = map_biv_verdict_to_mv(validation.output.verdict)
            upstream = build_upstream_from_biv(
                owner_id=owner_id,
                project_id=artifact.project_id,
                output=validation.output,
                accepted_conditions=list(launch.accepted_conditions or []) if launch else [],
                mv_verdict=mv_verdict,
            )

            artifact.approval_status = OfferApprovalStatus.REVISION_REQUESTED
            artifact.updated_at = now
            version.status = OfferArtifactStatus.REVISION_REQUESTED
            await self._offers.create_review_event(
                OfferReviewEventTable(
                    offer_artifact_id=artifact.id,
                    offer_version_id=version.id,
                    reviewer_id=owner_id,
                    decision="revision_requested",
                    expected_output_hash=body.expected_output_hash,
                    comment=body.comment,
                    created_at=now,
                )
            )

            context = OfferGenerationContext(
                owner_id=owner_id,
                project_id=artifact.project_id,
                launch_pack_request_id=artifact.launch_pack_request_id,
                business_verdict_id=artifact.business_verdict_id,
                user_request_id=launch.user_request_id if launch else validation.user_request_id,
                upstream=upstream,
                launch_objective=validation.user_request_text[:200],
            )
            output = generate_offer_output(context)
            validate_output_schema(output)
            semantic_errors = validate_output_semantics(
                output,
                mv_verdict=mv_verdict,
                substantiated_claim_ids=set(upstream.substantiated_claim_ids),
            )
            if semantic_errors:
                raise InvalidStateError("offer_output_semantic_invalid")

            if launch is not None:
                assert_workflow_transition(
                    _parse_workflow(launch.offer_workflow_status),
                    LaunchPackOfferWorkflowStatus.BUILDING_OFFER,
                )
                launch.offer_workflow_status = (
                    LaunchPackOfferWorkflowStatus.BUILDING_OFFER.value
                )
                launch.updated_at = now

            skill_input = build_skill_input(upstream)
            input_hash = hash_payload(skill_input)
            preferred = _preferred_candidate(output)
            new_version = OfferArtifactVersionTable(
                offer_artifact_id=artifact.id,
                version_number=version.version_number + 1,
                status=OfferArtifactStatus.REVIEW_REQUIRED,
                input_snapshot_hash=input_hash,
                output_hash=output["output_hash"],
                output_json=output,
                offer_title=preferred.get("offer_name", ""),
                offer_summary=preferred.get("offer_promise", ""),
                revision_of_id=version.id,
                lineage_metadata=build_lineage_metadata(
                    project_id=artifact.project_id,
                    launch_pack_request_id=artifact.launch_pack_request_id,
                    business_verdict_id=artifact.business_verdict_id,
                    upstream_refs=_upstream_refs(upstream),
                    generation_request_id=artifact.id,
                    version_number=version.version_number + 1,
                    revision_of_id=version.id,
                ),
                created_at=now,
            )
            new_version = await self._offers.create_version(new_version)
            artifact.current_version_id = new_version.id
            artifact.approval_status = OfferApprovalStatus.PENDING
            artifact.updated_at = now
            if launch is not None:
                launch.offer_workflow_status = (
                    LaunchPackOfferWorkflowStatus.OFFER_REVIEW_REQUIRED.value
                )
                launch.updated_at = now

        return await self._detail_for_artifact(owner_id, artifact)

    async def recover(
        self,
        owner_id: UUID,
        offer_id: UUID,
    ) -> OfferRecoverResponse:
        async with transactional(self._session):
            artifact = await self._offers.get_by_id_for_update(owner_id, offer_id)
            if artifact is None:
                raise NotFoundError("offer_not_found")
            launch = await self._launch_packs.get_by_id(owner_id, artifact.launch_pack_request_id)
            version = await self._offers.get_current_version(artifact)
            recovered_from = launch.offer_workflow_status if launch else "unknown"

            if launch is None:
                raise NotFoundError("launch_pack_not_found")

            if launch.offer_workflow_status == LaunchPackOfferWorkflowStatus.BUILDING_OFFER.value:
                if version is None:
                    launch.offer_workflow_status = (
                        LaunchPackOfferWorkflowStatus.OFFER_GENERATION_FAILED.value
                    )
                    launch.blocker_codes = ["offer_generation_interrupted"]
                else:
                    launch.offer_workflow_status = (
                        LaunchPackOfferWorkflowStatus.OFFER_REVIEW_REQUIRED.value
                    )
                    launch.blocker_codes = []
                launch.updated_at = utc_now()
            elif (
                launch.offer_workflow_status
                == LaunchPackOfferWorkflowStatus.OFFER_GENERATION_FAILED.value
                and version is not None
            ):
                launch.offer_workflow_status = (
                    LaunchPackOfferWorkflowStatus.OFFER_REVIEW_REQUIRED.value
                )
                launch.blocker_codes = []
                launch.updated_at = utc_now()
            else:
                raise InvalidStateError("offer_recovery_not_needed")

        detail = await self._detail_for_artifact(owner_id, artifact)
        return OfferRecoverResponse(
            offer=detail,
            recovered_from=recovered_from,
            launch_pack_workflow_status=_parse_workflow(launch.offer_workflow_status),
        )

    async def get_offer_for_launch_pack(
        self,
        owner_id: UUID,
        launch_pack_id: UUID,
    ) -> OfferArtifactDetail | None:
        artifact = await self._offers.get_by_launch_pack(owner_id, launch_pack_id)
        if artifact is None:
            return None
        return await self._detail_for_artifact(owner_id, artifact)

    async def _detail_for_artifact(
        self,
        owner_id: UUID,
        artifact: OfferArtifactTable,
    ) -> OfferArtifactDetail:
        version = await self._offers.get_current_version(artifact)
        if version is None:
            raise NotFoundError("offer_not_found")
        output = version.output_json
        preferred = _preferred_candidate(output)
        return OfferArtifactDetail(
            id=artifact.id,
            launch_pack_request_id=artifact.launch_pack_request_id,
            project_id=artifact.project_id,
            skill_id=artifact.skill_id,
            skill_version=artifact.skill_version,
            status=version.status,
            approval_status=artifact.approval_status,
            version_number=version.version_number,
            offer_title=version.offer_title or preferred.get("offer_name", ""),
            offer_summary=version.offer_summary or preferred.get("offer_promise", ""),
            human_review_required=bool(output.get("human_approval_required", True)),
            output_hash=version.output_hash,
            blocker_code=version.blocker_code,
            created_at=artifact.created_at,
            updated_at=artifact.updated_at,
            approved_at=artifact.approved_at,
            problem_statement=preferred.get("primary_customer_problem", ""),
            promised_outcome=preferred.get("desired_outcome", ""),
            value_proposition=(
                output.get("source_positioning_reference", {}).get("value_proposition", "")
                or preferred.get("offer_promise", "")
            ),
            offer_components=(
                list(preferred.get("product_components", []))
                + list(preferred.get("service_components", []))
            ),
            proof_references=list(preferred.get("proof_elements", [])),
            objection_handling=list(output.get("objection_handling_plan", [])),
            conditions=[
                c.get("text", "")
                for c in output.get("inherited_conditions", [])
                if isinstance(c, dict)
            ],
            limitations=list(output.get("evidence_gaps", [])),
            cta=preferred.get("call_to_action", "Связаться для старта пилота"),
            unsupported_claims=list(output.get("unsupported_claims_excluded", [])),
            evidence_gaps=list(output.get("evidence_gaps", [])),
            target_segment_ids=list(output.get("selected_segment_ids", [])),
            preferred_offer_id=output.get("preferred_offer_id"),
            offer_readiness=str(output.get("offer_readiness", "")),
            revision_of_id=version.revision_of_id,
            lineage_metadata=dict(version.lineage_metadata or {}),
            upstream_sources=await self._upstream_summaries(artifact.launch_pack_request_id),
        )

    async def _upstream_summaries(
        self,
        launch_pack_request_id: UUID,
    ) -> list[UpstreamSnapshotSummary]:
        rows = await self._offers.list_upstream_snapshots(launch_pack_request_id)
        summaries: list[UpstreamSnapshotSummary] = []
        for row in rows:
            try:
                mode = UpstreamSourceMode(row.source_mode)
            except ValueError:
                mode = UpstreamSourceMode.BRIDGED_BIV_SNAPSHOT
            summaries.append(
                UpstreamSnapshotSummary(
                    artifact_type=row.artifact_type,
                    source_skill_id=row.source_skill_id,
                    source_skill_version=row.source_skill_version,
                    source_mode=mode,
                    bridge_version=row.bridge_version,
                    source_biv_id=row.source_biv_id,
                    source_biv_hash=row.source_biv_hash,
                    generated_from_fields=[str(x) for x in (row.generated_from_fields or [])],
                    limitations=[str(x) for x in (row.limitations or [])],
                    replacement_required=bool(row.replacement_required),
                    source_output_hash=row.source_output_hash,
                )
            )
        return summaries

    async def _persist_upstream_snapshots(
        self,
        owner_id: UUID,
        project_id: UUID,
        launch_pack_id: UUID,
        upstream: UpstreamBundle,
        *,
        biv_id: UUID | None = None,
    ) -> None:
        now = utc_now()
        for artifact_type, entry in (
            ("market_validation", upstream.market_validation),
            ("positioning", upstream.positioning),
            ("claim_substantiation", upstream.claim_substantiation),
            ("cim", upstream.cim),
        ):
            source_mode = entry.get(
                "source_mode",
                UpstreamSourceMode.BRIDGED_BIV_SNAPSHOT.value,
            )
            self._session.add(
                CommercialUpstreamSnapshotTable(
                    owner_id=owner_id,
                    tenant_id=owner_id,
                    project_id=project_id,
                    launch_pack_request_id=launch_pack_id,
                    artifact_type=artifact_type,
                    source_skill_id=entry.get("source_skill_id", "derived"),
                    source_skill_version=entry.get("source_skill_version", "0.1.0"),
                    source_package_hash=PACKAGE_HASH,
                    source_output_hash=entry.get("source_output_hash", ""),
                    source_mode=UpstreamSourceMode(source_mode),
                    bridge_version=entry.get("bridge_version"),
                    source_biv_id=biv_id,
                    source_biv_hash=entry.get("source_biv_hash"),
                    generated_from_fields=entry.get("generated_from_fields", []),
                    limitations=entry.get("limitations", []),
                    replacement_required=bool(entry.get("replacement_required", True)),
                    payload=entry,
                    created_at=now,
                )
            )

    async def _require_launch_pack(
        self,
        owner_id: UUID,
        project_id: UUID,
        launch_pack_id: UUID,
    ) -> LaunchPackRequestTable:
        launch = await self._launch_packs.get_by_id(owner_id, launch_pack_id)
        if launch is None or launch.project_id != project_id:
            raise NotFoundError("launch_pack_not_found")
        return launch

    async def _require_validation(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> BusinessIdeaValidationProjectHydration:
        validation = await self._biv.get_project_hydration(owner_id, project_id)
        if validation is None:
            raise NotFoundError("validation_not_found")
        return validation


def _preferred_candidate(output: dict[str, Any]) -> dict[str, Any]:
    preferred_id = output.get("preferred_offer_id")
    for offer in output.get("offer_candidates", []):
        if offer.get("offer_id") == preferred_id:
            return offer
    candidates = output.get("offer_candidates") or []
    return candidates[0] if candidates else {}


def _upstream_refs(upstream: UpstreamBundle) -> dict[str, Any]:
    return {
        "market_validation": upstream.market_validation.get("artifact_id"),
        "positioning": upstream.positioning.get("artifact_id"),
        "claims": upstream.claim_substantiation.get("artifact_id"),
        "cim": upstream.cim.get("artifact_id"),
    }


def _workflow_from_launch(launch: LaunchPackRequestTable | None) -> LaunchPackOfferWorkflowStatus:
    if launch is None:
        return LaunchPackOfferWorkflowStatus.NOT_STARTED
    return _parse_workflow(launch.offer_workflow_status)


def _parse_workflow(raw: str) -> LaunchPackOfferWorkflowStatus:
    try:
        return LaunchPackOfferWorkflowStatus(raw)
    except ValueError:
        return LaunchPackOfferWorkflowStatus.REQUESTED
