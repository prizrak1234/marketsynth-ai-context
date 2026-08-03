"""Media Renderer service — Skills produce spec; connector executes after verification."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.connectors.contracts import (
    ConnectorExecutionRequest,
    ConnectorExecutionResultStatus,
    ConnectorPolicyOutcome,
    TimeoutPolicy,
)
from app.connectors.evidence import hash_payload
from app.connectors.higgsfield.adapter import HiggsfieldConnectorAdapter
from app.connectors.higgsfield.constants import (
    HIGGSFIELD_CONNECTOR_ID,
    HIGGSFIELD_CONNECTOR_VERIFICATION_STATUS,
    HIGGSFIELD_CONNECTOR_VERSION,
    MEDIA_OP_ASSET_FETCH,
    MEDIA_OP_IMAGE_GENERATE,
    MEDIA_OP_JOB_GET_STATUS,
    MEDIA_OP_VIDEO_GENERATE,
    RENDERER_UPSTREAM_SKILL_IDS,
)
from app.connectors.higgsfield.registry import (
    build_higgsfield_bindings,
    build_higgsfield_gateway,
    default_render_budget,
)
from app.connectors.higgsfield.sandbox.operation_mapping import load_operation_mapping
from app.core.config import Settings
from app.core.exceptions import InvalidStateError
from app.schemas.contracts import (
    MediaCanonicalOperation,
    MediaOperationMappingStatus,
    MediaProviderJobStatus,
    MediaRenderAssetType,
    MediaRendererReadiness,
    MediaRenderJobResponse,
    MediaRenderJobStatus,
    MediaRenderPlan,
    MediaRenderPlanStatus,
    MediaRenderRequest,
)


class MediaRendererService:
    """Orchestrates governed render calls to connector.higgsfield."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._gateway = build_higgsfield_gateway(settings)
        self._adapter = HiggsfieldConnectorAdapter(settings)
        self._mapping = load_operation_mapping()

    async def readiness(self) -> MediaRendererReadiness:
        descriptor = self._adapter.describe_connector()
        discovered = self._mapping.discovered_tool_names()
        sandbox_verified = self._settings.higgsfield_sandbox_verified
        return MediaRendererReadiness(
            enabled=self._settings.higgsfield_mcp_enabled,
            configured=self._settings.higgsfield_mcp_configured,
            connector_status=descriptor.status.value,
            connector_verification_status=(
                "sandbox_verified" if sandbox_verified else HIGGSFIELD_CONNECTOR_VERIFICATION_STATUS
            ),
            sandbox_verified=sandbox_verified,
            live_render_available=self._settings.higgsfield_mcp_live_calls_allowed,
            image_render_available=self._settings.higgsfield_mcp_enabled and sandbox_verified,
            video_render_available=(
                self._settings.higgsfield_mcp_enabled
                and sandbox_verified
                and self._settings.higgsfield_video_render_enabled
            ),
            requires_explicit_confirmation=True,
            requires_approval=True,
            detail_code="" if sandbox_verified else "sandbox_verification_required",
            detail_message=(
                "Dry-run returns local plan only. "
                "Live calls require sandbox verification + owner gate."
            ),
            discovered_mcp_tools=discovered,
        )

    async def render(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        body: MediaRenderRequest,
        live_allowed: bool = False,
    ) -> MediaRenderJobResponse:
        self._validate_upstream(body)

        canonical_op = (
            MEDIA_OP_VIDEO_GENERATE
            if body.spec.asset_type == MediaRenderAssetType.VIDEO
            else MEDIA_OP_IMAGE_GENERATE
        )
        if (
            canonical_op == MEDIA_OP_VIDEO_GENERATE
            and not self._settings.higgsfield_video_render_enabled
        ):
            raise InvalidStateError("higgsfield_video_render_disabled")

        if body.dry_run:
            return self._plan_only(body)

        self._validate_confirmation(body)
        if not live_allowed:
            raise InvalidStateError("connector_not_production_ready")
        if not self._settings.higgsfield_sandbox_verified:
            raise InvalidStateError("connector_not_production_ready")

        return await self._execute_live(
            owner_id=owner_id,
            project_id=project_id,
            tool_id=canonical_op,
            body=body,
        )

    async def get_status(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        job_id: str,
        upstream_skill_id: str,
        dry_run: bool = True,
        live_allowed: bool = False,
    ) -> MediaRenderJobResponse:
        body = MediaRenderRequest(
            spec=_status_probe_spec(),
            upstream_skill_id=upstream_skill_id,
            dry_run=dry_run,
        )
        if upstream_skill_id not in RENDERER_UPSTREAM_SKILL_IDS:
            raise InvalidStateError("upstream_skill_not_allowed")
        if dry_run:
            return self._plan_only(body, extra={"job_id": job_id})
        if not live_allowed:
            raise InvalidStateError("connector_not_production_ready")
        return await self._execute_live(
            owner_id=owner_id,
            project_id=project_id,
            tool_id=MEDIA_OP_JOB_GET_STATUS,
            body=body,
            extra_input={"job_id": job_id},
        )

    async def download_result(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        job_id: str,
        upstream_skill_id: str,
        dry_run: bool = True,
        live_allowed: bool = False,
    ) -> MediaRenderJobResponse:
        body = MediaRenderRequest(
            spec=_status_probe_spec(),
            upstream_skill_id=upstream_skill_id,
            dry_run=dry_run,
        )
        if upstream_skill_id not in RENDERER_UPSTREAM_SKILL_IDS:
            raise InvalidStateError("upstream_skill_not_allowed")
        if dry_run:
            return self._plan_only(body, extra={"job_id": job_id})
        if not live_allowed:
            raise InvalidStateError("connector_not_production_ready")
        return await self._execute_live(
            owner_id=owner_id,
            project_id=project_id,
            tool_id=MEDIA_OP_ASSET_FETCH,
            body=body,
            extra_input={"job_id": job_id},
        )

    def build_render_plan(
        self,
        body: MediaRenderRequest,
        *,
        extra: dict | None = None,
    ) -> MediaRenderPlan:
        canonical = _canonical_operation_for_spec(body.spec.asset_type)
        mapping_status = self._mapping.mapping_status(canonical.value)
        return MediaRenderPlan(
            status=MediaRenderPlanStatus.PLANNED_ONLY,
            spec_hash=hash_payload(body.spec.model_dump(mode="json")),
            canonical_operation=canonical,
            connector_requirements={
                "connector_id": HIGGSFIELD_CONNECTOR_ID,
                "credential_required": True,
                "explicit_confirmation_required": True,
                "approval_required": body.spec.approval_required,
                "sandbox_verified_required": True,
                "mcp_network_traffic": False,
                **(extra or {}),
            },
            policy_summary={
                "billing_sensitive": True,
                "estimated_cost_visibility": "unknown",
                "live_blocked_until_sandbox_verified": (
                    not self._settings.higgsfield_sandbox_verified
                ),
            },
            estimated_cost_visibility="unknown",
            provider_tool_mapping_status=MediaOperationMappingStatus(mapping_status),
            connector_verification_status=(
                "sandbox_verified"
                if self._settings.higgsfield_sandbox_verified
                else HIGGSFIELD_CONNECTOR_VERIFICATION_STATUS
            ),
        )

    def _plan_only(
        self,
        body: MediaRenderRequest,
        *,
        extra: dict | None = None,
    ) -> MediaRenderJobResponse:
        plan = self.build_render_plan(body, extra=extra)
        return MediaRenderJobResponse(
            job_id="",
            status=MediaRenderJobStatus.PLANNED_ONLY,
            asset_type=body.spec.asset_type,
            dry_run=True,
            paid_call_performed=False,
            detail_code="planned_only",
            detail_message="Local render plan only — zero MCP network traffic.",
            spec_hash=plan.spec_hash,
        )

    def _validate_upstream(self, body: MediaRenderRequest) -> None:
        if body.upstream_skill_id not in RENDERER_UPSTREAM_SKILL_IDS:
            raise InvalidStateError("upstream_skill_not_allowed")
        if not body.spec.prompt.strip():
            raise InvalidStateError("render_spec_incomplete")

    def _validate_confirmation(self, body: MediaRenderRequest) -> None:
        if not body.explicit_confirmation:
            raise InvalidStateError("explicit_confirmation_required")
        if body.spec.approval_required and not body.approval_reference:
            raise InvalidStateError("approval_reference_required")
        if not body.accept_unknown_cost:
            raise InvalidStateError("billing_cost_unknown_acceptance_required")

    async def _execute_live(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        tool_id: str,
        body: MediaRenderRequest,
        extra_input: dict | None = None,
    ) -> MediaRenderJobResponse:
        tenant_binding, project_binding, credential = build_higgsfield_bindings(
            tenant_id=owner_id,
            project_id=project_id,
            settings=self._settings,
        )
        accept_unknown_cost = body.accept_unknown_cost
        request = ConnectorExecutionRequest(
            request_id=uuid4(),
            correlation_id=uuid4(),
            tenant_id=owner_id,
            project_id=project_id,
            actor_id=owner_id,
            skill_id=body.upstream_skill_id,
            skill_version=body.upstream_skill_version,
            connector_id=HIGGSFIELD_CONNECTOR_ID,
            connector_version=HIGGSFIELD_CONNECTOR_VERSION,
            tool_id=tool_id,
            input_payload={
                "spec": body.spec.model_dump(mode="json"),
                **(extra_input or {}),
            },
            credential_binding_reference=credential,
            approval_reference=body.approval_reference,
            evidence_context={"render_spec_hash": hash_payload(body.spec.model_dump(mode="json"))},
            budget_context=default_render_budget(accept_unknown_cost=accept_unknown_cost),
            idempotency_key=body.idempotency_key,
            requested_at=datetime.now(UTC),
            timeout_policy=TimeoutPolicy(timeout_seconds=self._settings.higgsfield_mcp_timeout_seconds),
            dry_run=False,
            runtime_id="media_renderer",
            skill_allowed_tools=(tool_id,),
        )

        _descriptor, tool, decision = self._gateway.evaluate_policy(
            request,
            tenant_binding=tenant_binding,
            project_binding=project_binding,
        )
        if decision.outcome == ConnectorPolicyOutcome.DENY:
            raise InvalidStateError(decision.reason or "connector_policy_denied")
        if decision.outcome in {
            ConnectorPolicyOutcome.REQUIRE_APPROVAL,
            ConnectorPolicyOutcome.REQUIRE_ADDITIONAL_CONTEXT,
        }:
            return MediaRenderJobResponse(
                job_id="",
                status=MediaRenderJobStatus.APPROVAL_REQUIRED,
                asset_type=body.spec.asset_type,
                dry_run=False,
                detail_code=decision.reason or "approval_required",
                spec_hash=hash_payload(body.spec.model_dump(mode="json")),
            )

        exec_result = await self._adapter.execute_tool_async(request)
        return self._to_job_response(exec_result, body, dry_run=False)

    def _to_job_response(
        self,
        result,
        body: MediaRenderRequest,
        *,
        dry_run: bool,
    ) -> MediaRenderJobResponse:
        status = MediaRenderJobStatus.FAILED
        if result.status == ConnectorExecutionResultStatus.SUCCEEDED:
            provider_status = str(result.output_payload.get("status") or "submitted")
            status = _map_provider_status(provider_status)
        elif result.status == ConnectorExecutionResultStatus.APPROVAL_REQUIRED:
            status = MediaRenderJobStatus.APPROVAL_REQUIRED
        elif result.status == ConnectorExecutionResultStatus.REJECTED_BY_POLICY:
            status = MediaRenderJobStatus.BLOCKED

        evidence_id = None
        if result.evidence_descriptor is not None:
            evidence_id = result.evidence_descriptor.evidence_id

        return MediaRenderJobResponse(
            job_id=str(result.output_payload.get("job_id") or result.external_reference_id or ""),
            status=status,
            asset_type=body.spec.asset_type,
            dry_run=dry_run,
            paid_call_performed=(
                not dry_run and result.status == ConnectorExecutionResultStatus.SUCCEEDED
            ),
            result_url=result.output_payload.get("result_url"),
            mime_type=result.output_payload.get("mime_type"),
            external_reference_id=result.external_reference_id,
            detail_code=str(result.error.code if result.error else ""),
            detail_message=str(result.error.message if result.error else ""),
            spec_hash=hash_payload(body.spec.model_dump(mode="json")),
            evidence_id=evidence_id,
        )


def _canonical_operation_for_spec(asset_type: MediaRenderAssetType) -> MediaCanonicalOperation:
    if asset_type == MediaRenderAssetType.VIDEO:
        return MediaCanonicalOperation.VIDEO_GENERATE
    return MediaCanonicalOperation.IMAGE_GENERATE


def _map_provider_status(raw: str) -> MediaRenderJobStatus:
    normalized = raw.lower()
    mapping = {
        MediaProviderJobStatus.SUCCEEDED.value: MediaRenderJobStatus.SUCCEEDED,
        MediaProviderJobStatus.FAILED.value: MediaRenderJobStatus.FAILED,
        MediaProviderJobStatus.RUNNING.value: MediaRenderJobStatus.RUNNING,
        MediaProviderJobStatus.QUEUED.value: MediaRenderJobStatus.QUEUED,
        MediaProviderJobStatus.SUBMITTED.value: MediaRenderJobStatus.QUEUED,
        "done": MediaRenderJobStatus.SUCCEEDED,
        "completed": MediaRenderJobStatus.SUCCEEDED,
        "success": MediaRenderJobStatus.SUCCEEDED,
        "error": MediaRenderJobStatus.FAILED,
        "processing": MediaRenderJobStatus.RUNNING,
        "in_progress": MediaRenderJobStatus.RUNNING,
    }
    if normalized in mapping:
        return mapping[normalized]
    if normalized == MediaProviderJobStatus.UNKNOWN.value:
        return MediaRenderJobStatus.QUEUED
    return MediaRenderJobStatus.QUEUED


def _status_probe_spec():
    from app.schemas.contracts import MediaRenderSpec

    return MediaRenderSpec(
        asset_type=MediaRenderAssetType.IMAGE,
        style="probe",
        prompt="status probe",
        approval_required=False,
    )
