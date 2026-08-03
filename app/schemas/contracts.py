"""
Canonical data contracts for Marketsynth (legacy package name: BotFazer).

All domains (users, agents, memory, marketing) must use these models
before persisting or passing data between services.

Architecture v2.0 Phase V2.1 adds compatibility enums/models below that are
not yet wired into runtime APIs Р Р†Р вЂљРІР‚Сњ safe additive stubs only.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class AgentStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class AgentType(StrEnum):
    GENERAL = "general"
    PROGRAMMER = "programmer"
    MEDIA = "media"
    STRATEGIST = "strategist"
    RESEARCHER = "researcher"
    COPYWRITER = "copywriter"
    CONTENT_PLANNER = "content_planner"
    CRITIC = "critic"
    ANALYST = "analyst"
    ORCHESTRATOR = "orchestrator"


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class MemoryLayer(StrEnum):
    L1_SESSION = "l1_session"
    L2_PROJECT = "l2_project"
    L3_USER = "l3_user"
    L4_GLOBAL = "l4_global"


class ContentAssetType(StrEnum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"


class UserRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class OnboardingStep(StrEnum):
    """First-run onboarding milestones (Phase AI.86)."""

    PROJECT_CREATED = "project_created"
    AGENTS_SEEDED = "agents_seeded"
    DEMO_SEEDED = "demo_seeded"
    FIRST_CHAT_DONE = "first_chat_done"
    FIRST_ASSET_CREATED = "first_asset_created"
    FIRST_PUBLICATION_JOB_CREATED = "first_publication_job_created"


# Steps that may be marked complete via POST /me/onboarding/complete-step (UI-only).
ONBOARDING_MANUAL_STEPS: frozenset[OnboardingStep] = frozenset(
    {OnboardingStep.DEMO_SEEDED},
)


class BetaAccessStatus(StrEnum):
    """Closed-beta invite gate (Phase AI.96)."""

    PENDING = "pending"
    APPROVED = "approved"
    BLOCKED = "blocked"


class BetaFeedbackSource(StrEnum):
    ONBOARDING = "onboarding"
    CHAT = "chat"
    MARKETING_PIPELINE = "marketing_pipeline"
    CONTENT = "content"
    MEDIA = "media"
    PUBLISHING = "publishing"
    OTHER = "other"


class BetaFeedbackSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKER = "blocker"


class BetaFeedbackStatus(StrEnum):
    OPEN = "open"
    TRIAGED = "triaged"
    RESOLVED = "resolved"
    ARCHIVED = "archived"


class BetaFeedbackReport(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID | None = None
    source: BetaFeedbackSource = BetaFeedbackSource.OTHER
    severity: BetaFeedbackSeverity = BetaFeedbackSeverity.MEDIUM
    status: BetaFeedbackStatus = BetaFeedbackStatus.OPEN
    title: str
    description: str
    safe_context: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class User(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    telegram_id: int | None = None
    email: str | None = None
    display_name: str | None = None
    role: UserRole = UserRole.MEMBER
    is_active: bool = True
    beta_access_status: BetaAccessStatus = BetaAccessStatus.PENDING
    beta_notes: str | None = None
    last_login_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class BrowserSessionStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class BrowserSession(BaseModel):
    """Pilot browser session metadata Р Р†Р вЂљРІР‚Сњ never includes raw token."""

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    status: BrowserSessionStatus = BrowserSessionStatus.ACTIVE
    purpose: str = "pilot_browser"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    last_seen_at: datetime | None = None
    revoked_at: datetime | None = None


class ApiKey(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    name: str
    key_prefix: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None


class Project(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    name: str
    description: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AgentCapability(BaseModel):
    name: str
    description: str | None = None
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)


class Agent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    owner_id: UUID
    type: AgentType
    name: str
    description: str | None = None
    status: AgentStatus = AgentStatus.DRAFT
    config: dict[str, Any] = Field(default_factory=dict)
    capabilities: list[AgentCapability] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AgentRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentRun(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    task_id: UUID | None = None
    agent_id: UUID
    parent_agent_run_id: UUID | None = None
    status: AgentRunStatus = AgentRunStatus.QUEUED
    input_payload: dict[str, Any] = Field(default_factory=dict)
    output_payload: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Task(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    agent_id: UUID | None = None
    title: str
    status: TaskStatus = TaskStatus.PENDING
    input_payload: dict[str, Any] = Field(default_factory=dict)
    output_payload: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None


class UserRequestStatus(StrEnum):
    """Home conversational intake lifecycle (Phase H1). Not TaskStatus / AgentRunStatus."""

    SUBMITTED = "submitted"
    NEEDS_CLARIFICATION = "needs_clarification"
    ROUTED = "routed"
    READY_FOR_DRAFT = "ready_for_draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UserRequestExecutionReadiness(StrEnum):
    """Skill/knowledge readiness Р Р†Р вЂљРІР‚Сњ independent of route kind (Phase H2.5)."""

    NOT_APPLICABLE = "not_applicable"
    NEEDS_CLARIFICATION = "needs_clarification"
    AWAITING_KNOWLEDGE = "awaiting_knowledge"
    READY_FOR_DRAFT = "ready_for_draft"
    BLOCKED = "blocked"


class UserRequestRouteCategory(StrEnum):
    IDEA_VALIDATION = "idea_validation"
    MARKET_RESEARCH = "market_research"
    COMPETITOR_ANALYSIS = "competitor_analysis"
    MARKETING_STRATEGY = "marketing_strategy"
    CONTENT = "content"
    CONTENT_PLAN = "content_plan"
    SOCIAL_MEDIA = "social_media"
    YOUTUBE = "youtube"
    IMAGE_GENERATION = "image_generation"
    TELEGRAM_BOT = "telegram_bot"
    WEBSITE = "website"
    SAAS = "saas"
    AUTOMATION = "automation"
    GENERAL = "general"
    UNSUPPORTED = "unsupported"


class UserRequestRouteKind(StrEnum):
    PROJECT_INTAKE = "project_intake"
    SPECIALIST_TASK = "specialist_task"
    CLARIFY = "clarify"
    UNSUPPORTED = "unsupported"


class UserRequest(BaseModel):
    """Owner-scoped conversational intake Р Р†Р вЂљРІР‚Сњ distinct from project Task / AgentRun."""

    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    text: str
    normalized_text: str = ""
    selected_scenario: str | None = None
    route_category: UserRequestRouteCategory = UserRequestRouteCategory.GENERAL
    route_kind: UserRequestRouteKind = UserRequestRouteKind.CLARIFY
    route_confidence: float = 0.0
    status: UserRequestStatus = UserRequestStatus.SUBMITTED
    clarification_question: str | None = None
    clarification_answer: str | None = None
    project_id: UUID | None = None
    task_id: UUID | None = None
    assigned_specialist: str | None = None
    requires_project: bool = False
    avoids_investigation: bool = False
    next_href: str | None = None
    next_action_label: str | None = None
    assistant_message: str = ""
    title: str = ""
    source: str = "home_conversation"
    # Phase H2.5 Р Р†Р вЂљРІР‚Сњ skill / knowledge context (no execution)
    skill_code: str | None = None
    skill_version: str | None = None
    capability_pack_code: str | None = None
    capability_pack_version: str | None = None
    knowledge_snapshot_id: UUID | None = None
    knowledge_snapshot_hash: str | None = None
    execution_readiness: UserRequestExecutionReadiness = (
        UserRequestExecutionReadiness.NOT_APPLICABLE
    )
    missing_inputs: list[str] = Field(default_factory=list)
    quality_profile_code: str | None = None
    skill_inputs: dict[str, Any] = Field(default_factory=dict)
    approved_knowledge_count: int = 0
    generated_visual_asset_ids: list[UUID] = Field(default_factory=list)
    generation_status: str | None = None
    generation_warnings: list[str] = Field(default_factory=list)
    # Phase H2.7 Р Р†Р вЂљРІР‚Сњ content draft execution (draft-only)
    content_draft: dict[str, Any] | None = None
    content_draft_review_status: str | None = None
    prompt_package_hash: str | None = None
    execution_provider: str | None = None
    execution_model: str | None = None
    business_idea_validation: dict[str, Any] | None = None
    client_message_id: str | None = None
    idempotency_key: str | None = None
    conversation_id: UUID | None = None
    sequence_number: int | None = None
    assistant_run_id: UUID | None = None
    routing_decision_id: UUID | None = None
    chat_route: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class GeneratedVisualAssetStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"
    DIAGNOSTIC = "diagnostic"
    AWAITING_IDENTITY_REVIEW = "awaiting_identity_review"
    REJECTED_INSUFFICIENT_SIMILARITY = "rejected_insufficient_similarity"
    REJECTED_BY_QUALITY_GATE = "rejected_by_quality_gate"


class GeneratedVisualGenerationMode(StrEnum):
    REAL = "real"
    MOCK = "mock"


class VisualExecutionMode(StrEnum):
    """Exact provider execution modes (Phase H2.8D)."""

    TEXT_TO_IMAGE = "text_to_image"
    REFERENCE_GUIDED_STYLE = "reference_guided_style"
    PERSON_IDENTITY_PRESERVATION = "person_identity_preservation"
    EXACT_LOGO_COMPOSITING = "exact_logo_compositing"
    IMAGE_EDIT = "image_edit"


class IdentityProviderCapability(StrEnum):
    SUITABLE_FOR_IDENTITY = "suitable_for_identity"
    CONDITIONALLY_SUITABLE = "conditionally_suitable"
    UNSUITABLE_FOR_IDENTITY = "unsuitable_for_identity"
    UNKNOWN = "unknown"
    UNVERIFIED = "unverified"
    UNAVAILABLE = "unavailable"


# --- Phase H2.8E: Identity Generation Subsystem ---


class IdentityProviderHealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class IdentityProviderCostPolicy(StrEnum):
    FREE_MOCK = "free_mock"
    PAID_PER_CALL = "paid_per_call"
    UNKNOWN = "unknown"


class IdentityProviderDefinition(BaseModel):
    """Authoritative identity provider registry entry (no secrets)."""

    provider_code: str
    adapter_code: str
    enabled: bool = False
    configured: bool = False
    health_status: IdentityProviderHealthStatus = IdentityProviderHealthStatus.UNKNOWN
    supported_modes: list[VisualExecutionMode] = Field(default_factory=list)
    maximum_identity_images: int = 1
    supports_primary_reference: bool = False
    supports_supporting_references: bool = False
    supports_style_reference: bool = False
    supports_identity_strength: bool = False
    supports_style_strength: bool = False
    supports_seed: bool = False
    supports_image_edit: bool = False
    supports_async_jobs: bool = False
    cost_policy: IdentityProviderCostPolicy = IdentityProviderCostPolicy.UNKNOWN
    approval_required: bool = True
    known_limitations: list[str] = Field(default_factory=list)
    last_verified_at: datetime | None = None
    capability_status: IdentityProviderCapability = IdentityProviderCapability.UNVERIFIED


class IdentityReferenceAdmissionStatus(StrEnum):
    UPLOADED = "uploaded"
    INSPECTED = "inspected"
    ACCEPTED_FOR_REFERENCE = "accepted_for_reference"
    CLASSIFIED = "classified"
    SELECTED = "selected"
    EXCLUDED = "excluded"
    FROZEN_IN_MANIFEST = "frozen_in_manifest"
    REJECTED_TECHNICAL = "rejected_technical"


class IdentityManifestSelectedEntry(BaseModel):
    asset_id: UUID
    checksum: str
    purpose: str
    role: str
    group: str
    original_width: int | None = None
    original_height: int | None = None
    transmitted_width: int | None = None
    transmitted_height: int | None = None
    mime_type: str | None = None
    quality_status: str
    selection_rank: int
    selected_reason: str
    will_transmit: bool = False
    transmission_status: str = "selected"  # selected | selected_but_not_transmitted | transmitted


class IdentityManifestExcludedEntry(BaseModel):
    asset_id: UUID
    exclusion_code: str
    safe_reason: str


class IdentityReferenceManifest(BaseModel):
    """Immutable Source-of-Truth snapshot for identity execution (Phase H2.8E)."""

    manifest_id: UUID
    owner_id: UUID
    reference_set_id: UUID
    reference_set_version: str
    subject_type: str
    primary_reference_id: UUID | None = None
    identity_reference_ids: list[UUID] = Field(default_factory=list)
    appearance_reference_ids: list[UUID] = Field(default_factory=list)
    style_reference_ids: list[UUID] = Field(default_factory=list)
    excluded_references: list[IdentityManifestExcludedEntry] = Field(default_factory=list)
    selected_entries: list[IdentityManifestSelectedEntry] = Field(default_factory=list)
    selection_policy_version: str = "h2.8e.1"
    identity_profile_id: str | None = None
    identity_profile_version: str | None = None
    provider_code: str | None = None
    transmitted_reference_ids: list[UUID] = Field(default_factory=list)
    references_selected_count: int = 0
    references_provider_received_count: int = 0
    stored_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    immutable_hash: str


class IdentityPreflightCondition(BaseModel):
    code: str
    blocking: bool
    safe_message: str
    ok: bool


class IdentityGenerationReadiness(BaseModel):
    """Typed readiness for person_identity_preservation (Phase H2.8E)."""

    ready: bool
    subsystem: str = "identity_generation"
    provider: str | None = None
    provider_definition: IdentityProviderDefinition | None = None
    requested_mode: VisualExecutionMode = VisualExecutionMode.PERSON_IDENTITY_PRESERVATION
    capability_status: IdentityProviderCapability = IdentityProviderCapability.UNVERIFIED
    uploaded_references: int = 0
    selected_identity_references: int = 0
    selected_style_references: int = 0
    actual_provider_input_capacity: int = 1
    references_provider_will_receive: int = 0
    blocking_conditions: list[IdentityPreflightCondition] = Field(default_factory=list)
    paid_approval_required: bool = True
    paid_approval_granted: bool = False
    estimated_provider_calls: int = 0
    mock_or_real: str = "unknown"  # mock | real
    safe_summary: str = ""
    safe_detail_lines: list[str] = Field(default_factory=list)


class IdentityQualificationRunStatus(StrEnum):
    DRAFT = "draft"
    PREFLIGHT_FAILED = "preflight_failed"
    AWAITING_PAID_APPROVAL = "awaiting_paid_approval"
    APPROVED = "approved"
    RUNNING = "running"
    AWAITING_OWNER_REVIEW = "awaiting_owner_review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class IdentityPaidApprovalChoice(StrEnum):
    APPROVE_ONE_DIAGNOSTIC = "approve_one_diagnostic"
    APPROVE_FULL_COMPARISON = "approve_full_comparison"
    REJECT = "reject"
    CANCEL = "cancel"


class IdentityQualificationVariantStatus(StrEnum):
    PENDING = "pending"
    UNSUPPORTED_BY_ADAPTER = "unsupported_by_adapter"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTED = "executed"
    FAILED = "failed"
    SKIPPED = "skipped"


class IdentityQualificationVariant(BaseModel):
    variant_code: str  # A|B|C|D
    label: str
    status: IdentityQualificationVariantStatus
    reason: str | None = None
    asset_id: UUID | None = None
    transmitted_reference_ids: list[UUID] = Field(default_factory=list)
    references_provider_received_count: int = 0


class IdentityPaidApprovalRequest(BaseModel):
    approval_id: UUID
    action_type: str = "identity_provider_qualification_calls"
    provider: str
    model: str | None = None
    call_count: int
    estimated_max_cost: str | None = None
    prompt_summary: str
    manifest_id: UUID
    variants: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None
    owner_confirmed: bool = False
    choice: IdentityPaidApprovalChoice | None = None


class IdentityQualificationRun(BaseModel):
    id: UUID
    owner_id: UUID
    status: IdentityQualificationRunStatus
    baseline_asset_id: UUID | None = None
    reference_set_id: UUID
    manifest_id: UUID | None = None
    manifest_hash: str | None = None
    provider_code: str
    prompt_summary: str
    stage: str = "validate_preflight"
    variants: list[IdentityQualificationVariant] = Field(default_factory=list)
    paid_approval: IdentityPaidApprovalRequest | None = None
    readiness: IdentityGenerationReadiness | None = None
    capability_status: IdentityProviderCapability = IdentityProviderCapability.UNKNOWN
    owner_review_result: str | None = None
    consistency_assist: str | None = None
    report_summary: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class IdentityProductMode(StrEnum):
    CREATIVE_GENERATION = "creative_generation"
    REFERENCE_GUIDED_STYLE = "reference_guided_style"
    PERSON_IDENTITY_PRESERVATION = "person_identity_preservation"
    EXACT_LOGO_PRODUCT_PLACEMENT = "exact_logo_product_placement"


class IdentityRecipeCode(StrEnum):
    NEW_CREATIVE_CHARACTER = "new_creative_character"
    PRESERVE_PERSON_NEW_SCENE = "preserve_person_new_scene"
    APPLY_STYLE_NO_IDENTITY = "apply_style_no_identity"
    EXACT_LOGO_PLACEMENT = "exact_logo_placement"
    STRENGTHEN_LIKENESS = "strengthen_likeness"
    PROVIDER_QUALIFICATION = "provider_qualification"


class IdentityRecipe(BaseModel):
    code: IdentityRecipeCode
    title: str
    title_ru: str
    required_inputs: list[str] = Field(default_factory=list)
    provider_capability_required: IdentityProviderCapability | None = None
    approval_required: bool = False
    tool_profile: str = "design.image_generation"
    quality_gate: str = "none"
    review_required: bool = False
    prohibited_fallbacks: list[str] = Field(default_factory=list)
    product_mode: IdentityProductMode
    notes: str = ""


class IdentityCapabilityDecision(BaseModel):
    provider_code: str
    capability_status: IdentityProviderCapability
    rationale: str
    owner_review_required: bool = True
    replacement_recommended: bool = False
    decided_by: str = "policy"  # policy | owner Р Р†Р вЂљРІР‚Сњ never unit_tests
    decided_at: datetime = Field(default_factory=datetime.utcnow)


class GeneratedVisualAssetType(StrEnum):
    USER_RESULT = "user_result"
    DIAGNOSTIC_PLACEHOLDER = "diagnostic_placeholder"
    IDENTITY_AB_CHILD = "identity_ab_child"

    VIDEO_CLIP = "video_clip"


class DurationValidationStatus(StrEnum):
    """VS.2A-R — measured clip duration vs requested."""

    MATCHED = "matched"
    WITHIN_TOLERANCE = "within_tolerance"
    MISMATCH = "mismatch"


class VideoClipRequestStatus(StrEnum):
    """VS.2A commercial single-clip lifecycle."""

    PREVIEW = "preview"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    RESULT_REQUIRES_REVIEW = "result_requires_review"
    FAILED = "failed"
    OUTCOME_UNKNOWN = "outcome_unknown"


class VideoClipPreviewPublic(BaseModel):
    """Entrepreneur-safe preview — no provider/runtime internals."""

    clip_request_id: UUID
    status: VideoClipRequestStatus
    motion_brief: str
    duration_seconds: int
    aspect_ratio: str
    estimated_cost_label: str
    estimated_wait_seconds: int
    what_will_be_created_ru: str
    limitations_ru: list[str] = Field(default_factory=list)
    ready_to_generate: bool
    blocked_reason_ru: str | None = None
    approval_required: bool = True


class VideoClipExecutionPublic(BaseModel):
    """Entrepreneur-safe execution result."""

    clip_request_id: UUID
    status: VideoClipRequestStatus
    user_message_ru: str
    result_asset_id: UUID | None = None
    result_playback_uri: str | None = None
    requested_duration_seconds: int | None = None
    actual_duration_seconds: float | None = None
    duration_delta_seconds: float | None = None
    duration_validation_status: DurationValidationStatus | None = None
    can_accept: bool = False
    can_retry_motion: bool = False
    can_create_variant: bool = False
    can_add_to_project: bool = False
    can_reconcile: bool = False
    can_contact_admin: bool = False


class VideoClipHydrationPublic(BaseModel):
    """Restore image→video state by source asset — no auto-create."""

    clip_request_id: UUID
    status: VideoClipRequestStatus
    source_image_asset_id: UUID
    preview: VideoClipPreviewPublic | None = None
    execution: VideoClipExecutionPublic | None = None


class VideoOwnerAcceptancePreviewPublic(BaseModel):
    """Owner/admin diagnostic binding for canonical smoke acceptance preview."""

    source_image_asset_id: UUID
    clip_request_id: UUID
    result_asset_id: UUID | None = None
    user_request_id: UUID | None = None
    seed_brief: str
    source_user_accepted: bool
    video_user_accepted: bool | None = None
    execution: VideoClipExecutionPublic


class VideoDurationMode(StrEnum):
    SINGLE_CLIP = "single_clip"
    LONG_FORM = "long_form"


class VideoSourceMode(StrEnum):
    NO_START_FRAME = "no_start_frame"
    IMAGE = "image"
    START_END_FRAME = "start_end_frame"


class VideoAspectRatioOptionPublic(BaseModel):
    id: str
    label_ru: str
    label_en: str
    purpose_ru: str
    availability: str
    disabled_reason_ru: str | None = None


class CameraMovementOptionPublic(BaseModel):
    id: str
    label_ru: str
    label_en: str
    description_ru: str
    provisional: bool = True


class VideoStudioCapabilitiesPublic(BaseModel):
    requested_durations_seconds: list[int]
    provider_supported_single_clip_durations_seconds: list[int]
    single_clip_max_seconds: int
    single_clip_min_seconds: int
    target_scene_duration_seconds: int
    aspect_ratios: list[VideoAspectRatioOptionPublic]
    camera_movements: list[CameraMovementOptionPublic]
    camera_movements_catalog_status: str
    camera_movements_catalog_note_ru: str
    long_form_planning_available: bool
    long_form_generation_available: bool
    start_end_frame_available: bool
    single_clip_generation_available: bool
    assembly_pipeline_ready: bool


class VideoStudioPreviewPublic(BaseModel):
    duration_mode: VideoDurationMode
    requested_duration_seconds: int
    aspect_ratio: str
    source_mode: VideoSourceMode
    camera_movement_id: str
    scene_description: str
    scene_count: int
    scene_durations_seconds: list[int]
    estimated_provider_calls: int
    estimated_cost_label: str
    estimated_wait_seconds: int
    what_will_be_created_ru: str
    limitations_ru: list[str] = Field(default_factory=list)
    generation_available: bool
    plan_only: bool
    primary_action_ru: str
    blocked_reason_ru: str | None = None
    approval_required: bool = False
    readiness_message_ru: str
    normalized_motion_prompt: str | None = None


class VisualConsistencyLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNAVAILABLE = "unavailable"


class IdentityPreservationProfile(BaseModel):
    """Person-mode identity constraints (Phase H2.8B) Р Р†Р вЂљРІР‚Сњ maximize, never guarantee."""

    version: str = "1.0"
    primary_reference_id: UUID | None = None
    reference_asset_ids: list[UUID] = Field(default_factory=list)
    preserve_face_structure: bool = True
    preserve_eye_shape: bool = True
    preserve_nose_shape: bool = True
    preserve_lip_shape: bool = True
    preserve_skin_tone: bool = True
    preserve_hair_color: bool = True
    preserve_hair_style: bool = True
    preserve_apparent_age: bool = True
    preserve_distinctive_features: bool = True
    preserve_body_proportions: bool = True
    allowed_changes: list[str] = Field(
        default_factory=lambda: [
            "clothing",
            "background",
            "lighting",
            "pose_within_limits",
            "artistic_setting",
        ]
    )
    forbidden_changes: list[str] = Field(
        default_factory=lambda: [
            "replace_person",
            "change_ethnicity",
            "material_age_change",
            "core_facial_proportions",
            "unrelated_facial_features",
        ]
    )
    user_notes: str | None = None
    strengthen_mode: bool = False


class GeneratedVisualAsset(BaseModel):
    """Owner-scoped durable image from design.image_generation (Phase H2.6A)."""

    id: UUID
    owner_id: UUID
    user_request_id: UUID
    skill_code: str
    skill_version: str
    knowledge_snapshot_id: UUID | None = None
    provider: str
    model: str | None = None
    provider_model: str | None = None
    generation_mode: GeneratedVisualGenerationMode = GeneratedVisualGenerationMode.MOCK
    asset_type: GeneratedVisualAssetType = GeneratedVisualAssetType.DIAGNOSTIC_PLACEHOLDER
    prompt_summary: str
    aspect_ratio: str
    width: int | None = None
    height: int | None = None
    mime_type: str = "image/png"
    storage_uri: str | None = None
    content_path: str | None = None
    checksum: str | None = None
    status: GeneratedVisualAssetStatus
    safety_result: str = "passed"
    generation_metadata: dict[str, Any] = Field(default_factory=dict)
    error_category: str | None = None
    created_at: datetime
    reference_set_id: UUID | None = None
    used_reference_ids: list[UUID] = Field(default_factory=list)
    excluded_reference_ids: list[UUID] = Field(default_factory=list)
    identity_similarity: str | None = None
    brand_similarity: str | None = None
    user_accepted: bool | None = None
    review_notes: str | None = None
    parent_asset_id: UUID | None = None
    identity_profile_version: str | None = None
    visual_consistency: str | None = None


class ReferenceAssetPurpose(StrEnum):
    IDENTITY_REFERENCE = "identity_reference"
    FACE_REFERENCE = "face_reference"
    FACE_FRONT = "face_front"
    FACE_THREE_QUARTER = "face_three_quarter"
    FACE_PROFILE = "face_profile"
    FACE_CLOSEUP = "face_closeup"
    HALF_BODY = "half_body"
    FULL_BODY = "full_body"
    BODY_REFERENCE = "body_reference"
    OUTFIT_REFERENCE = "outfit_reference"
    CLOTHING = "clothing"
    POSE = "pose"
    POSE_REFERENCE = "pose_reference"
    HAIR = "hair"
    PRODUCT_REFERENCE = "product_reference"
    BRAND_REFERENCE = "brand_reference"
    STYLE_REFERENCE = "style_reference"
    COMPOSITION_REFERENCE = "composition_reference"
    BACKGROUND_REFERENCE = "background_reference"
    LOGO_REFERENCE = "logo_reference"
    OTHER = "other"


class ReferencePurposeGroup(StrEnum):
    IDENTITY = "identity"
    APPEARANCE = "appearance"
    SCENE = "scene"
    OTHER = "other"


class ReferenceExclusionReason(StrEnum):
    NOT_FACE_REFERENCE = "not_face_reference"
    DUPLICATED_ANGLE = "duplicated_angle"
    DUPLICATE_ANGLE = "duplicate_angle"  # H2.8E alias
    LOWER_QUALITY = "lower_quality"
    LOW_RESOLUTION = "low_resolution"
    BLUR = "blur"
    BLURRED = "blurred"
    OCCLUDED = "occluded"
    OCCLUSION = "occlusion"
    STYLE_ONLY = "style_only"
    BODY_ONLY = "body_only"
    PROVIDER_LIMIT = "provider_limit"
    DUPLICATE_CHECKSUM = "duplicate_checksum"
    INCONSISTENT_SUBJECT = "inconsistent_subject"
    USER_EXCLUDED = "user_excluded"
    UNSUITABLE_QUALITY = "unsuitable_quality"
    BODY_NOT_PRIMARY = "body_not_primary"
    NOT_SELECTED = "not_selected"
    PROVIDER_CAP_RANK = "provider_cap_rank"
    SELECTED_BUT_NOT_TRANSMITTED = "selected_but_not_transmitted"
    PROVIDER_ADAPTER_LIMIT = "provider_adapter_limit"


class ReferenceSubjectType(StrEnum):
    PERSON = "person"
    PRODUCT = "product"
    LOGO = "logo"
    CHARACTER = "character"
    LOCATION = "location"
    STYLE = "style"
    MIXED = "mixed"


class ReferenceQualityStatus(StrEnum):
    SUITABLE = "suitable"
    LIMITED = "limited"
    UNSUITABLE = "unsuitable"
    PENDING = "pending"


class ReferenceSafetyStatus(StrEnum):
    PASSED = "passed"
    REJECTED = "rejected"
    PENDING = "pending"


class ReferenceSetStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    USED = "used"
    ARCHIVED = "archived"


class ReferenceVisualAsset(BaseModel):
    """Owner-scoped uploaded reference image (Phase H2.6A-R)."""

    id: UUID
    owner_id: UUID
    project_id: UUID | None = None
    user_request_id: UUID | None = None
    original_filename: str
    mime_type: str
    width: int | None = None
    height: int | None = None
    byte_size: int
    checksum: str
    storage_uri: str | None = None
    asset_purpose: ReferenceAssetPurpose = ReferenceAssetPurpose.OTHER
    subject_type: ReferenceSubjectType = ReferenceSubjectType.MIXED
    quality_status: ReferenceQualityStatus = ReferenceQualityStatus.PENDING
    quality_notes: str | None = None
    safety_status: ReferenceSafetyStatus = ReferenceSafetyStatus.PENDING
    created_at: datetime
    archived_at: datetime | None = None
    # H2.8B Р Р†Р вЂљРІР‚Сњ idempotent attach (never expose raw duplicate_checksum to UI)
    attach_status: str | None = None  # already_attached | reused_existing_asset | created
    attach_message: str | None = None
    # H2.8C Р Р†Р вЂљРІР‚Сњ optional secondary purposes (primary remains asset_purpose)
    asset_purposes: list[str] = Field(default_factory=list)


class ReferenceSet(BaseModel):
    """Durable set of up to 15 references for identity/brand preservation."""

    id: UUID
    owner_id: UUID
    project_id: UUID | None = None
    user_request_id: UUID | None = None
    title: str
    subject_type: ReferenceSubjectType = ReferenceSubjectType.MIXED
    preservation_goal: str = "maximize_recognizability"
    status: ReferenceSetStatus = ReferenceSetStatus.DRAFT
    reference_asset_ids: list[UUID] = Field(default_factory=list)
    primary_reference_id: UUID | None = None
    identity_notes: str | None = None
    immutable_traits: list[str] = Field(default_factory=list)
    allowed_variations: list[str] = Field(default_factory=list)
    forbidden_changes: list[str] = Field(default_factory=list)
    consent_confirmed: bool = False
    created_at: datetime
    updated_at: datetime


class ReferenceSelectionRole(BaseModel):
    """Per-reference role in provider selection (Phase H2.8D)."""

    reference_id: UUID
    purpose: str
    group: ReferencePurposeGroup = ReferencePurposeGroup.OTHER
    role_label: str = ""
    is_primary: bool = False
    selected: bool = False
    exclusion_reason: str | None = None


class ReferenceSelectionResult(BaseModel):
    selected_reference_ids: list[UUID] = Field(default_factory=list)
    excluded_reference_ids: list[UUID] = Field(default_factory=list)
    exclusion_reasons: dict[str, str] = Field(default_factory=dict)
    max_provider_references: int = 5
    selection_summary: str = ""
    # H2.8D Р Р†Р вЂљРІР‚Сњ identity/style split
    identity_selected_ids: list[UUID] = Field(default_factory=list)
    appearance_selected_ids: list[UUID] = Field(default_factory=list)
    scene_selected_ids: list[UUID] = Field(default_factory=list)
    identity_selected_count: int = 0
    style_selected_count: int = 0
    excluded_count: int = 0
    stored_count: int = 0
    roles: list[ReferenceSelectionRole] = Field(default_factory=list)
    transmitted_reference_ids: list[UUID] = Field(default_factory=list)
    primary_reference_id: UUID | None = None


class VisualConsistencyReview(BaseModel):
    identity_similarity: str | None = None  # high|medium|low|not_applicable
    brand_similarity: str | None = None
    user_accepted: bool | None = None
    review_notes: str | None = None


# --- Phase H2.1Р Р†Р вЂљРІР‚СљH2.2: Knowledge Inventory + Specialist Skill Registry ---


class KnowledgeType(StrEnum):
    """Classification for candidate / governed knowledge (Phase H2.1)."""

    CONSTITUTIONAL_POLICY = "constitutional_policy"
    DOMAIN_METHODOLOGY = "domain_methodology"
    WORKFLOW_INSTRUCTION = "workflow_instruction"
    OUTPUT_TEMPLATE = "output_template"
    QUALITY_STANDARD = "quality_standard"
    VERIFIED_FACT = "verified_fact"
    PROJECT_KNOWLEDGE = "project_knowledge"
    EXAMPLE = "example"
    HISTORICAL_RECORD = "historical_record"
    OPERATIONAL_DOCUMENT = "operational_document"
    OBSOLETE = "obsolete"
    FORBIDDEN = "forbidden"


class KnowledgeItemStatus(StrEnum):
    CANDIDATE = "candidate"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class KnowledgeAuthority(StrEnum):
    CONSTITUTIONAL = "constitutional"
    PRODUCT = "product"
    DOMAIN = "domain"
    OWNER = "owner"
    PROJECT = "project"
    EXAMPLE = "example"
    HISTORICAL = "historical"


class KnowledgeTenantScope(StrEnum):
    GLOBAL = "global"
    OWNER = "owner"
    PROJECT = "project"


class KnowledgeDomain(StrEnum):
    CONSTITUTIONAL = "constitutional"
    MARKETING = "marketing"
    RESEARCH = "research"
    CONTENT = "content"
    STRATEGY = "strategy"
    PROGRAMMER = "programmer"
    PRODUCT = "product"
    OPERATIONS = "operations"
    MIXED = "mixed"


class KnowledgeItem(BaseModel):
    """Governed knowledge metadata Р Р†Р вЂљРІР‚Сњ inventory catalog (Phase H2.1)."""

    id: str
    title: str
    knowledge_type: KnowledgeType
    domain: KnowledgeDomain
    specialist_roles: list[str] = Field(default_factory=list)
    source_uri: str
    source_hash: str | None = None
    version: str = "1.0"
    status: KnowledgeItemStatus = KnowledgeItemStatus.CANDIDATE
    authority: KnowledgeAuthority = KnowledgeAuthority.PRODUCT
    tenant_scope: KnowledgeTenantScope = KnowledgeTenantScope.GLOBAL
    owner_id: UUID | None = None
    project_id: UUID | None = None
    locale: str = "en"
    valid_from: datetime = Field(default_factory=datetime.utcnow)
    valid_until: datetime | None = None
    supersedes_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    citation_required: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None
    migration_action: str | None = None
    notes: str | None = None


class KnowledgeContentFormat(StrEnum):
    MARKDOWN = "markdown"
    TEXT = "text"
    JSON = "json"


class StoredKnowledgeItem(BaseModel):
    """Durable KnowledgeItem row (Phase H2.3) Р Р†Р вЂљРІР‚Сњ approved versions are immutable."""

    id: UUID
    code: str
    title: str
    knowledge_type: KnowledgeType
    domain: KnowledgeDomain
    content: str
    content_format: KnowledgeContentFormat = KnowledgeContentFormat.MARKDOWN
    content_hash: str
    source_uri: str
    source_hash: str | None = None
    version: str
    status: KnowledgeItemStatus
    authority: KnowledgeAuthority
    tenant_scope: KnowledgeTenantScope
    owner_id: UUID | None = None
    project_id: UUID | None = None
    locale: str = "en"
    valid_from: datetime
    valid_until: datetime | None = None
    supersedes_id: UUID | None = None
    citation_required: bool = False
    tags: list[str] = Field(default_factory=list)
    specialist_roles: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    review_rationale: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None


class KnowledgeRetrievalRequest(BaseModel):
    skill_code: str
    skill_version: str = "1.0"
    specialist_role: str | None = None
    owner_id: UUID
    project_id: UUID | None = None
    locale: str = "ru"
    requested_scopes: list[str] = Field(default_factory=list)
    query_terms: list[str] = Field(default_factory=list)
    domain_codes: list[str] = Field(default_factory=list)
    limit: int = Field(default=40, ge=1, le=100)


class KnowledgeRetrievalItem(BaseModel):
    knowledge_item_id: UUID
    code: str
    version: str
    title: str
    knowledge_type: KnowledgeType
    source_uri: str
    authority: KnowledgeAuthority
    tenant_scope: KnowledgeTenantScope
    owner_id: UUID | None = None
    project_id: UUID | None = None
    citation_required: bool
    relevance_reason: str
    content_hash: str
    locale: str
    # Content omitted from default specialist UI; diagnostics may opt-in.
    include_content: bool = False
    content: str | None = None


class KnowledgeRetrievalResult(BaseModel):
    items: list[KnowledgeRetrievalItem] = Field(default_factory=list)
    snapshot_hash: str
    retrieval_policy_version: str
    excluded_count: int = 0
    warnings: list[str] = Field(default_factory=list)


class KnowledgeSnapshotItemRef(BaseModel):
    knowledge_item_id: UUID
    code: str
    version: str
    content_hash: str
    relevance_reason: str
    authority: KnowledgeAuthority
    citation_required: bool


class KnowledgeSnapshot(BaseModel):
    id: UUID
    owner_id: UUID
    project_id: UUID | None = None
    skill_code: str
    skill_version: str
    capability_pack_version: str
    retrieval_policy_version: str
    locale: str
    item_refs: list[KnowledgeSnapshotItemRef] = Field(default_factory=list)
    snapshot_hash: str
    created_at: datetime


class KnowledgeApproveRequest(BaseModel):
    rationale: str | None = None


class KnowledgeSupersedeRequest(BaseModel):
    content: str
    version: str
    source_uri: str | None = None
    source_hash: str | None = None
    rationale: str | None = None
    locale: str | None = None
    tags: list[str] | None = None


class KnowledgeInventoryFilter(BaseModel):
    knowledge_type: KnowledgeType | None = None
    domain: KnowledgeDomain | None = None
    status: KnowledgeItemStatus | None = None
    specialist_role: str | None = None
    locale: str | None = None


class KnowledgeReviewRequest(BaseModel):
    note: str | None = None


class KnowledgeRetrievalHit(BaseModel):
    """Deterministic retrieval result Р Р†Р вЂљРІР‚Сњ similarity is never factual confidence."""

    knowledge_id: str
    version: str
    source_uri: str
    authority: KnowledgeAuthority
    tenant_scope: KnowledgeTenantScope
    owner_id: UUID | None = None
    project_id: UUID | None = None
    relevance_reason: str
    citation_required: bool
    knowledge_type: KnowledgeType


class KnowledgeStorageOption(StrEnum):
    POSTGRES_FTS = "postgres_fts"
    POSTGRES_VECTOR_ADAPTER = "postgres_vector_adapter"
    EXISTING_APPROVED_SERVICE = "existing_approved_service"


# --- Knowledge Governance Subsystem (architecture contracts; no retrieval/vector/LLM impl) ---


class KnowledgeGovernanceStatus(StrEnum):
    """Authoritative governance lifecycle for Knowledge Objects.

    Maps onto legacy KnowledgeItemStatus for H2.1Р Р†Р вЂљРІР‚СљH2.5 compatibility:
    draftР Р†РІР‚В РІР‚в„ўcandidate, validatedР Р†РІР‚В РІР‚в„ўunder_review(+validation), publishedР Р†РІР‚В РІР‚в„ўapproved,
    deprecatedР Р†РІР‚В РІР‚в„ў(new axis; not served), archivedР Р†РІР‚В РІР‚в„ўarchived, supersededР Р†РІР‚В РІР‚в„ўsuperseded.
    """

    DRAFT = "draft"
    VALIDATED = "validated"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    SUPERSEDED = "superseded"


class KnowledgeVisibility(StrEnum):
    PRIVATE = "private"
    OWNER = "owner"
    PROJECT = "project"
    TENANT = "tenant"
    GLOBAL = "global"


class KnowledgeFreshnessState(StrEnum):
    FRESH = "fresh"
    DUE_FOR_REVIEW = "due_for_review"
    EXPIRED = "expired"
    DEPRECATED = "deprecated"
    UNKNOWN = "unknown"


class KnowledgeConfidenceLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNVERIFIED = "unverified"


class KnowledgeEvidenceRef(BaseModel):
    """Link in an EvidenceChain Р Р†Р вЂљРІР‚Сњ durable id/uri only; never embeds secrets."""

    evidence_id: str
    source_uri: str | None = None
    locator: str | None = None
    note: str | None = None


class KnowledgeDecisionRef(BaseModel):
    """Link in a DecisionChain (review/publication/deprecation decisions)."""

    decision_id: str
    decision_type: str
    actor: str | None = None
    decided_at: datetime | None = None
    rationale: str | None = None


class KnowledgeObject(BaseModel):
    """Governed Knowledge Object Р Р†Р вЂљРІР‚Сњ required metadata for the governance subsystem.

    Architecture contract only in this phase. Persistence/API may follow in a later phase.
    """

    knowledge_id: UUID
    owner: str
    reviewer: str | None = None
    review_date: datetime | None = None
    next_review: datetime | None = None
    confidence: KnowledgeConfidenceLevel = KnowledgeConfidenceLevel.UNVERIFIED
    freshness: KnowledgeFreshnessState = KnowledgeFreshnessState.UNKNOWN
    visibility: KnowledgeVisibility = KnowledgeVisibility.OWNER
    tenant: KnowledgeTenantScope = KnowledgeTenantScope.OWNER
    domain: KnowledgeDomain = KnowledgeDomain.MIXED
    evidence_chain: list[KnowledgeEvidenceRef] = Field(default_factory=list)
    decision_chain: list[KnowledgeDecisionRef] = Field(default_factory=list)
    version: str = "1.0"
    status: KnowledgeGovernanceStatus = KnowledgeGovernanceStatus.DRAFT
    # Compatibility bridge to H2.1 inventory
    legacy_item_status: KnowledgeItemStatus | None = None
    title: str | None = None
    superseded_by: UUID | None = None
    supersedes: UUID | None = None


class SemanticChunk(BaseModel):
    """Structured semantic unit Р Р†Р вЂљРІР‚Сњ not arbitrary token/window chunking."""

    chunk_id: UUID
    knowledge_id: UUID
    title: str
    intent: str
    rule: str
    condition: str | None = None
    exception: str | None = None
    references: list[str] = Field(default_factory=list)
    version: str = "1.0"
    locale: str = "ru"


class BenchmarkCase(BaseModel):
    """Single benchmark case for validating governed knowledge answers."""

    case_id: UUID
    question: str
    expected_source: str
    expected_evidence: str
    expected_answer: str
    requires_expert: bool = False
    acceptance_criteria: list[str] = Field(default_factory=list)
    domain: KnowledgeDomain | None = None
    knowledge_ids: list[UUID] = Field(default_factory=list)


class BenchmarkDataset(BaseModel):
    """Versioned benchmark suite for Knowledge Governance validation."""

    dataset_id: UUID
    name: str
    version: str = "1.0"
    cases: list[BenchmarkCase] = Field(default_factory=list)
    owner: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeValidationStage(StrEnum):
    CANDIDATE = "knowledge_candidate"
    HUMAN_REVIEW = "human_review"
    VALIDATION = "validation"
    PUBLICATION = "publication"


class KnowledgeValidationPipelineState(BaseModel):
    """Pipeline: Knowledge Candidate Р Р†РІР‚В РІР‚в„ў Human Review Р Р†РІР‚В РІР‚в„ў Validation Р Р†РІР‚В РІР‚в„ў Publication."""

    pipeline_id: UUID
    knowledge_id: UUID
    stage: KnowledgeValidationStage = KnowledgeValidationStage.CANDIDATE
    governance_status: KnowledgeGovernanceStatus = KnowledgeGovernanceStatus.DRAFT
    blocking_reasons: list[str] = Field(default_factory=list)
    benchmark_dataset_id: UUID | None = None
    benchmark_pass: bool | None = None
    reviewer: str | None = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CitationContract(BaseModel):
    """Mandatory agent answer envelope for governed knowledge use.

    Any agent returning knowledge-backed answers must populate all fields.
    Architecture contract Р Р†Р вЂљРІР‚Сњ no LLM implementation in this phase.
    """

    answer: str
    evidence: list[KnowledgeEvidenceRef] = Field(default_factory=list)
    source: str
    confidence: KnowledgeConfidenceLevel
    knowledge_ids: list[UUID] = Field(default_factory=list)
    snapshot_id: UUID | None = None
    warnings: list[str] = Field(default_factory=list)


class KnowledgeFreshnessCheck(BaseModel):
    """Result of automatic freshness / review-date policy evaluation."""

    knowledge_id: UUID
    review_date: datetime | None = None
    next_review: datetime | None = None
    freshness: KnowledgeFreshnessState
    expired: bool = False
    deprecated: bool = False
    safe_message: str = ""


class KnowledgeGovernanceManifest(BaseModel):
    """Immutable Source-of-Truth snapshot for a governed knowledge publication set."""

    manifest_id: UUID
    owner_id: UUID | None = None
    tenant: KnowledgeTenantScope = KnowledgeTenantScope.GLOBAL
    policy_version: str = "kg.1"
    knowledge_ids: list[UUID] = Field(default_factory=list)
    semantic_chunk_ids: list[UUID] = Field(default_factory=list)
    benchmark_dataset_id: UUID | None = None
    published_only: bool = True
    immutable_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Legacy status Р Р†РІР‚В РІР‚Сњ governance lifecycle mapping (documentation as code)
KNOWLEDGE_GOVERNANCE_TO_LEGACY_STATUS: dict[str, str] = {
    KnowledgeGovernanceStatus.DRAFT.value: KnowledgeItemStatus.CANDIDATE.value,
    KnowledgeGovernanceStatus.VALIDATED.value: KnowledgeItemStatus.UNDER_REVIEW.value,
    KnowledgeGovernanceStatus.PUBLISHED.value: KnowledgeItemStatus.APPROVED.value,
    KnowledgeGovernanceStatus.DEPRECATED.value: KnowledgeItemStatus.ARCHIVED.value,
    KnowledgeGovernanceStatus.ARCHIVED.value: KnowledgeItemStatus.ARCHIVED.value,
    KnowledgeGovernanceStatus.SUPERSEDED.value: KnowledgeItemStatus.SUPERSEDED.value,
}


class SpecialistSkillCode(StrEnum):
    """Versioned specialist capability contracts (Phase H2.2) Р Р†Р вЂљРІР‚Сњ not Agent Registry."""

    CONTENT_TELEGRAM_POST = "content.telegram_post"
    CONTENT_CLAIM_VERIFICATION = "content.claim_verification"
    CONTENT_EDITORIAL_REVIEW = "content.editorial_review"
    CONTENT_SOCIAL_POST = "content.social_post"
    CONTENT_CONTENT_PLAN = "content.content_plan"
    CONTENT_YOUTUBE_SCRIPT = "content.youtube_script"
    DESIGN_IMAGE_GENERATION = "design.image_generation"
    RESEARCH_MARKET_OVERVIEW = "research.market_overview"
    RESEARCH_COMPETITOR_ANALYSIS = "research.competitor_analysis"
    RESEARCH_AUDIENCE_SEGMENTATION = "research.audience_segmentation"
    PROGRAMMER_TELEGRAM_BOT_SPEC = "programmer.telegram_bot_spec"
    PROGRAMMER_WEBSITE_SPEC = "programmer.website_spec"
    PROGRAMMER_AUTOMATION_SPEC = "programmer.automation_spec"
    STRATEGY_POSITIONING = "strategy.positioning"
    STRATEGY_OFFER_DESIGN = "strategy.offer_design"
    STRATEGY_CHANNEL_SELECTION = "strategy.channel_selection"


class SpecialistSkillStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class SpecialistSkillExecutionPolicy(StrEnum):
    DRAFT_ONLY = "draft_only"
    OWNER_APPROVAL_REQUIRED = "owner_approval_required"
    FORBIDDEN = "forbidden"


class SpecialistSkillDefinition(BaseModel):
    """Skill = versioned capability contract, not a long prompt."""

    id: str
    code: SpecialistSkillCode
    version: str
    title: str
    domain: KnowledgeDomain
    description: str
    specialist_roles: list[str] = Field(default_factory=list)
    input_schema: list[str] = Field(default_factory=list)
    output_schema: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    clarification_schema: list[str] = Field(default_factory=list)
    knowledge_scopes: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    optional_tools: list[str] = Field(default_factory=list)
    quality_gates: list[str] = Field(default_factory=list)
    execution_policy: SpecialistSkillExecutionPolicy = (
        SpecialistSkillExecutionPolicy.DRAFT_ONLY
    )
    status: SpecialistSkillStatus = SpecialistSkillStatus.DRAFT
    supersedes_version: str | None = None


class SpecialistCapabilityPack(BaseModel):
    """What a specialist may use Р Р†Р вЂљРІР‚Сњ skills, knowledge scopes, tools, policies."""

    specialist_role: str
    version: str
    allowed_skills: list[SpecialistSkillCode] = Field(default_factory=list)
    default_skill: SpecialistSkillCode | None = None
    knowledge_scopes: list[str] = Field(default_factory=list)
    tool_profile: list[str] = Field(default_factory=list)
    forbidden_tools: list[str] = Field(default_factory=list)
    output_policy: str
    approval_policy: str
    quality_profile: list[str] = Field(default_factory=list)
    locale_policy: list[str] = Field(default_factory=lambda: ["ru", "en"])


class SkillRouteMapping(BaseModel):
    """UserRequest route Р Р†РІР‚В РІР‚в„ў specialist Р Р†РІР‚В РІР‚в„ў skill (or clarification / existing path)."""

    route_category: UserRequestRouteCategory
    specialist_role: str | None
    skill_code: SpecialistSkillCode | None = None
    requires_clarification_when_incomplete: bool = True
    domain_eligibility_required: bool = False
    notes: str = ""
    uses_existing_project_path: bool = False


class SkillClarificationResult(BaseModel):
    skill_code: SpecialistSkillCode
    ready: bool
    missing_fields: list[str] = Field(default_factory=list)
    clarification_prompt: str | None = None


# ---------------------------------------------------------------------------
# Phase H2.7 Р Р†Р вЂљРІР‚Сњ Specialist Execution Foundation (governed contracts)
# Integration Registry, BusinessTool abstraction, Tool Profiles,
# Prompt Packages and draft-only content execution results.
# No secrets are ever stored on these contracts.
# ---------------------------------------------------------------------------


class IntegrationCode(StrEnum):
    """Configured external integrations Р Р†Р вЂљРІР‚Сњ credential presence != capability."""

    OPENAI = "openai"
    OPENROUTER = "openrouter"
    GPTUNNEL = "gptunnel"
    FIRECRAWL = "firecrawl"
    XMLRIVER = "xmlriver"
    PINECONE = "pinecone"
    MAKE = "make"
    N8N = "n8n"
    YANDEX_DIRECT = "yandex_direct"
    YANDEX_METRICA = "yandex_metrica"
    HIGGSFIELD = "higgsfield"


class IntegrationCategory(StrEnum):
    LLM = "llm"
    IMAGE = "image"
    RESEARCH_READ = "research_read"
    SEARCH_READ = "search_read"
    RETRIEVAL = "retrieval"
    EXTERNAL_EXECUTION = "external_execution"
    ADVERTISING = "advertising"
    ANALYTICS = "analytics"


class IntegrationReadiness(StrEnum):
    """Governed readiness Р Р†Р вЂљРІР‚Сњ distinct from raw credential presence."""

    CONFIGURED = "configured"
    READY = "ready"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    DISABLED = "disabled"


class IntegrationAuthType(StrEnum):
    API_KEY = "api_key"
    OAUTH_TOKEN = "oauth_token"
    NONE = "none"


class IntegrationRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class IntegrationDefinition(BaseModel):
    """Authoritative registry entry for an external integration."""

    code: IntegrationCode
    provider: str
    category: IntegrationCategory
    read_capabilities: list[str] = Field(default_factory=list)
    write_capabilities: list[str] = Field(default_factory=list)
    authentication_type: IntegrationAuthType = IntegrationAuthType.API_KEY
    configured: bool = False
    readiness: IntegrationReadiness = IntegrationReadiness.DISABLED
    health_status: str = "unknown"
    allowed_environments: list[str] = Field(default_factory=lambda: ["development"])
    cost_profile: str = "unknown"
    risk_level: IntegrationRiskLevel = IntegrationRiskLevel.MEDIUM
    owner_approval_required: bool = True
    supported_skills: list[str] = Field(default_factory=list)
    secrets_source: str = "app.core.config"
    diagnostics_safe_fields: dict[str, Any] = Field(default_factory=dict)
    notes: str = ""


class BusinessToolCode(StrEnum):
    """Normalized specialist-facing tools Р Р†Р вЂљРІР‚Сњ never provider SDKs directly."""

    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    WEB_SEARCH = "web_search"
    SOURCE_FETCH = "source_fetch"
    STRUCTURED_EXTRACTION = "structured_extraction"
    IMAGE_GENERATION = "image_generation"
    WORKFLOW_AUTOMATION = "workflow_automation"
    ADVERTISING_PLATFORM = "advertising_platform"


class BusinessToolMode(StrEnum):
    READ = "read"
    WRITE = "write"
    DISABLED = "disabled"


class ToolProfile(BaseModel):
    """Typed per-specialist tool policy Р Р†Р вЂљРІР‚Сњ governs which tools a role may use."""

    specialist_role: str
    version: str = "1.0"
    allowed_tools: list[BusinessToolCode] = Field(default_factory=list)
    denied_tools: list[BusinessToolCode] = Field(default_factory=list)
    mode: BusinessToolMode = BusinessToolMode.READ
    approval_required: bool = True
    max_calls: int = 0
    timeout_seconds: int = 30
    max_retries: int = 1
    cost_ceiling_usd: float = 0.0
    data_scope: str = "owner"
    allowed_environments: list[str] = Field(default_factory=lambda: ["development"])


class PromptPackage(BaseModel):
    """Versioned, assembled prompt lineage Р Р†Р вЂљРІР‚Сњ safe metadata only, no hidden CoT."""

    code: str
    version: str = "1.0"
    locale: str = "ru"
    specialist_role: str
    skill_code: str
    constitutional_prompt_version: str
    role_prompt_version: str
    skill_instruction_version: str
    output_schema_version: str
    quality_profile_version: str
    tool_policy_version: str
    knowledge_snapshot_id: UUID | None = None
    knowledge_snapshot_hash: str | None = None
    rendered_hash: str
    status: str = "assembled"


class ContentDraftReviewStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REVISION_REQUESTED = "revision_requested"
    REJECTED = "rejected"


class ContentDraftReviewAction(StrEnum):
    ACCEPT = "accept"
    REQUEST_REVISION = "request_revision"
    CREATE_VARIANT = "create_variant"
    REJECT = "reject"


class ContentDomainCode(StrEnum):
    GENERAL_MARKETING = "general_marketing"
    OIL_AND_GAS = "oil_and_gas"
    INDUSTRIAL_SAFETY = "industrial_safety"
    DRILLING_OPERATIONS = "drilling_operations"
    HEALTHCARE = "healthcare"
    DENTISTRY = "dentistry"
    SAAS = "saas"
    AUTOMATION = "automation"
    SOFTWARE_DEVELOPMENT = "software_development"
    E_COMMERCE = "e_commerce"
    UNKNOWN = "unknown"


class ContentFactualityMode(StrEnum):
    GENERAL_EXPERT = "general_expert"
    SOURCE_BACKED = "source_backed"
    USER_MATERIALS_ONLY = "user_materials_only"
    CREATIVE = "creative"


class ContentClaimType(StrEnum):
    FACTUAL = "factual"
    ADVISORY = "advisory"
    EXPERIENTIAL = "experiential"
    INTERPRETIVE = "interpretive"
    PROMOTIONAL = "promotional"
    OPINION = "opinion"


class ContentClaimEvidenceState(StrEnum):
    APPROVED_KNOWLEDGE = "approved_knowledge"
    USER_MATERIAL = "user_material"
    SOURCE_CANDIDATE = "source_candidate"
    INFERRED = "inferred"
    UNSUPPORTED = "unsupported"


class ContentClaimAction(StrEnum):
    ALLOW = "allow"
    SOFTEN = "soften"
    MARK_ASSUMPTION = "mark_assumption"
    REMOVE = "remove"
    REQUEST_SOURCE = "request_source"


class ContentQualityGateDecision(StrEnum):
    PASS = "pass"
    REVISE = "revise"
    BLOCK = "block"


class ContentClaim(BaseModel):
    statement: str
    claim_type: ContentClaimType = ContentClaimType.FACTUAL
    source_refs: list[str] = Field(default_factory=list)
    evidence_state: ContentClaimEvidenceState = ContentClaimEvidenceState.UNSUPPORTED
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    visible_citation_required: bool = False
    action: ContentClaimAction = ContentClaimAction.ALLOW


class ContentDomainClassification(BaseModel):
    primary: ContentDomainCode = ContentDomainCode.UNKNOWN
    secondary: list[ContentDomainCode] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    labels: list[str] = Field(default_factory=list)


class ContentTextFoundation(BaseModel):
    domain_items: list[str] = Field(default_factory=list)
    external_sources: list[str] = Field(default_factory=list)
    user_materials: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    softened_or_removed_claims: list[str] = Field(default_factory=list)


class ContentDraftQualityCheck(BaseModel):
    passed: bool = False
    schema_valid: bool = False
    required_fields_present: bool = False
    locale_ok: bool = False
    no_unsupported_claims: bool = False
    no_secrets: bool = False
    checks: dict[str, bool] = Field(default_factory=dict)
    issues: list[str] = Field(default_factory=list)
    score: float = 0.0
    dimension_scores: dict[str, float] = Field(default_factory=dict)
    critical_failures: list[str] = Field(default_factory=list)
    gate_decision: ContentQualityGateDecision = ContentQualityGateDecision.BLOCK


class ContentDraftResult(BaseModel):
    """Draft-only content specialist output Р Р†Р вЂљРІР‚Сњ never published automatically."""

    skill_code: str
    hook: str = ""
    body: str = ""
    cta: str = ""
    variants: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    factual_claims: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    knowledge_refs: list[str] = Field(default_factory=list)
    expertise_labels: list[str] = Field(default_factory=list)
    materials_used: list[str] = Field(default_factory=list)
    quality_check: ContentDraftQualityCheck = Field(
        default_factory=ContentDraftQualityCheck
    )
    generation_mode: str = "real"
    review_status: ContentDraftReviewStatus = ContentDraftReviewStatus.PENDING
    status: str = "draft"
    domain: ContentDomainClassification | None = None
    factuality_mode: ContentFactualityMode = ContentFactualityMode.GENERAL_EXPERT
    claims: list[ContentClaim] = Field(default_factory=list)
    editorial_notes: list[str] = Field(default_factory=list)
    text_foundation: ContentTextFoundation | None = None
    revision_count: int = 0


class MemoryItem(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    project_id: UUID | None = None
    layer: MemoryLayer
    key: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None


class LLMProvider(StrEnum):
    OPENAI = "openai"
    OPENROUTER = "openrouter"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    DEEPSEEK = "deepseek"
    LOCAL = "local"
    MOCK = "mock"


class LLMRequestStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LLMRequest(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    agent_id: UUID
    agent_run_id: UUID
    task_id: UUID | None = None
    provider: LLMProvider
    model: str
    input_payload: dict[str, Any] = Field(default_factory=dict)
    prompt_metadata: dict[str, Any] = Field(default_factory=dict)
    request_metadata: dict[str, Any] = Field(default_factory=dict)
    status: LLMRequestStatus = LLMRequestStatus.QUEUED
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LLMResponse(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    llm_request_id: UUID
    output_payload: dict[str, Any] = Field(default_factory=dict)
    raw_response: dict[str, Any] = Field(default_factory=dict)
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_estimate: float | None = None
    latency_ms: int | None = None
    response_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MarketingBrief(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    goal: str
    audience: str | None = None
    channels: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MarketingCampaignStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class MarketingCampaign(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    brief_id: UUID | None = None
    title: str
    description: str | None = None
    status: MarketingCampaignStatus = MarketingCampaignStatus.DRAFT
    start_at: datetime | None = None
    end_at: datetime | None = None
    campaign_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CampaignPlanDraftStatus(StrEnum):
    DRAFT = "draft"
    ARCHIVED = "archived"


class CampaignPlanDraft(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    campaign_id: UUID
    source_agent_run_id: UUID | None = None
    title: str
    plan_payload: dict[str, Any] = Field(default_factory=dict)
    status: CampaignPlanDraftStatus = CampaignPlanDraftStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ContentAsset(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    brief_id: UUID | None = None
    asset_type: ContentAssetType
    title: str
    body: str | None = None
    uri: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EventOutboxStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DEAD_LETTERED = "dead_lettered"


class WebhookDeliveryLogStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class WebhookDeliveryLog(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    webhook_id: UUID | None = None
    event_outbox_id: UUID
    event_type: str
    target_url_preview: str
    status: WebhookDeliveryLogStatus
    http_status_code: int | None = None
    attempt_number: int
    duration_ms: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    response_preview: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EventType(StrEnum):
    GRAPH_HANDOFF_PARENT_SYNCED = "graph.handoff.parent_synced"
    CONTENT_ASSET_APPROVED = "content_asset.approved"
    CONTENT_ASSET_ARCHIVED = "content_asset.archived"
    CONTENT_ASSET_ROLLBACK_REVISION_CREATED = "content_asset.rollback_revision_created"


class EventOutbox(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    event_type: EventType
    aggregate_type: str
    aggregate_id: UUID
    payload: dict[str, Any] = Field(default_factory=dict)
    status: EventOutboxStatus = EventOutboxStatus.PENDING
    attempts: int = 0
    last_error: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectWebhook(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    url: str
    subscribed_event_types: list[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CampaignWorkflowState(StrEnum):
    PLANNING = "planning"
    PLAN_READY = "plan_ready"
    ASSETS_GENERATED = "assets_generated"
    CONTENT_IN_REVISION = "content_in_revision"
    READY_FOR_REVIEW = "ready_for_review"
    APPROVED_FOR_PUBLICATION = "approved_for_publication"
    COMPLETED = "completed"


class CampaignWorkflowRecommendedAction(StrEnum):
    CREATE_PLAN_DRAFT = "create_plan_draft"
    GENERATE_ASSETS = "generate_assets"
    REVIEW_ASSETS = "review_assets"
    APPROVE_ASSETS = "approve_assets"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    SCHEDULE_PUBLICATION = "schedule_publication"
    MONITOR_PUBLICATION = "monitor_publication"
    NONE = "none"


class AgentChatMessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatSessionEntrypoint(StrEnum):
    GENERAL_DELEGATION = "general_delegation"
    DIRECT_SPECIALIST = "direct_specialist"
    PROJECT_GENERAL = "project_general"


class ChatSessionDomain(StrEnum):
    UNKNOWN = "unknown"
    MARKETING = "marketing"
    PROGRAMMER = "programmer"
    MEDIA = "media"


class ChatSessionStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ChatAuditEventType(StrEnum):
    SESSION_CREATED = "chat.session.created"
    SESSION_ARCHIVED = "chat.session.archived"
    MESSAGE_USER_APPENDED = "chat.message.user_appended"
    MESSAGE_ASSISTANT_APPENDED = "chat.message.assistant_appended"
    RUN_STARTED = "chat.run.started"
    RUN_SUCCEEDED = "chat.run.succeeded"
    RUN_FAILED = "chat.run.failed"
    BLOCK_ACTION_REQUESTED = "chat.block_action.requested"
    BLOCK_ACTION_SUCCEEDED = "chat.block_action.succeeded"
    BLOCK_ACTION_FAILED = "chat.block_action.failed"
    SEARCH_SESSIONS = "chat.search.sessions"
    SEARCH_MESSAGES = "chat.search.messages"


class ChatSession(BaseModel):
    """Specialist chat session (Phase AI.19) Р Р†Р вЂљРІР‚Сњ session-scoped history, not long-term memory."""

    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    agent_id: UUID | None = None
    entrypoint: ChatSessionEntrypoint = ChatSessionEntrypoint.DIRECT_SPECIALIST
    domain: ChatSessionDomain = ChatSessionDomain.UNKNOWN
    title: str | None = None
    status: ChatSessionStatus = ChatSessionStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ChatSessionListItem(ChatSession):
    """Session row for list UIs (Phase AI.20) Р Р†Р вЂљРІР‚Сњ preview fields computed from messages."""

    last_message_preview: str | None = None
    last_message_at: datetime | None = None
    message_count: int = 0
    unread_count: int = 0


class MarketingSpecialistType(StrEnum):
    """Marketing department specialist roles (Phase AI.27 registry; v2 expansion AI.110)."""

    STRATEGIST = "strategist"
    RESEARCHER = "researcher"
    COPYWRITER = "copywriter"
    CONTENT_PLANNER = "content_planner"
    ANALYST = "analyst"
    CRITIC = "critic"
    OFFER_STRATEGIST = "offer_strategist"
    FUNNEL_ARCHITECT = "funnel_architect"
    LEAD_MAGNET_SPECIALIST = "lead_magnet_specialist"
    SALES_COPYWRITER = "sales_copywriter"
    EMAIL_DM_SPECIALIST = "email_dm_specialist"
    CRO_SPECIALIST = "cro_specialist"
    SMM_STRATEGIST = "smm_strategist"
    AD_CREATIVE_STRATEGIST = "ad_creative_strategist"


class MarketingExecutionMode(StrEnum):
    """Orchestrator execution mode Р Р†Р вЂљРІР‚Сњ AI.27 allows planning only."""

    PLANNING = "planning"


class MarketingSpecialistTask(BaseModel):
    specialist: MarketingSpecialistType
    objective: str
    expected_output: str


class MarketingExecutionPlan(BaseModel):
    """Structured marketing department plan (Phase AI.27) Р Р†Р вЂљРІР‚Сњ not executed in this phase."""

    goal: str
    project_context: dict[str, Any] = Field(default_factory=dict)
    specialist_tasks: list[MarketingSpecialistTask] = Field(default_factory=list)
    execution_mode: MarketingExecutionMode = MarketingExecutionMode.PLANNING
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MarketingPlanStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    ARCHIVED = "archived"


class ScenarioTemplate(BaseModel):
    """Product scenario template (Phase AI.127) Р Р†Р вЂљРІР‚Сњ registry only, no execution."""

    id: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=256)
    industry: str = Field(..., min_length=1, max_length=256)
    goal: str = Field(..., min_length=1, max_length=4096)
    required_specialists: list[MarketingSpecialistType] = Field(default_factory=list)
    default_plan_tasks: list[MarketingSpecialistTask] = Field(default_factory=list)
    expected_artifacts: list[str] = Field(default_factory=list)


class ScenarioWizardRunStatus(StrEnum):
    """Scenario wizard lifecycle (Phase AI.137)."""

    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScenarioWizardRun(BaseModel):
    """Manual scenario wizard run Р Р†Р вЂљРІР‚Сњ one advance step at a time (Phase AI.137)."""

    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    scenario_id: str
    scenario_name: str
    source_campaign_id: UUID | None = None
    status: ScenarioWizardRunStatus = ScenarioWizardRunStatus.DRAFT
    current_step: str
    step_results: dict[str, Any] = Field(default_factory=dict)
    failure_reason: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None


class CampaignStatus(StrEnum):
    """Business campaign lifecycle (Phase AI.147)."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Campaign(BaseModel):
    """Business operating system campaign container (Phase AI.147)."""

    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    name: str
    goal: str
    scenario_id: str | None = None
    status: CampaignStatus = CampaignStatus.DRAFT
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CampaignMetrics(BaseModel):
    """Aggregate counts for a campaign (Phase AI.152)."""

    plans_total: int = 0
    outputs_total: int = 0
    assets_total: int = 0
    media_total: int = 0
    packages_total: int = 0
    jobs_total: int = 0
    wizard_runs_total: int = 0


class CampaignDashboard(BaseModel):
    """Campaign dashboard read model (Phase AI.150)."""

    campaign: Campaign
    metrics: CampaignMetrics
    latest_plan_status: str | None = None
    latest_execution_status: str | None = None


class CampaignHealthStatus(StrEnum):
    """Campaign control center health (Phase AI.159)."""

    HEALTHY = "healthy"
    WAITING_FOR_USER = "waiting_for_user"
    BLOCKED = "blocked"
    FAILED = "failed"
    COMPLETED = "completed"


class CampaignNextActionType(StrEnum):
    """Recommended next manual step Р Р†Р вЂљРІР‚Сњ no auto-execution (Phase AI.158)."""

    ATTACH_SCENARIO = "attach_scenario"
    START_WIZARD = "start_wizard"
    ADVANCE_WIZARD = "advance_wizard"
    APPROVE_PLAN = "approve_plan"
    START_EXECUTION = "start_execution"
    EXECUTE_NEXT_SPECIALIST = "execute_next_specialist"
    APPROVE_COPYWRITER_OUTPUT = "approve_copywriter_output"
    CREATE_CONTENT_ASSET = "create_content_asset"
    APPROVE_ASSET = "approve_asset"
    CREATE_MEDIA_BRIEF = "create_media_brief"
    APPROVE_MEDIA_BRIEF = "approve_media_brief"
    CREATE_PUBLICATION_PACKAGE = "create_publication_package"
    SCHEDULE_OR_DRY_RUN = "schedule_or_dry_run"
    NONE = "none"


class CampaignTimelineEventType(StrEnum):
    """Read-only campaign timeline entry kinds (Phase AI.157)."""

    WIZARD_STEP = "wizard_step"
    PLAN = "plan"
    EXECUTION_RUN = "execution_run"
    SPECIALIST_OUTPUT = "specialist_output"
    CONTENT_ASSET = "content_asset"
    MEDIA_BRIEF = "media_brief"
    PUBLICATION_PACKAGE = "publication_package"
    PUBLICATION_JOB = "publication_job"
    SKILL_RUN = "skill_run"


class CampaignTimelineEvent(BaseModel):
    """Single read-only timeline event (Phase AI.157)."""

    event_type: CampaignTimelineEventType
    label: str
    status: str | None = None
    resource_id: UUID
    occurred_at: datetime
    safe_summary: str | None = None


class CampaignNextAction(BaseModel):
    """Recommendation only Р Р†Р вЂљРІР‚Сњ user must invoke existing APIs (Phase AI.158)."""

    action_type: CampaignNextActionType
    label: str
    safe_description: str
    resource_ids: dict[str, str] = Field(default_factory=dict)


class CampaignHealth(BaseModel):
    """Campaign health snapshot (Phase AI.159)."""

    status: CampaignHealthStatus
    blocking_reason: str | None = None
    progress_percent: int = Field(default=0, ge=0, le=100)


class MarketingToolType(StrEnum):
    """Marketing data tool identifiers (Phase AI.217)."""

    WORDSTAT = "wordstat"
    METRICA = "metrica"
    IMAGE_GENERATION = "image_generation"


class MarketingToolCallStatus(StrEnum):
    """Marketing tool call lifecycle (Phase AI.217)."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MarketingToolSuggestion(BaseModel):
    """Read-only tool recommendation Р Р†Р вЂљРІР‚Сњ no auto-call (Phase AI.222)."""

    tool_type: MarketingToolType
    label: str
    safe_description: str
    recommended: bool = True


class WordstatToolInput(BaseModel):
    """Wordstat tool input (Phase AI.218)."""

    query: str = Field(..., min_length=1, max_length=512)
    region: str | None = Field(default=None, max_length=128)
    device: str | None = Field(default=None, max_length=32)
    report_type: str = Field(default="one", pattern="^(one|short|long)$")


class MetricaToolInput(BaseModel):
    """Metrica tool input (Phase AI.219)."""

    counter_id: str | None = Field(default=None, max_length=64)
    metrics: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)
    date1: str | None = Field(default=None, max_length=32)
    date2: str | None = Field(default=None, max_length=32)
    filtersCustom: str | None = Field(default=None, max_length=512)
    natural_language: str | None = Field(default=None, max_length=1024)


class ImageGenerationToolInput(BaseModel):
    """Image generation tool input (Phase AI.220)."""

    prompt: str = Field(..., min_length=1, max_length=4096)
    user_id: str | None = Field(default=None, max_length=128)
    aspect_ratio: str | None = Field(default=None, max_length=16)
    image_size: str | None = Field(default=None, max_length=32)


class MarketingToolCall(BaseModel):
    """Persisted marketing data tool call (Phase AI.217)."""

    id: UUID
    owner_id: UUID
    project_id: UUID
    tool_type: MarketingToolType
    input_payload: dict[str, Any] = Field(default_factory=dict)
    output_payload: dict[str, Any] | None = None
    status: MarketingToolCallStatus
    safe_metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class MarketingSkillType(StrEnum):
    """Marketing skill identifiers (Phase AI.227)."""

    SEGMENT_RESEARCH = "segment_research"
    MEANING_UNPACKING = "meaning_unpacking"
    OFFER_PACKAGING = "offer_packaging"
    OFFER_JUSTIFICATION = "offer_justification"
    WORDSTAT_RESEARCH = "wordstat_research"
    METRICA_ANALYSIS = "metrica_analysis"
    VISUAL_REPORT = "visual_report"


class MarketingSkillRunStatus(StrEnum):
    """Marketing skill run lifecycle (Phase AI.227)."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MarketingSkillSuggestion(BaseModel):
    """Read-only skill recommendation Р Р†Р вЂљРІР‚Сњ no auto-run (Phase AI.234)."""

    skill_type: MarketingSkillType
    label: str
    safe_description: str
    recommended: bool = True


class MarketingSkillDefinition(BaseModel):
    """Skill registry entry exposed to clients (Phase AI.228)."""

    skill_type: MarketingSkillType
    name: str
    purpose: str
    required_inputs: list[str] = Field(default_factory=list)
    optional_tools: list[MarketingToolType] = Field(default_factory=list)
    output_type: str
    out_of_scope: list[str] = Field(default_factory=list)


class MarketingSkillRun(BaseModel):
    """Persisted marketing skill run (Phase AI.227)."""

    id: UUID
    owner_id: UUID
    project_id: UUID
    campaign_id: UUID | None = None
    skill_type: MarketingSkillType
    status: MarketingSkillRunStatus
    input_payload: dict[str, Any] = Field(default_factory=dict)
    output_payload: dict[str, Any] | None = None
    used_tool_call_ids: list[UUID] = Field(default_factory=list)
    safe_metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class CampaignSkillSuggestion(BaseModel):
    """Campaign-level skill recommendation (Phase AI.237)."""

    skill_type: MarketingSkillType
    reason: str
    priority: int = Field(ge=1, le=10)
    expected_output: str
    related_brief_fields: list[str] = Field(default_factory=list)
    related_next_action: CampaignNextActionType | None = None
    label: str = ""


class CampaignSkillContext(BaseModel):
    """Safe aggregated skill outputs on campaign (Phase AI.240)."""

    segment_summary: dict[str, Any] | None = None
    offer_summary: dict[str, Any] | None = None
    demand_summary: dict[str, Any] | None = None
    analytics_summary: dict[str, Any] | None = None
    source_run_ids: dict[str, str] = Field(default_factory=dict)
    updated_at: datetime | None = None


class CampaignSupervisorSeverity(StrEnum):
    """Supervisor finding severity (Phase AI.247)."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class CampaignSupervisorCategory(StrEnum):
    """Supervisor finding category (Phase AI.247)."""

    BRIEF = "brief"
    STRATEGY = "strategy"
    OFFER = "offer"
    CONTENT = "content"
    MEDIA = "media"
    PUBLISHING = "publishing"
    DATA = "data"
    EXECUTION = "execution"


class CampaignSupervisorFinding(BaseModel):
    """Read-only campaign quality finding (Phase AI.247)."""

    severity: CampaignSupervisorSeverity
    category: CampaignSupervisorCategory
    title: str
    description: str
    affected_resource_type: str | None = None
    affected_resource_id: UUID | None = None
    recommended_action_type: CampaignActionType | None = None
    safe_metadata: dict[str, Any] = Field(default_factory=dict)


class CampaignSupervisorReport(BaseModel):
    """Full campaign supervisor quality report (Phase AI.247)."""

    campaign_id: UUID
    health_score: int = Field(ge=0, le=100)
    findings: list[CampaignSupervisorFinding] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommended_next_actions: list[CampaignActionType] = Field(default_factory=list)


class CampaignResourceIds(BaseModel):
    """Linked artifact ids for deep links (Phase AI.160)."""

    wizard_run_id: UUID | None = None
    marketing_plan_id: UUID | None = None
    execution_run_id: UUID | None = None
    copywriter_output_id: UUID | None = None
    content_asset_id: UUID | None = None
    media_brief_id: UUID | None = None
    media_asset_id: UUID | None = None
    publication_package_id: UUID | None = None
    publication_package_job_id: UUID | None = None


class CampaignFailureRecoveryHint(BaseModel):
    """Failure recovery guidance Р Р†Р вЂљРІР‚Сњ read-only, no auto-recovery (Phase AI.162)."""

    failed_object_type: str
    failed_object_id: UUID
    error_code: str | None = None
    suggested_recovery: str


class CampaignControlCenter(BaseModel):
    """Campaign control center aggregate (Phase AI.160)."""

    campaign: Campaign
    health: CampaignHealth
    next_action: CampaignNextAction
    timeline: list[CampaignTimelineEvent] = Field(default_factory=list)
    metrics: CampaignMetrics
    resource_ids: CampaignResourceIds
    safe_warnings: list[str] = Field(default_factory=list)
    recovery_hint: CampaignFailureRecoveryHint | None = None
    primary_action: CampaignAction | None = None
    available_actions: list[CampaignAction] = Field(default_factory=list)
    tool_suggestions: list[MarketingToolSuggestion] = Field(default_factory=list)
    skill_suggestions: list[CampaignSkillSuggestion] = Field(default_factory=list)
    latest_skill_runs: list[MarketingSkillRun] = Field(default_factory=list)
    skill_context: CampaignSkillContext | None = None
    supervisor_health_score: int = Field(default=100, ge=0, le=100)
    supervisor_findings_count: int = Field(default=0, ge=0)
    critical_findings_count: int = Field(default=0, ge=0)
    top_findings: list[CampaignSupervisorFinding] = Field(default_factory=list)
    workflow_suggestions: list[CampaignWorkflowSuggestion] = Field(default_factory=list)
    active_workflow: CampaignWorkflowRunSummary | None = None


class CampaignControlCenterSummary(BaseModel):
    """Lightweight list row for campaign filters (Phase AI.163)."""

    campaign: Campaign
    health: CampaignHealth
    next_action_type: CampaignNextActionType


class CampaignActionType(StrEnum):
    """Executable campaign actions (Phase AI.167Р Р†Р вЂљРІР‚СљAI.168)."""

    START_WIZARD = "start_wizard"
    ADVANCE_WIZARD = "advance_wizard"
    APPROVE_PLAN = "approve_plan"
    START_EXECUTION = "start_execution"
    EXECUTE_NEXT_SPECIALIST = "execute_next_specialist"
    APPROVE_COPYWRITER_OUTPUT = "approve_copywriter_output"
    CREATE_CONTENT_ASSET = "create_content_asset"
    SUBMIT_ASSET_REVIEW = "submit_asset_review"
    APPROVE_ASSET = "approve_asset"
    CREATE_MEDIA_BRIEF = "create_media_brief"
    SUBMIT_MEDIA_BRIEF_REVIEW = "submit_media_brief_review"
    APPROVE_MEDIA_BRIEF = "approve_media_brief"
    CREATE_PUBLICATION_PACKAGE = "create_publication_package"
    SUBMIT_PACKAGE_REVIEW = "submit_package_review"
    APPROVE_PACKAGE = "approve_package"
    CREATE_PUBLICATION_JOB = "create_publication_job"
    SCHEDULE_JOB = "schedule_job"
    DRY_RUN_DISPATCH = "dry_run_dispatch"
    RUN_SEGMENT_RESEARCH = "run_segment_research"
    RUN_MEANING_UNPACKING = "run_meaning_unpacking"
    RUN_OFFER_PACKAGING = "run_offer_packaging"
    RUN_OFFER_JUSTIFICATION = "run_offer_justification"
    RUN_WORDSTAT_RESEARCH = "run_wordstat_research"
    RUN_METRICA_ANALYSIS = "run_metrica_analysis"
    RUN_VISUAL_REPORT = "run_visual_report"


class CampaignAction(BaseModel):
    """Explicit action button descriptor (Phase AI.167)."""

    type: CampaignActionType
    label: str
    enabled: bool = True
    disabled_reason: str | None = None
    target_resource_type: str | None = None
    target_resource_id: UUID | None = None
    confirmation_required: bool = False
    safe_payload: dict[str, Any] = Field(default_factory=dict)


class CampaignActionResultStatus(StrEnum):
    """Campaign action execution outcome (Phase AI.171)."""

    SUCCEEDED = "succeeded"
    ALREADY_APPLIED = "already_applied"
    FAILED = "failed"


class CampaignActionResult(BaseModel):
    """Result of POST .../actions/{action_type}/execute (Phase AI.171)."""

    status: CampaignActionResultStatus
    message: str
    action_type: CampaignActionType
    created_resource_type: str | None = None
    created_resource_id: UUID | None = None
    updated_resource_type: str | None = None
    updated_resource_id: UUID | None = None
    next_action_after: CampaignNextAction
    control_center_snapshot: CampaignControlCenter | None = None


class CampaignWorkflowRunStatus(StrEnum):
    """Campaign workflow run lifecycle (Phase AI.260)."""

    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class CampaignWorkflowStepStatus(StrEnum):
    """Read-only step checklist state (Phase AI.262)."""

    PENDING = "pending"
    CURRENT = "current"
    COMPLETED = "completed"


class CampaignWorkflowStep(BaseModel):
    """Single workflow step Р Р†Р вЂљРІР‚Сњ recommends next action only (Phase AI.262)."""

    step_id: str = Field(..., min_length=1, max_length=128)
    label: str = Field(..., min_length=1, max_length=256)
    safe_description: str = Field(..., min_length=1, max_length=4096)
    recommended_action_type: CampaignActionType | None = None
    recommended_skill_type: MarketingSkillType | None = None
    recommended_tool_type: MarketingToolType | None = None


class CampaignWorkflowTemplate(BaseModel):
    """Reusable campaign business process template (Phase AI.257)."""

    id: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=256)
    goal: str = Field(..., min_length=1, max_length=4096)
    applicable_scenarios: list[str] = Field(default_factory=list)
    required_brief_fields: list[str] = Field(default_factory=list)
    recommended_skills: list[MarketingSkillType] = Field(default_factory=list)
    recommended_tools: list[MarketingToolType] = Field(default_factory=list)
    steps: list[CampaignWorkflowStep] = Field(default_factory=list)
    expected_artifacts: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)


class CampaignWorkflowSuggestion(BaseModel):
    """Read-only workflow template recommendation (Phase AI.259)."""

    template_id: str = Field(..., min_length=1, max_length=128)
    label: str = Field(..., min_length=1, max_length=256)
    reason: str = Field(..., min_length=1, max_length=4096)
    priority: int = Field(default=5, ge=1, le=10)
    expected_artifacts: list[str] = Field(default_factory=list)


class CampaignWorkflowRun(BaseModel):
    """Persisted workflow run Р Р†Р вЂљРІР‚Сњ checklist only, no auto-execution (Phase AI.260)."""

    id: UUID
    owner_id: UUID
    project_id: UUID
    campaign_id: UUID
    template_id: str = Field(..., min_length=1, max_length=128)
    status: CampaignWorkflowRunStatus
    current_step_index: int = Field(default=0, ge=0)
    step_results: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class CampaignWorkflowStepView(BaseModel):
    """Workflow step with inferred progress for Control Center UI (Phase AI.263)."""

    step_index: int = Field(ge=0)
    step_id: str
    label: str
    safe_description: str
    status: CampaignWorkflowStepStatus
    recommended_action_type: CampaignActionType | None = None
    recommended_skill_type: MarketingSkillType | None = None
    recommended_tool_type: MarketingToolType | None = None


class CampaignWorkflowRunSummary(BaseModel):
    """Active workflow run aggregate for Control Center (Phase AI.263)."""

    run: CampaignWorkflowRun
    template_name: str
    template_goal: str
    steps: list[CampaignWorkflowStepView] = Field(default_factory=list)
    progress_percent: int = Field(default=0, ge=0, le=100)


class BusinessIntent(BaseModel):
    """Parsed business goal from user message (Phase AI.177)."""

    goal: str
    industry: str | None = None
    business_type: str | None = None
    campaign_type: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    recommended_scenario: str | None = None


class ScenarioRecommendation(BaseModel):
    """Scenario pick from intent (Phase AI.179)."""

    recommended_scenario: str
    alternative_scenarios: list[str] = Field(default_factory=list)
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)


class BusinessOperatorCreateCampaignResponse(BaseModel):
    """Response for POST .../business-operator/create-campaign (Phase AI.182)."""

    campaign: Campaign
    intent: BusinessIntent
    recommendation: ScenarioRecommendation
    control_center: CampaignControlCenter


class BusinessOperatorClarification(BaseModel):
    """Clarifying question when confidence gate not passed (Phase AI.187)."""

    question: str
    reason: str
    missing_field: str
    options: list[str] = Field(default_factory=list)
    required: bool = True


class BusinessOperatorIntentSource(StrEnum):
    """How business intent was resolved (Phase AI.202)."""

    RULE_BASED = "rule_based"
    LLM_FALLBACK = "llm_fallback"
    CLARIFICATION = "clarification"


class BusinessOperatorLLMIntent(BaseModel):
    """Structured LLM intent classification output (Phase AI.197)."""

    goal: str
    industry: str | None = None
    business_type: str | None = None
    campaign_type: str | None = None
    suggested_scenario: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning_summary: str
    missing_fields: list[str] = Field(default_factory=list)


class ScenarioExplanation(BaseModel):
    """Human-readable scenario choice explanation (Phase AI.190)."""

    why_this_scenario: str
    alternatives: list[str] = Field(default_factory=list)
    what_will_be_created: str
    what_user_must_confirm: str


class BusinessOperatorCampaignPreview(BaseModel):
    """Pre-create campaign preview Р Р†Р вЂљРІР‚Сњ no DB objects (Phase AI.191)."""

    campaign_name: str
    goal: str
    scenario_id: str
    scenario_name: str
    specialists_count: int = Field(ge=0)
    expected_artifacts: list[str] = Field(default_factory=list)


class CampaignBriefStatus(StrEnum):
    """Campaign brief lifecycle (Phase AI.211)."""

    DRAFT = "draft"
    CONFIRMED = "confirmed"
    ARCHIVED = "archived"


class CampaignBriefQuestion(BaseModel):
    """Missing brief field question (Phase AI.209)."""

    field: str
    question: str
    options: list[str] = Field(default_factory=list)
    required: bool = True


class CampaignBriefFields(BaseModel):
    """Editable campaign brief fields (Phase AI.207)."""

    business_name: str | None = None
    industry: str | None = None
    offer: str | None = None
    target_audience: str | None = None
    geography: str | None = None
    channels: list[str] = Field(default_factory=list)
    budget_range: str | None = None
    deadline: str | None = None
    constraints: str | None = None
    success_metric: str | None = None
    goal: str | None = None


class CampaignBriefCompleteness(BaseModel):
    """Brief completeness evaluation (Phase AI.208)."""

    score: int = Field(ge=0, le=100)
    threshold: int = Field(ge=0, le=100)
    passed: bool
    missing_questions: list[CampaignBriefQuestion] = Field(default_factory=list)


class CampaignBrief(CampaignBriefFields):
    """Persisted campaign brief linked to operator intake (Phase AI.211)."""

    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    campaign_id: UUID | None = None
    source_intent: dict[str, Any] = Field(default_factory=dict)
    source_scenario_id: str | None = None
    status: CampaignBriefStatus = CampaignBriefStatus.DRAFT
    completeness_score: int = Field(default=0, ge=0, le=100)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Commercial MVP P0.1 Р Р†Р вЂљРІР‚Сњ ProjectBrief (durable Marketsynth intake)
# Distinct from CampaignBrief (operator campaign questionnaire).
# ---------------------------------------------------------------------------


class ProjectBriefStatus(StrEnum):
    """ProjectBrief lifecycle Р Р†Р вЂљРІР‚Сњ not Project lifecycle, not Business Verdict."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class ProjectBriefReadinessStatus(StrEnum):
    """Intake readiness snapshot Р Р†Р вЂљРІР‚Сњ not Business Verdict."""

    READY = "ready"
    CONDITIONALLY_READY = "conditionally_ready"
    INSUFFICIENT_DATA = "insufficient_data"


class MoneyValueMode(StrEnum):
    """Money / value uncertainty Р Р†Р вЂљРІР‚Сњ unknown must never coerce to zero."""

    EXACT = "exact"
    RANGE = "range"
    UNKNOWN = "unknown"


class MoneyValue(BaseModel):
    """Typed money representation for ProjectBrief economics / product price."""

    mode: MoneyValueMode = MoneyValueMode.UNKNOWN
    exact: str | None = None
    min: str | None = None
    max: str | None = None


class ProjectBriefBasicsSection(BaseModel):
    project_name: str = Field(default="", max_length=256)
    idea_description: str = Field(default="", max_length=8000)
    business_type: str = Field(default="", max_length=64)
    project_stage: str = Field(default="", max_length=64)
    geography: str = Field(default="", max_length=512)
    preferred_language: str = Field(default="ru", max_length=16)


class ProjectBriefProductSection(BaseModel):
    product_or_service: str = Field(default="", max_length=4000)
    customer_problem: str = Field(default="", max_length=4000)
    value_proposition: str = Field(default="", max_length=4000)
    price: MoneyValue = Field(default_factory=MoneyValue)
    price_type: str = Field(default="", max_length=64)
    price_value: str | None = Field(default=None, max_length=128)
    price_min: str | None = Field(default=None, max_length=128)
    price_max: str | None = Field(default=None, max_length=128)
    delivery_model: str = Field(default="", max_length=2000)
    differentiators: str = Field(default="", max_length=4000)
    limitations: str = Field(default="", max_length=4000)


class ProjectBriefMarketSection(BaseModel):
    target_market: str = Field(default="", max_length=4000)
    geography: str = Field(default="", max_length=512)
    known_competitors: str = Field(default="", max_length=4000)
    competitor_urls: str = Field(default="", max_length=4000)
    market_assumptions: str = Field(default="", max_length=4000)
    demand_evidence: str = Field(default="", max_length=4000)
    seasonality: str = Field(default="", max_length=2000)
    restrictions: str = Field(default="", max_length=4000)


class ProjectBriefAudienceSegment(BaseModel):
    id: str = Field(default="", max_length=64)
    label: str = Field(default="", max_length=256)
    notes: str = Field(default="", max_length=2000)


class ProjectBriefAudienceSection(BaseModel):
    business_model: str = Field(default="", max_length=32)
    segments: list[ProjectBriefAudienceSegment] = Field(default_factory=list)
    decision_maker: str = Field(default="", max_length=2000)
    buyer_user_distinction: str = Field(default="", max_length=2000)
    geography: str = Field(default="", max_length=512)
    pains: str = Field(default="", max_length=4000)
    objections: str = Field(default="", max_length=4000)
    current_research: str = Field(default="", max_length=4000)


class ProjectBriefEconomicsSection(BaseModel):
    launch_budget: MoneyValue = Field(default_factory=MoneyValue)
    monthly_marketing_budget: MoneyValue = Field(default_factory=MoneyValue)
    target_revenue: MoneyValue = Field(default_factory=MoneyValue)
    payback_period: str = Field(default="", max_length=256)
    average_order_value: MoneyValue = Field(default_factory=MoneyValue)
    gross_margin: str = Field(default="", max_length=128)
    team_size: str = Field(default="", max_length=128)
    internal_resources: str = Field(default="", max_length=4000)
    launch_deadline: str = Field(default="", max_length=256)
    critical_constraints: str = Field(default="", max_length=4000)


class ProjectBriefMaterialItem(BaseModel):
    """Metadata only Р Р†Р вЂљРІР‚Сњ no file contents, binaries, or remote fetches."""

    title: str = Field(default="", max_length=512)
    type: str = Field(default="", max_length=64)
    filename: str | None = Field(default=None, max_length=512)
    url: str | None = Field(default=None, max_length=2000)
    local_reference_label: str | None = Field(default=None, max_length=512)
    status: str = Field(default="noted", max_length=64)
    notes: str | None = Field(default=None, max_length=2000)


class ProjectBriefMaterialsSummary(BaseModel):
    website_url: str = Field(default="", max_length=2000)
    social_profiles: str = Field(default="", max_length=4000)
    items: list[ProjectBriefMaterialItem] = Field(default_factory=list)


class ProjectBriefContent(BaseModel):
    """Typed decision-critical sections for create/update."""

    language: str = Field(default="ru", max_length=16)
    project_basics: ProjectBriefBasicsSection = Field(
        default_factory=ProjectBriefBasicsSection,
    )
    product: ProjectBriefProductSection = Field(default_factory=ProjectBriefProductSection)
    market: ProjectBriefMarketSection = Field(default_factory=ProjectBriefMarketSection)
    audience: ProjectBriefAudienceSection = Field(
        default_factory=ProjectBriefAudienceSection,
    )
    economics: ProjectBriefEconomicsSection = Field(
        default_factory=ProjectBriefEconomicsSection,
    )
    materials_summary: ProjectBriefMaterialsSummary = Field(
        default_factory=ProjectBriefMaterialsSummary,
    )
    assumptions: list[str] = Field(default_factory=list)
    missing_data: list[str] = Field(default_factory=list)
    readiness_status: ProjectBriefReadinessStatus = (
        ProjectBriefReadinessStatus.INSUFFICIENT_DATA
    )
    readiness_reasons: list[str] = Field(default_factory=list)


class ProjectBrief(ProjectBriefContent):
    """Durable project-scoped intake SoT (Commercial MVP P0.1)."""

    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    version: int = Field(ge=1)
    status: ProjectBriefStatus = ProjectBriefStatus.DRAFT
    input_fingerprint: str = Field(max_length=128)
    supersedes_brief_id: UUID | None = None
    submitted_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectBriefCreateRequest(ProjectBriefContent):
    """POST body Р Р†Р вЂљРІР‚Сњ create draft ProjectBrief."""


class ProjectBriefUpdateRequest(BaseModel):
    """PATCH body Р Р†Р вЂљРІР‚Сњ update draft only; omitted fields untouched when None."""

    language: str | None = Field(default=None, max_length=16)
    project_basics: ProjectBriefBasicsSection | None = None
    product: ProjectBriefProductSection | None = None
    market: ProjectBriefMarketSection | None = None
    audience: ProjectBriefAudienceSection | None = None
    economics: ProjectBriefEconomicsSection | None = None
    materials_summary: ProjectBriefMaterialsSummary | None = None
    assumptions: list[str] | None = None
    missing_data: list[str] | None = None
    readiness_status: ProjectBriefReadinessStatus | None = None
    readiness_reasons: list[str] | None = None


# ---------------------------------------------------------------------------
# Commercial MVP P0.2 Р Р†Р вЂљРІР‚Сњ Investigation aggregate (no Source/Evidence SoT yet)
# ---------------------------------------------------------------------------


class InvestigationStatus(StrEnum):
    """Investigation lifecycle Р Р†Р вЂљРІР‚Сњ not Business Verdict, not Agent Run."""

    DRAFT = "draft"
    READY = "ready"
    ACTIVE = "active"
    BLOCKED = "blocked"
    UNDER_REVIEW = "under_review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"


class InvestigationReadinessStatus(StrEnum):
    """Investigation readiness Р Р†Р вЂљРІР‚Сњ not Business Verdict."""

    NOT_READY = "not_ready"
    CONDITIONALLY_READY = "conditionally_ready"
    READY_FOR_REVIEW = "ready_for_review"


class InvestigationStageId(StrEnum):
    """Frozen Product Alpha pipeline stages."""

    PROJECT_CONTEXT = "project_context"
    MARKET_RESEARCH = "market_research"
    COMPETITOR_ANALYSIS = "competitor_analysis"
    AUDIENCE_ANALYSIS = "audience_analysis"
    DEMAND_SIGNALS = "demand_signals"
    ECONOMICS = "economics"
    RISK_ASSESSMENT = "risk_assessment"
    EVIDENCE_REVIEW = "evidence_review"
    VERDICT_PREPARATION = "verdict_preparation"


class InvestigationStageStatus(StrEnum):
    NOT_STARTED = "not_started"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    NEEDS_REVIEW = "needs_review"


class InvestigationStageState(BaseModel):
    stage_id: InvestigationStageId
    status: InvestigationStageStatus = InvestigationStageStatus.NOT_STARTED
    blocked_reason: str | None = Field(default=None, max_length=2000)


class InvestigationCreateRequest(BaseModel):
    """Create Investigation draft from a submitted ProjectBrief."""

    project_brief_id: UUID
    project_brief_version: int = Field(ge=1)
    input_fingerprint: str = Field(min_length=8, max_length=128)


class InvestigationUpdateRequest(BaseModel):
    """Limited PATCH for draft/ready/blocked fields Р Р†Р вЂљРІР‚Сњ not completed/superseded."""

    current_stage: InvestigationStageId | None = None
    readiness_status: InvestigationReadinessStatus | None = None
    readiness_reasons: list[str] | None = None
    blocked_reason: str | None = Field(default=None, max_length=2000)
    metadata: dict[str, Any] | None = None


class InvestigationStageUpdateRequest(BaseModel):
    status: InvestigationStageStatus
    blocked_reason: str | None = Field(default=None, max_length=2000)


class Investigation(BaseModel):
    """Durable research lifecycle for one Project + exact Brief version."""

    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    project_brief_id: UUID
    project_brief_version: int = Field(ge=1)
    input_fingerprint: str = Field(max_length=128)
    version: int = Field(ge=1)
    status: InvestigationStatus = InvestigationStatus.DRAFT
    current_stage: InvestigationStageId = InvestigationStageId.PROJECT_CONTEXT
    stages: list[InvestigationStageState] = Field(default_factory=list)
    readiness_status: InvestigationReadinessStatus = (
        InvestigationReadinessStatus.NOT_READY
    )
    readiness_reasons: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    blocked_reason: str | None = None
    supersedes_investigation_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SourceType(StrEnum):
    """Where the information physically originated (format/channel)."""

    WEBSITE = "website"
    COMPETITOR_WEBSITE = "competitor_website"
    MARKET_REPORT = "market_report"
    PUBLIC_DATASET = "public_dataset"
    ANALYTICS_EXPORT = "analytics_export"
    UPLOADED_DOCUMENT = "uploaded_document"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    INTERVIEW = "interview"
    USER_STATEMENT = "user_statement"
    CUSTOMER_INTERVIEW = "customer_interview"
    CRM_EXPORT = "crm_export"
    API_REFERENCE = "api_reference"
    INTERNAL_CALCULATION = "internal_calculation"
    INTERNAL_DOCUMENT = "internal_document"
    OTHER = "other"


class SourceProvenanceType(StrEnum):
    """Origin authority Р Р†Р вЂљРІР‚Сњ not AI confidence, not Business Verdict."""

    OFFICIAL = "official"
    PRIMARY = "primary"
    SECONDARY = "secondary"
    USER_PROVIDED = "user_provided"
    UPLOADED = "uploaded"
    INTERNAL = "internal"
    GENERATED = "generated"
    UNKNOWN = "unknown"


class SourceCapability(StrEnum):
    """Format capability Р Р†Р вЂљРІР‚Сњ not extracted meaning."""

    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    STRUCTURED_DATA = "structured_data"
    WEBPAGE = "webpage"
    PDF = "pdf"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    API_PAYLOAD = "api_payload"


class SourceFreshnessStatus(StrEnum):
    CURRENT = "current"
    ACCEPTABLE = "acceptable"
    OUTDATED = "outdated"
    UNKNOWN = "unknown"


class SourceReliabilityLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNVERIFIED = "unverified"


class SourceStatus(StrEnum):
    REGISTERED = "registered"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class InvestigationSourceLinkStatus(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXCLUDED = "excluded"


class SourceCreateRequest(BaseModel):
    """Register immutable Source provenance Р Р†Р вЂљРІР‚Сњ no content/analysis/evidence."""

    source_type: SourceType
    provenance_type: SourceProvenanceType = SourceProvenanceType.UNKNOWN
    title: str = Field(min_length=1, max_length=500)
    origin: str = Field(default="", max_length=500)
    url: str | None = Field(default=None, max_length=2000)
    domain: str | None = Field(default=None, max_length=255)
    publisher: str | None = Field(default=None, max_length=500)
    language: str | None = Field(default=None, max_length=32)
    country: str | None = Field(default=None, max_length=64)
    published_at: datetime | None = None
    captured_at: datetime | None = None
    accessed_at: datetime | None = None
    freshness_status: SourceFreshnessStatus | None = None
    content_hash: str | None = Field(default=None, max_length=128)
    etag: str | None = Field(default=None, max_length=255)
    license_type: str | None = Field(default=None, max_length=128)
    capabilities: list[SourceCapability] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    attach_to_investigation_id: UUID | None = None
    link_purpose: str | None = Field(default=None, max_length=500)


class SourceSupersedeRequest(SourceCreateRequest):
    """New Source version replacing an immutable prior snapshot."""

    pass


class SourceReliabilityReviewRequest(BaseModel):
    reliability_level: SourceReliabilityLevel
    review_note: str | None = Field(default=None, max_length=2000)


class SourceArchiveRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


class InvestigationSourceLinkCreateRequest(BaseModel):
    purpose: str | None = Field(default=None, max_length=500)
    investigation_area: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=2000)
    status: InvestigationSourceLinkStatus = InvestigationSourceLinkStatus.ACCEPTED


class InvestigationSourceLinkUpdateRequest(BaseModel):
    purpose: str | None = Field(default=None, max_length=500)
    investigation_area: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=2000)
    status: InvestigationSourceLinkStatus | None = None


class SourceSnapshot(BaseModel):
    """Architectural contract: one captured state of an origin (not a separate table)."""

    source_id: UUID
    project_id: UUID
    version: int = Field(ge=1)
    fingerprint: str
    content_hash: str | None = None
    captured_at: datetime | None = None
    accessed_at: datetime | None = None
    supersedes_source_id: UUID | None = None
    status: SourceStatus


class Source(BaseModel):
    """Immutable provenance record Р Р†Р вЂљРІР‚Сњ where information came from, not what it proves."""

    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    source_type: SourceType
    provenance_type: SourceProvenanceType = SourceProvenanceType.UNKNOWN
    title: str
    origin: str = ""
    url: str | None = None
    domain: str | None = None
    publisher: str | None = None
    language: str | None = None
    country: str | None = None
    published_at: datetime | None = None
    captured_at: datetime | None = None
    accessed_at: datetime | None = None
    freshness_status: SourceFreshnessStatus = SourceFreshnessStatus.UNKNOWN
    reliability_level: SourceReliabilityLevel = SourceReliabilityLevel.UNVERIFIED
    status: SourceStatus = SourceStatus.REGISTERED
    fingerprint: str = Field(max_length=128)
    content_hash: str | None = None
    etag: str | None = None
    version: int = Field(ge=1, default=1)
    supersedes_source_id: UUID | None = None
    license_type: str | None = None
    capabilities: list[SourceCapability] = Field(default_factory=list)
    reusable_within_project: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class InvestigationSourceLink(BaseModel):
    """Additive use of a Project Source inside one Investigation Р Р†Р вЂљРІР‚Сњ not Evidence."""

    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    investigation_id: UUID
    source_id: UUID
    purpose: str | None = None
    investigation_area: str | None = None
    notes: str | None = None
    status: InvestigationSourceLinkStatus = InvestigationSourceLinkStatus.ACCEPTED
    added_by: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class InvestigationSourceItem(BaseModel):
    """Source plus link metadata for Investigation listing."""

    link: InvestigationSourceLink
    source: Source


class EvidenceType(StrEnum):
    """Atomic claim kinds Р Р†Р вЂљРІР‚Сњ not recommendation/verdict/opinion."""

    OBSERVED_FACT = "observed_fact"
    METRIC = "metric"
    COMPARISON = "comparison"
    USER_STATEMENT = "user_statement"
    CUSTOMER_STATEMENT = "customer_statement"
    MARKET_SIGNAL = "market_signal"
    DEMAND_SIGNAL = "demand_signal"
    CONSTRAINT = "constraint"
    REGULATORY_FACT = "regulatory_fact"
    ECONOMIC_INPUT = "economic_input"
    CALCULATION_RESULT = "calculation_result"
    ABSENCE_SIGNAL = "absence_signal"
    HISTORICAL_FACT = "historical_fact"
    OTHER = "other"


class EvidenceLifecycleStatus(StrEnum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class EvidenceConfidenceLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class EvidenceMateriality(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EvidenceAssessmentState(StrEnum):
    """Evidential quality Р Р†Р вЂљРІР‚Сњ separate from lifecycle; distinct from Business Verdict."""

    CONFIRMED = "confirmed"
    PARTIAL = "partial"
    CONFLICTING = "conflicting"
    MISSING = "missing"
    OUTDATED = "outdated"
    UNVERIFIED = "unverified"


class EvidencePreparedByType(StrEnum):
    USER = "user"
    SYSTEM = "system"
    IMPORT = "import"
    UNKNOWN = "unknown"


class EvidenceSourceStance(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    CONTEXT = "context"


class EvidenceLocatorType(StrEnum):
    PAGE = "page"
    SECTION = "section"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    ROW = "row"
    CELL_RANGE = "cell_range"
    TIMESTAMP = "timestamp"
    URL_FRAGMENT = "url_fragment"
    RECORD_ID = "record_id"
    MANUAL_REFERENCE = "manual_reference"
    UNKNOWN = "unknown"


class EvidenceInvestigationArea(StrEnum):
    PROJECT_CONTEXT = "project_context"
    MARKET_RESEARCH = "market_research"
    COMPETITOR_ANALYSIS = "competitor_analysis"
    AUDIENCE_ANALYSIS = "audience_analysis"
    DEMAND_SIGNALS = "demand_signals"
    ECONOMICS = "economics"
    RISK_ASSESSMENT = "risk_assessment"
    EVIDENCE_REVIEW = "evidence_review"
    OTHER = "other"


class EvidenceSourceLinkInput(BaseModel):
    source_id: UUID
    stance: EvidenceSourceStance
    locator_type: EvidenceLocatorType = EvidenceLocatorType.UNKNOWN
    locator_value: str | None = Field(default=None, max_length=500)
    excerpt: str | None = Field(default=None, max_length=2000)
    note: str | None = Field(default=None, max_length=2000)


class EvidenceCreateRequest(BaseModel):
    """Create draft Evidence Р Р†Р вЂљРІР‚Сњ atomic claim, no Verdict."""

    claim: str = Field(min_length=8, max_length=2000)
    evidence_type: EvidenceType
    investigation_area: EvidenceInvestigationArea = EvidenceInvestigationArea.OTHER
    assessment_state: EvidenceAssessmentState = EvidenceAssessmentState.UNVERIFIED
    confidence_level: EvidenceConfidenceLevel = EvidenceConfidenceLevel.UNKNOWN
    materiality: EvidenceMateriality = EvidenceMateriality.MEDIUM
    review_note: str | None = Field(default=None, max_length=2000)
    why_it_matters: str | None = Field(default=None, max_length=2000)
    recommended_source_type: str | None = Field(default=None, max_length=64)
    source_links: list[EvidenceSourceLinkInput] = Field(default_factory=list)


class EvidenceUpdateRequest(BaseModel):
    """Limited draft edits only."""

    claim: str | None = Field(default=None, min_length=8, max_length=2000)
    evidence_type: EvidenceType | None = None
    investigation_area: EvidenceInvestigationArea | None = None
    assessment_state: EvidenceAssessmentState | None = None
    confidence_level: EvidenceConfidenceLevel | None = None
    materiality: EvidenceMateriality | None = None
    review_note: str | None = Field(default=None, max_length=2000)
    why_it_matters: str | None = Field(default=None, max_length=2000)
    recommended_source_type: str | None = Field(default=None, max_length=64)
    source_links: list[EvidenceSourceLinkInput] | None = None


class EvidenceReviewNoteRequest(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


class EvidenceSupersedeRequest(EvidenceCreateRequest):
    pass


class EvidenceSourceLink(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    investigation_id: UUID
    evidence_id: UUID
    source_id: UUID
    stance: EvidenceSourceStance
    locator_type: EvidenceLocatorType = EvidenceLocatorType.UNKNOWN
    locator_value: str | None = None
    excerpt: str | None = None
    excerpt_hash: str | None = None
    note: str | None = None
    added_by: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Evidence(BaseModel):
    """Atomic reviewable claim linked to exact Source versions Р Р†Р вЂљРІР‚Сњ not Business Verdict."""

    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    investigation_id: UUID
    claim: str
    evidence_type: EvidenceType
    investigation_area: EvidenceInvestigationArea = EvidenceInvestigationArea.OTHER
    lifecycle_status: EvidenceLifecycleStatus = EvidenceLifecycleStatus.DRAFT
    assessment_state: EvidenceAssessmentState = EvidenceAssessmentState.UNVERIFIED
    confidence_level: EvidenceConfidenceLevel = EvidenceConfidenceLevel.UNKNOWN
    materiality: EvidenceMateriality = EvidenceMateriality.MEDIUM
    review_note: str | None = None
    why_it_matters: str | None = None
    recommended_source_type: str | None = None
    prepared_by_type: EvidencePreparedByType = EvidencePreparedByType.USER
    prepared_by_reference: str | None = None
    version: int = Field(ge=1, default=1)
    input_fingerprint: str = Field(max_length=128)
    supersedes_evidence_id: UUID | None = None
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    source_links: list[EvidenceSourceLink] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EvidenceSummary(BaseModel):
    """Read-only Evidence summary Р Р†Р вЂљРІР‚Сњ not Business Verdict."""

    total: int = 0
    by_assessment_state: dict[str, int] = Field(default_factory=dict)
    by_area: dict[str, int] = Field(default_factory=dict)
    by_confidence: dict[str, int] = Field(default_factory=dict)
    by_materiality: dict[str, int] = Field(default_factory=dict)
    accepted_count: int = 0
    unsupported_critical_claims: int = 0
    conflicting_critical_claims: int = 0
    outdated_critical_claims: int = 0
    missing_critical_claims: int = 0
    verdict_readiness_contribution: str = "partial"
    creates_business_verdict: bool = False


# ---------------------------------------------------------------------------
# Commercial MVP P0.5 Р Р†Р вЂљРІР‚Сњ BusinessVerdict Domain
# ---------------------------------------------------------------------------


class BusinessVerdictLifecycleStatus(StrEnum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class BusinessVerdictConfidenceLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class BusinessVerdictPreparedByType(StrEnum):
    USER = "user"
    DETERMINISTIC = "deterministic"
    DETERMINISTIC_LOCAL_IMPORT = "deterministic_local_import"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class BusinessVerdictEvidenceRole(StrEnum):
    SUPPORTS = "supports"
    WEAKENS = "weakens"
    CONTRADICTS = "contradicts"
    CONDITION_BASIS = "condition_basis"
    RISK_BASIS = "risk_basis"
    CONTEXT = "context"


class VerdictConditionStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    SATISFIED = "satisfied"
    FAILED = "failed"
    WAIVED = "waived"


class VerdictRiskSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class VerdictRiskProbability(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class VerdictSensitivity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERDICT_CHANGING = "verdict_changing"


class VerdictAssumptionStatus(StrEnum):
    ACCEPTED_FOR_NOW = "accepted_for_now"
    REQUIRES_VALIDATION = "requires_validation"
    CONFIRMED = "confirmed"
    INVALIDATED = "invalidated"


class VerdictFindingType(StrEnum):
    STRENGTH = "strength"
    WEAKNESS = "weakness"
    OPPORTUNITY = "opportunity"
    CONSTRAINT = "constraint"
    ANOMALY = "anomaly"
    CONTRADICTION = "contradiction"


class VerdictReadinessStatus(StrEnum):
    """Separate from BusinessVerdict type Р Р†Р вЂљРІР‚Сњ from Evidence Summary / Investigation."""

    NOT_READY = "not_ready"
    CONDITIONALLY_READY = "conditionally_ready"
    READY_FOR_REVIEW = "ready_for_review"


class VerdictCondition(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=240)
    required_action: str = Field(min_length=1, max_length=2000)
    owner_role: str = Field(min_length=1, max_length=120)
    success_criterion: str = Field(min_length=1, max_length=2000)
    evidence_required: bool = True
    target_milestone: str | None = Field(default=None, max_length=240)
    consequence_if_unmet: str = Field(min_length=1, max_length=2000)
    status: VerdictConditionStatus = VerdictConditionStatus.OPEN
    waiver_note: str | None = Field(default=None, max_length=2000)


class VerdictCriticalRisk(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(min_length=1, max_length=4000)
    severity: VerdictRiskSeverity
    probability: VerdictRiskProbability
    business_consequence: str = Field(min_length=1, max_length=2000)
    linked_evidence_ids: list[UUID] = Field(default_factory=list)
    mitigation: str | None = Field(default=None, max_length=2000)
    verdict_sensitivity: VerdictSensitivity = VerdictSensitivity.MEDIUM
    status: str = Field(default="open", max_length=64)


class VerdictAssumption(BaseModel):
    statement: str = Field(min_length=1, max_length=2000)
    reason_required: str = Field(min_length=1, max_length=2000)
    linked_evidence_ids: list[UUID] = Field(default_factory=list)
    confidence: BusinessVerdictConfidenceLevel = BusinessVerdictConfidenceLevel.UNKNOWN
    validation_method: str | None = Field(default=None, max_length=1000)
    validation_stage: str | None = Field(default=None, max_length=240)
    impact_if_false: str = Field(min_length=1, max_length=2000)
    status: VerdictAssumptionStatus = VerdictAssumptionStatus.ACCEPTED_FOR_NOW
    converted_from_missing_evidence: bool = False


class VerdictChangeTrigger(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    current_state: str = Field(min_length=1, max_length=500)
    threshold_or_event: str = Field(min_length=1, max_length=1000)
    possible_transition: str = Field(min_length=1, max_length=120)
    linked_evidence_ids: list[UUID] = Field(default_factory=list)
    required_review: bool = True


class VerdictFinding(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    statement: str = Field(min_length=1, max_length=4000)
    finding_type: VerdictFindingType
    linked_evidence_ids: list[UUID] = Field(default_factory=list)
    business_impact: str | None = Field(default=None, max_length=2000)
    status: str = Field(default="active", max_length=64)


class BusinessVerdictEvidenceLinkCreate(BaseModel):
    evidence_id: UUID
    evidence_version: int = Field(ge=1)
    role: BusinessVerdictEvidenceRole
    decision_criterion: str | None = Field(default=None, max_length=240)
    note: str | None = Field(default=None, max_length=2000)


class BusinessVerdictEvidenceLink(BaseModel):
    id: UUID
    verdict_id: UUID
    evidence_id: UUID
    evidence_version: int = Field(ge=1)
    role: BusinessVerdictEvidenceRole
    decision_criterion: str | None = None
    materiality_at_snapshot: EvidenceMateriality
    assessment_state_at_snapshot: EvidenceAssessmentState
    confidence_at_snapshot: EvidenceConfidenceLevel
    note: str | None = None
    owner_id: UUID
    project_id: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BusinessVerdictEvidenceSnapshot(BaseModel):
    """Immutable Evidence basis for a BusinessVerdict Р Р†Р вЂљРІР‚Сњ not a live query."""

    id: UUID
    owner_id: UUID
    project_id: UUID
    investigation_id: UUID
    snapshot_hash: str = Field(min_length=16, max_length=128)
    evidence_ids: list[UUID] = Field(default_factory=list)
    evidence_versions: dict[str, int] = Field(default_factory=dict)
    accepted_evidence_count: int = 0
    missing_critical_count: int = 0
    conflicting_critical_count: int = 0
    outdated_critical_count: int = 0
    area_coverage: dict[str, int] = Field(default_factory=dict)
    readiness_status: VerdictReadinessStatus = VerdictReadinessStatus.NOT_READY
    verdict_readiness_contribution: str = "partial"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BusinessVerdictCreate(BaseModel):
    """Manual draft create Р Р†Р вЂљРІР‚Сњ requires Investigation + Evidence links snapshot."""

    verdict_type: VerdictKind
    confidence_level: BusinessVerdictConfidenceLevel = BusinessVerdictConfidenceLevel.UNKNOWN
    executive_conclusion: str = Field(min_length=1, max_length=2000)
    executive_rationale: str = Field(min_length=1, max_length=8000)
    primary_business_implication: str = Field(min_length=1, max_length=2000)
    recommended_next_action: str = Field(min_length=1, max_length=2000)
    supporting_evidence_summary: str | None = Field(default=None, max_length=4000)
    counter_evidence_summary: str | None = Field(default=None, max_length=4000)
    evidence_links: list[BusinessVerdictEvidenceLinkCreate] = Field(default_factory=list)
    conditions: list[VerdictCondition] = Field(default_factory=list)
    critical_risks: list[VerdictCriticalRisk] = Field(default_factory=list)
    assumptions: list[VerdictAssumption] = Field(default_factory=list)
    change_triggers: list[VerdictChangeTrigger] = Field(default_factory=list)
    findings: list[VerdictFinding] = Field(default_factory=list)
    prepared_by_type: BusinessVerdictPreparedByType = BusinessVerdictPreparedByType.USER
    prepared_by_reference: str | None = Field(default=None, max_length=240)
    supersedes_verdict_id: UUID | None = None


class BusinessVerdictUpdate(BaseModel):
    """Draft-only editable fields."""

    verdict_type: VerdictKind | None = None
    confidence_level: BusinessVerdictConfidenceLevel | None = None
    executive_conclusion: str | None = Field(default=None, min_length=1, max_length=2000)
    executive_rationale: str | None = Field(default=None, min_length=1, max_length=8000)
    primary_business_implication: str | None = Field(default=None, min_length=1, max_length=2000)
    recommended_next_action: str | None = Field(default=None, min_length=1, max_length=2000)
    supporting_evidence_summary: str | None = Field(default=None, max_length=4000)
    counter_evidence_summary: str | None = Field(default=None, max_length=4000)
    conditions: list[VerdictCondition] | None = None
    critical_risks: list[VerdictCriticalRisk] | None = None
    assumptions: list[VerdictAssumption] | None = None
    change_triggers: list[VerdictChangeTrigger] | None = None
    findings: list[VerdictFinding] | None = None


class BusinessVerdictReviewRequest(BaseModel):
    note: str | None = Field(default=None, max_length=2000)
    rejection_reason: str | None = Field(default=None, max_length=2000)


class BusinessVerdictStrategyEligibility(BaseModel):
    """Eligibility only Р Р†Р вЂљРІР‚Сњ does not create Strategy."""

    strategy_eligible: bool = False
    strategy_blocked_reason: str | None = None
    open_conditions_mandatory: bool = False
    pivot_route_allowed: bool = False
    return_to_investigation: bool = False
    creates_strategy: bool = False
    creates_execution_approval: bool = False
    creates_publication_approval: bool = False
    creates_agent_run: bool = False


class BusinessVerdict(BaseModel):
    """Durable commercial viability decision Р Р†Р вЂљРІР‚Сњ not execution/publication approval."""

    id: UUID
    owner_id: UUID
    project_id: UUID
    investigation_id: UUID
    investigation_version: int = Field(ge=1)
    project_brief_id: UUID
    project_brief_version: int = Field(ge=1)
    version: int = Field(ge=1)
    verdict_type: VerdictKind
    lifecycle_status: BusinessVerdictLifecycleStatus
    confidence_level: BusinessVerdictConfidenceLevel
    evidence_snapshot_id: UUID
    evidence_snapshot_hash: str = Field(min_length=16, max_length=128)
    executive_conclusion: str
    executive_rationale: str
    primary_business_implication: str
    recommended_next_action: str
    supporting_evidence_summary: str | None = None
    counter_evidence_summary: str | None = None
    conditions: list[VerdictCondition] = Field(default_factory=list)
    critical_risks: list[VerdictCriticalRisk] = Field(default_factory=list)
    assumptions: list[VerdictAssumption] = Field(default_factory=list)
    change_triggers: list[VerdictChangeTrigger] = Field(default_factory=list)
    findings: list[VerdictFinding] = Field(default_factory=list)
    readiness_snapshot: VerdictReadinessStatus
    prepared_by_type: BusinessVerdictPreparedByType
    prepared_by_reference: str | None = None
    submitted_by: UUID | None = None
    submitted_at: datetime | None = None
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None
    supersedes_verdict_id: UUID | None = None
    strategy_eligibility: BusinessVerdictStrategyEligibility = Field(
        default_factory=BusinessVerdictStrategyEligibility
    )
    evidence_links: list[BusinessVerdictEvidenceLink] = Field(default_factory=list)
    evidence_snapshot: BusinessVerdictEvidenceSnapshot | None = None
    creates_strategy: bool = False
    creates_execution_approval: bool = False
    creates_publication_approval: bool = False
    creates_agent_run: bool = False
    is_execution_approval: bool = False
    is_readiness: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Commercial MVP P0.6 Р Р†Р вЂљРІР‚Сњ MarketingStrategy Domain
# ---------------------------------------------------------------------------


class MarketingStrategyLifecycleStatus(StrEnum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class MarketingStrategyOrigin(StrEnum):
    MANUAL = "manual"
    DETERMINISTIC = "deterministic"
    IMPORTED_LOCAL_PREVIEW = "imported_local_preview"
    FUTURE_LLM_ASSISTED = "future_llm_assisted"
    FUTURE_HUMAN_AUTHORED = "future_human_authored"


class MarketingStrategyReadinessStatus(StrEnum):
    NOT_READY = "not_ready"
    CONDITIONALLY_READY = "conditionally_ready"
    READY_FOR_PLANNING = "ready_for_planning"
    BLOCKED = "blocked"


class StrategyObjectivePriority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class StrategyObjectiveStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    SUPERSEDED = "superseded"


class StrategyMarketType(StrEnum):
    B2B = "b2b"
    B2C = "b2c"
    B2G = "b2g"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class StrategySegmentPriority(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    EXPERIMENTAL = "experimental"
    EXCLUDED = "excluded"


class StrategySegmentValidationStatus(StrEnum):
    CONFIRMED = "confirmed"
    EVIDENCE_SUPPORTED_HYPOTHESIS = "evidence_supported_hypothesis"
    UNVALIDATED_HYPOTHESIS = "unvalidated_hypothesis"
    REJECTED = "rejected"


class StrategyOfferType(StrEnum):
    CORE = "core"
    ENTRY = "entry"
    VALIDATION = "validation"
    PREMIUM = "premium"
    RETENTION = "retention"


class StrategyPriceMode(StrEnum):
    EXACT = "exact"
    RANGE = "range"
    HYPOTHESIS = "hypothesis"
    UNKNOWN = "unknown"


class StrategyChannelStatus(StrEnum):
    RECOMMENDED = "recommended"
    TEST = "test"
    CONDITIONAL = "conditional"
    EXCLUDED = "excluded"
    INSUFFICIENT_DATA = "insufficient_data"


class StrategyAssumptionPlanningStatus(StrEnum):
    ACCEPTED_FOR_PLANNING = "accepted_for_planning"
    REQUIRES_VALIDATION = "requires_validation"
    CONFIRMED = "confirmed"
    INVALIDATED = "invalidated"


class StrategyHandoffStatus(StrEnum):
    NOT_STARTED = "not_started"
    FUTURE = "future"
    UNSUPPORTED = "unsupported"


class StrategyObjective(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=240)
    business_outcome: str = Field(min_length=1, max_length=2000)
    marketing_outcome: str = Field(min_length=1, max_length=2000)
    priority: StrategyObjectivePriority = StrategyObjectivePriority.MEDIUM
    timeframe: str = Field(min_length=1, max_length=240)
    success_metric: str = Field(min_length=1, max_length=1000)
    baseline: str | None = Field(default=None, max_length=500)
    target: str | None = Field(default=None, max_length=500)
    dependency: str | None = Field(default=None, max_length=1000)
    linked_verdict_criterion: str | None = Field(default=None, max_length=240)
    status: StrategyObjectiveStatus = StrategyObjectiveStatus.PROPOSED


class StrategyAudienceSegment(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=240)
    market_type: StrategyMarketType = StrategyMarketType.UNKNOWN
    problem: str = Field(min_length=1, max_length=2000)
    desired_outcome: str = Field(min_length=1, max_length=2000)
    buying_trigger: str | None = Field(default=None, max_length=1000)
    objections: str | None = Field(default=None, max_length=2000)
    decision_maker: str | None = Field(default=None, max_length=500)
    buyer_user_distinction: str | None = Field(default=None, max_length=1000)
    geography: str | None = Field(default=None, max_length=500)
    evidence_strength: BusinessVerdictConfidenceLevel = BusinessVerdictConfidenceLevel.UNKNOWN
    priority: StrategySegmentPriority = StrategySegmentPriority.SECONDARY
    validation_status: StrategySegmentValidationStatus = (
        StrategySegmentValidationStatus.UNVALIDATED_HYPOTHESIS
    )
    linked_evidence_ids: list[UUID] = Field(default_factory=list)


class StrategyPositioning(BaseModel):
    target_customer: str = Field(min_length=1, max_length=1000)
    category: str = Field(min_length=1, max_length=500)
    core_problem: str = Field(min_length=1, max_length=2000)
    alternative_used_today: str | None = Field(default=None, max_length=2000)
    primary_differentiation: str = Field(min_length=1, max_length=2000)
    proof: str | None = Field(default=None, max_length=2000)
    reason_to_believe: str | None = Field(default=None, max_length=2000)
    key_message: str = Field(min_length=1, max_length=2000)
    positioning_risks: list[str] = Field(default_factory=list)
    linked_evidence_ids: list[UUID] = Field(default_factory=list)


class StrategyOffer(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    offer_type: StrategyOfferType
    name: str = Field(min_length=1, max_length=240)
    target_segment_id: str = Field(min_length=1, max_length=64)
    customer_problem: str = Field(min_length=1, max_length=2000)
    promised_outcome: str = Field(min_length=1, max_length=2000)
    scope: str | None = Field(default=None, max_length=2000)
    price_model: StrategyPriceMode = StrategyPriceMode.UNKNOWN
    price_value_or_range: str | None = Field(default=None, max_length=500)
    proof: str | None = Field(default=None, max_length=2000)
    risk_reversal: str | None = Field(default=None, max_length=2000)
    call_to_action: str | None = Field(default=None, max_length=500)
    validation_status: StrategySegmentValidationStatus = (
        StrategySegmentValidationStatus.UNVALIDATED_HYPOTHESIS
    )
    linked_evidence_ids: list[UUID] = Field(default_factory=list)


class StrategyChannelItem(BaseModel):
    channel: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=500)
    funnel_stage: str = Field(min_length=1, max_length=64)
    target_segment_ids: list[str] = Field(default_factory=list)
    expected_signal: str | None = Field(default=None, max_length=1000)
    cost_class: str | None = Field(default=None, max_length=64)
    evidence_basis: str | None = Field(default=None, max_length=1000)
    dependency: str | None = Field(default=None, max_length=1000)
    risk: str | None = Field(default=None, max_length=1000)
    status: StrategyChannelStatus = StrategyChannelStatus.TEST
    exclusion_reason: str | None = Field(default=None, max_length=1000)


class StrategyFunnelStage(BaseModel):
    stage: str = Field(min_length=1, max_length=64)
    customer_action: str = Field(min_length=1, max_length=1000)
    business_action: str = Field(min_length=1, max_length=1000)
    channel: str | None = Field(default=None, max_length=120)
    asset: str | None = Field(default=None, max_length=240)
    metric: str | None = Field(default=None, max_length=500)
    entry_criterion: str | None = Field(default=None, max_length=1000)
    exit_criterion: str | None = Field(default=None, max_length=1000)
    risk: str | None = Field(default=None, max_length=1000)
    linked_objective_ids: list[str] = Field(default_factory=list)


class StrategyAssetItem(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    asset_type: str = Field(min_length=1, max_length=120)
    purpose: str = Field(min_length=1, max_length=1000)
    target_segment_ids: list[str] = Field(default_factory=list)
    funnel_stage: str | None = Field(default=None, max_length=64)
    linked_message: str | None = Field(default=None, max_length=1000)
    dependency: str | None = Field(default=None, max_length=1000)
    priority: StrategyObjectivePriority = StrategyObjectivePriority.MEDIUM
    status: str = Field(default="planned", max_length=64)


class StrategyBudgetLine(BaseModel):
    category: str = Field(min_length=1, max_length=120)
    amount_mode: StrategyPriceMode = StrategyPriceMode.UNKNOWN
    amount_value_or_range: str | None = Field(default=None, max_length=240)
    rationale: str = Field(min_length=1, max_length=2000)
    condition: str | None = Field(default=None, max_length=1000)
    risk: str | None = Field(default=None, max_length=1000)
    expected_learning_outcome: str | None = Field(default=None, max_length=1000)
    requires_approval: bool = False


class StrategyBudgetPolicy(BaseModel):
    research_and_validation: StrategyBudgetLine | None = None
    content_and_assets: StrategyBudgetLine | None = None
    acquisition_testing: StrategyBudgetLine | None = None
    tooling: StrategyBudgetLine | None = None
    specialist_work: StrategyBudgetLine | None = None
    analytics: StrategyBudgetLine | None = None
    contingency: StrategyBudgetLine | None = None
    lines: list[StrategyBudgetLine] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=2000)
    no_guaranteed_roi: bool = True


class StrategyMetric(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=240)
    category: str = Field(min_length=1, max_length=64)
    purpose: str = Field(min_length=1, max_length=1000)
    baseline: str | None = Field(default=None, max_length=500)
    target: str | None = Field(default=None, max_length=500)
    measurement_period: str | None = Field(default=None, max_length=240)
    data_source: str | None = Field(default=None, max_length=500)
    decision_threshold: str = Field(min_length=1, max_length=1000)
    action_if_missed: str = Field(min_length=1, max_length=2000)
    linked_objective_ids: list[str] = Field(default_factory=list)


class StrategyVerdictConditionLink(BaseModel):
    """Reference to Verdict condition authority Р Р†Р вЂљРІР‚Сњ Strategy does not own satisfaction."""

    verdict_condition_id: str = Field(min_length=1, max_length=64)
    current_status_snapshot: str = Field(min_length=1, max_length=64)
    strategy_response: str | None = Field(default=None, max_length=2000)
    validation_action: str | None = Field(default=None, max_length=2000)
    impact_on_strategy: str | None = Field(default=None, max_length=2000)
    blocking_effect: bool = True


class StrategyStrategicRisk(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=240)
    source: str | None = Field(default=None, max_length=500)
    probability: VerdictRiskProbability = VerdictRiskProbability.UNKNOWN
    severity: VerdictRiskSeverity = VerdictRiskSeverity.MEDIUM
    business_impact: str = Field(min_length=1, max_length=2000)
    strategy_impact: str = Field(min_length=1, max_length=2000)
    mitigation: str | None = Field(default=None, max_length=2000)
    early_warning_indicator: str | None = Field(default=None, max_length=1000)
    stop_condition: str | None = Field(default=None, max_length=1000)
    linked_verdict_risk_id: str | None = Field(default=None, max_length=64)
    linked_evidence_ids: list[UUID] = Field(default_factory=list)
    status: str = Field(default="open", max_length=64)


class StrategyPlanningAssumption(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    statement: str = Field(min_length=1, max_length=2000)
    source: str | None = Field(default=None, max_length=500)
    confidence: BusinessVerdictConfidenceLevel = BusinessVerdictConfidenceLevel.UNKNOWN
    validation_method: str | None = Field(default=None, max_length=1000)
    validation_stage: str | None = Field(default=None, max_length=240)
    owner_role: str | None = Field(default=None, max_length=120)
    impact_if_false: str = Field(min_length=1, max_length=2000)
    status: StrategyAssumptionPlanningStatus = (
        StrategyAssumptionPlanningStatus.REQUIRES_VALIDATION
    )
    linked_evidence_ids: list[UUID] = Field(default_factory=list)


class MarketingStrategyCreate(BaseModel):
    business_verdict_id: UUID
    business_verdict_version: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=240)
    executive_summary: str = Field(min_length=1, max_length=4000)
    primary_business_objective: str = Field(min_length=1, max_length=2000)
    strategic_horizon: str = Field(min_length=1, max_length=240)
    objectives: list[StrategyObjective] = Field(default_factory=list)
    audience_segments: list[StrategyAudienceSegment] = Field(default_factory=list)
    positioning: StrategyPositioning
    offers: list[StrategyOffer] = Field(default_factory=list)
    channel_strategy: list[StrategyChannelItem] = Field(default_factory=list)
    funnel: list[StrategyFunnelStage] = Field(default_factory=list)
    asset_plan: list[StrategyAssetItem] = Field(default_factory=list)
    budget_policy: StrategyBudgetPolicy = Field(default_factory=StrategyBudgetPolicy)
    metrics: list[StrategyMetric] = Field(default_factory=list)
    verdict_conditions: list[StrategyVerdictConditionLink] = Field(default_factory=list)
    strategic_risks: list[StrategyStrategicRisk] = Field(default_factory=list)
    assumptions: list[StrategyPlanningAssumption] = Field(default_factory=list)
    execution_constraints: list[str] = Field(default_factory=list)
    strategy_origin: MarketingStrategyOrigin = MarketingStrategyOrigin.MANUAL
    supersedes_strategy_id: UUID | None = None


class MarketingStrategyUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    executive_summary: str | None = Field(default=None, min_length=1, max_length=4000)
    primary_business_objective: str | None = Field(default=None, min_length=1, max_length=2000)
    strategic_horizon: str | None = Field(default=None, min_length=1, max_length=240)
    objectives: list[StrategyObjective] | None = None
    audience_segments: list[StrategyAudienceSegment] | None = None
    positioning: StrategyPositioning | None = None
    offers: list[StrategyOffer] | None = None
    channel_strategy: list[StrategyChannelItem] | None = None
    funnel: list[StrategyFunnelStage] | None = None
    asset_plan: list[StrategyAssetItem] | None = None
    budget_policy: StrategyBudgetPolicy | None = None
    metrics: list[StrategyMetric] | None = None
    verdict_conditions: list[StrategyVerdictConditionLink] | None = None
    strategic_risks: list[StrategyStrategicRisk] | None = None
    assumptions: list[StrategyPlanningAssumption] | None = None
    execution_constraints: list[str] | None = None


class MarketingStrategyReviewRequest(BaseModel):
    note: str | None = Field(default=None, max_length=2000)
    rejection_reason: str | None = Field(default=None, max_length=2000)


class MarketingStrategyBuildDraftRequest(BaseModel):
    business_verdict_id: UUID
    supersedes_strategy_id: UUID | None = None


class MarketingStrategy(BaseModel):
    """Durable commercial go-to-market strategy Р Р†Р вЂљРІР‚Сњ not MarketingPlan or execution approval."""

    id: UUID
    owner_id: UUID
    project_id: UUID
    business_verdict_id: UUID
    business_verdict_version: int = Field(ge=1)
    business_verdict_type: VerdictKind
    evidence_snapshot_id: UUID
    evidence_snapshot_hash: str = Field(min_length=16, max_length=128)
    version: int = Field(ge=1)
    lifecycle_status: MarketingStrategyLifecycleStatus
    strategy_origin: MarketingStrategyOrigin
    title: str
    executive_summary: str
    primary_business_objective: str
    strategic_horizon: str
    objectives: list[StrategyObjective] = Field(default_factory=list)
    audience_segments: list[StrategyAudienceSegment] = Field(default_factory=list)
    positioning: StrategyPositioning
    offers: list[StrategyOffer] = Field(default_factory=list)
    channel_strategy: list[StrategyChannelItem] = Field(default_factory=list)
    funnel: list[StrategyFunnelStage] = Field(default_factory=list)
    asset_plan: list[StrategyAssetItem] = Field(default_factory=list)
    budget_policy: StrategyBudgetPolicy = Field(default_factory=StrategyBudgetPolicy)
    metrics: list[StrategyMetric] = Field(default_factory=list)
    verdict_conditions: list[StrategyVerdictConditionLink] = Field(default_factory=list)
    strategic_risks: list[StrategyStrategicRisk] = Field(default_factory=list)
    assumptions: list[StrategyPlanningAssumption] = Field(default_factory=list)
    execution_constraints: list[str] = Field(default_factory=list)
    readiness_status: MarketingStrategyReadinessStatus
    submitted_by: UUID | None = None
    submitted_at: datetime | None = None
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None
    supersedes_strategy_id: UUID | None = None
    related_marketing_plan_ids: list[UUID] = Field(default_factory=list)
    handoff_status: StrategyHandoffStatus = StrategyHandoffStatus.NOT_STARTED
    creates_marketing_plan: bool = False
    creates_campaign: bool = False
    creates_execution_approval: bool = False
    creates_publication_approval: bool = False
    creates_agent_run: bool = False
    is_marketing_plan: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)



# ---------------------------------------------------------------------------
# Commercial MVP P1.1 Р Р†Р вЂљРІР‚Сњ ImplementationPlan (delivery plan; not MarketingPlan)
# ---------------------------------------------------------------------------


class ImplementationPlanLifecycleStatus(StrEnum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    BLOCKED = "blocked"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class ImplementationPlanOrigin(StrEnum):
    MANUAL = "manual"
    DETERMINISTIC = "deterministic"
    IMPORTED_LOCAL_PREVIEW = "imported_local_preview"
    FUTURE_LLM_ASSISTED = "future_llm_assisted"
    FUTURE_HUMAN_AUTHORED = "future_human_authored"


class ImplementationPlanReadinessStatus(StrEnum):
    NOT_READY = "not_ready"
    CONDITIONALLY_READY = "conditionally_ready"
    READY_FOR_HANDOFF = "ready_for_handoff"
    BLOCKED = "blocked"


class ImplWorkstreamType(StrEnum):
    VALIDATION = "validation"
    RESEARCH = "research"
    POSITIONING = "positioning"
    OFFER_DEVELOPMENT = "offer_development"
    ACQUISITION = "acquisition"
    CONTENT_AND_ASSETS = "content_and_assets"
    SALES_ENABLEMENT = "sales_enablement"
    ANALYTICS = "analytics"
    OPERATIONS = "operations"
    COMPLIANCE = "compliance"
    CUSTOMER_SUCCESS = "customer_success"
    RETENTION = "retention"
    OTHER = "other"


class ImplWorkstreamStatus(StrEnum):
    NOT_STARTED = "not_started"
    READY = "ready"
    BLOCKED = "blocked"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ImplPriority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ImplMilestoneStatus(StrEnum):
    PLANNED = "planned"
    READY = "ready"
    BLOCKED = "blocked"
    IN_PROGRESS = "in_progress"
    ACHIEVED = "achieved"
    MISSED = "missed"
    CANCELLED = "cancelled"


class ImplTaskStatus(StrEnum):
    BACKLOG = "backlog"
    READY = "ready"
    BLOCKED = "blocked"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    APPROVED = "approved"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ImplTaskMappingEligibility(StrEnum):
    EXACT = "exact"
    TRANSFORMABLE = "transformable"
    UNSUPPORTED = "unsupported"
    EXCLUDED = "excluded"
    BLOCKED = "blocked"


class ImplRoleType(StrEnum):
    EXACT_BACKEND_ROLE = "exact_backend_role"
    FRONTEND_ALIAS = "frontend_alias"
    AGGREGATE_ROLE = "aggregate_role"
    CLIENT_OWNER = "client_owner"
    UNSUPPORTED = "unsupported"


class ImplDependencyType(StrEnum):
    FINISH_TO_START = "finish_to_start"
    START_TO_START = "start_to_start"
    APPROVAL_GATE = "approval_gate"
    EVIDENCE_GATE = "evidence_gate"
    BUDGET_GATE = "budget_gate"
    COMPLIANCE_GATE = "compliance_gate"
    RESOURCE_GATE = "resource_gate"
    STRATEGY_CONDITION_GATE = "strategy_condition_gate"


class ImplDependencyNodeType(StrEnum):
    WORKSTREAM = "workstream"
    MILESTONE = "milestone"
    TASK = "task"
    DELIVERABLE = "deliverable"
    BUDGET_GATE = "budget_gate"
    APPROVAL_GATE = "approval_gate"
    CONDITION = "condition"


class ImplDependencyStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    BLOCKED = "blocked"
    WAIVED = "waived"


class ImplDeliverableStatus(StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    READY_FOR_REVIEW = "ready_for_review"
    ACCEPTED = "accepted"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class ImplBudgetValueType(StrEnum):
    EXACT = "exact"
    RANGE = "range"
    UNKNOWN = "unknown"
    REQUIRES_APPROVAL = "requires_approval"


class ImplBudgetCategory(StrEnum):
    RESEARCH_AND_VALIDATION = "research_and_validation"
    CREATIVE_PRODUCTION = "creative_production"
    ACQUISITION_TESTING = "acquisition_testing"
    TOOLING = "tooling"
    SPECIALIST_WORK = "specialist_work"
    ANALYTICS = "analytics"
    CONTINGENCY = "contingency"


class ImplLocalGateStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED_LOCAL = "approved_local"
    REJECTED_LOCAL = "rejected_local"
    EXPIRED = "expired"
    BLOCKED = "blocked"


class ImplApprovalGateType(StrEnum):
    STRATEGY_REVIEW = "strategy_review"
    VALIDATION_COMPLETION = "validation_completion"
    OFFER_REVIEW = "offer_review"
    BUDGET_REVIEW = "budget_review"
    ASSET_REVIEW = "asset_review"
    PILOT_READINESS = "pilot_readiness"
    IMPLEMENTATION_PLAN_REVIEW = "implementation_plan_review"
    FUTURE_EXECUTION_READINESS = "future_execution_readiness"


class ImplConditionSourceType(StrEnum):
    BUSINESS_VERDICT = "business_verdict"
    MARKETING_STRATEGY = "marketing_strategy"
    VALIDATION_REQUIREMENT = "validation_requirement"


class ImplAssumptionStatus(StrEnum):
    ACCEPTED_FOR_PLANNING = "accepted_for_planning"
    REQUIRES_VALIDATION = "requires_validation"
    CONFIRMED = "confirmed"
    INVALIDATED = "invalidated"


class ImplRiskStatus(StrEnum):
    OPEN = "open"
    MITIGATING = "mitigating"
    ACCEPTED = "accepted"
    CLOSED = "closed"


class ImplRoadmapHorizon(StrEnum):
    WEEK_1_2 = "week_1_2"
    MONTH_1 = "month_1"
    MONTH_2 = "month_2"
    QUARTER_1 = "quarter_1"
    CUSTOM_RANGE = "custom_range"
    TBD = "tbd"


class ImplRoadmapPhaseStatus(StrEnum):
    PLANNED = "planned"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ImplTargetPeriodMode(StrEnum):
    EXACT_DATE = "exact_date"
    DATE_RANGE = "date_range"
    RELATIVE_HORIZON = "relative_horizon"
    TBD = "tbd"


class ImplPeriodSpec(BaseModel):
    mode: ImplTargetPeriodMode = ImplTargetPeriodMode.TBD
    label: str = Field(default="TBD", max_length=120)
    start_date: str | None = Field(default=None, max_length=32)
    end_date: str | None = Field(default=None, max_length=32)


class ImplWorkstream(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=240)
    purpose: str = Field(min_length=1, max_length=2000)
    workstream_type: ImplWorkstreamType
    linked_strategy_objective_ids: list[str] = Field(default_factory=list)
    owner_role: str = Field(min_length=1, max_length=120)
    reviewer_role: str = Field(min_length=1, max_length=120)
    priority: ImplPriority = ImplPriority.MEDIUM
    lifecycle_status: ImplWorkstreamStatus = ImplWorkstreamStatus.NOT_STARTED
    planned_start: ImplPeriodSpec = Field(default_factory=ImplPeriodSpec)
    planned_finish: ImplPeriodSpec = Field(default_factory=ImplPeriodSpec)
    dependencies: list[str] = Field(default_factory=list)
    deliverable_ids: list[str] = Field(default_factory=list)
    budget_range: str = Field(default="unknown", max_length=240)
    success_criteria: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    linked_strategy_risk_ids: list[str] = Field(default_factory=list)


class ImplMilestone(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(default="", max_length=2000)
    target_period: ImplPeriodSpec = Field(default_factory=ImplPeriodSpec)
    linked_workstream_ids: list[str] = Field(default_factory=list)
    required_deliverable_ids: list[str] = Field(default_factory=list)
    entry_criteria: list[str] = Field(default_factory=list)
    exit_criteria: list[str] = Field(default_factory=list)
    approval_required: bool = False
    approval_gate_id: str | None = Field(default=None, max_length=64)
    blocking_dependency_ids: list[str] = Field(default_factory=list)
    status: ImplMilestoneStatus = ImplMilestoneStatus.PLANNED


class ImplTask(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(default="", max_length=4000)
    workstream_id: str = Field(min_length=1, max_length=64)
    milestone_id: str | None = Field(default=None, max_length=64)
    responsible_role: str = Field(min_length=1, max_length=120)
    reviewer_role: str | None = Field(default=None, max_length=120)
    priority: ImplPriority = ImplPriority.MEDIUM
    lifecycle_status: ImplTaskStatus = ImplTaskStatus.BACKLOG
    dependency_ids: list[str] = Field(default_factory=list)
    required_inputs: list[str] = Field(default_factory=list)
    expected_output: str = Field(default="", max_length=2000)
    acceptance_criteria: list[str] = Field(default_factory=list)
    budget_impact: str = Field(default="none", max_length=240)
    risk_level: ImplPriority = ImplPriority.MEDIUM
    approval_required: bool = False
    approval_gate_id: str | None = Field(default=None, max_length=64)
    linked_strategy_element_refs: list[str] = Field(default_factory=list)
    mapping_eligibility: ImplTaskMappingEligibility = ImplTaskMappingEligibility.TRANSFORMABLE
    blocked_reason: str | None = Field(default=None, max_length=2000)


class ImplRoleAssignment(BaseModel):
    implementation_role: str = Field(min_length=1, max_length=120)
    backend_role_mapping: str | None = Field(default=None, max_length=120)
    role_type: ImplRoleType = ImplRoleType.FRONTEND_ALIAS
    responsibility: str = Field(min_length=1, max_length=2000)
    decision_authority: str = Field(default="", max_length=2000)
    required_input: str = Field(default="", max_length=2000)
    expected_output: str = Field(default="", max_length=2000)
    reviewer_relationship: str = Field(default="", max_length=2000)
    execution_mapping_allowed: bool = False


class ImplDependency(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    predecessor_type: ImplDependencyNodeType
    predecessor_id: str = Field(min_length=1, max_length=64)
    successor_type: ImplDependencyNodeType
    successor_id: str = Field(min_length=1, max_length=64)
    dependency_type: ImplDependencyType = ImplDependencyType.FINISH_TO_START
    blocking: bool = True
    resolution_action: str = Field(default="", max_length=2000)
    status: ImplDependencyStatus = ImplDependencyStatus.OPEN


class ImplDeliverable(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=240)
    deliverable_type: str = Field(min_length=1, max_length=120)
    workstream_id: str = Field(min_length=1, max_length=64)
    owner_role: str = Field(min_length=1, max_length=120)
    format: str = Field(default="document", max_length=120)
    lifecycle_status: ImplDeliverableStatus = ImplDeliverableStatus.PLANNED
    acceptance_criteria: list[str] = Field(default_factory=list)
    approval_required: bool = False
    approval_gate_id: str | None = Field(default=None, max_length=64)
    linked_strategy_element_refs: list[str] = Field(default_factory=list)
    due_period: ImplPeriodSpec = Field(default_factory=ImplPeriodSpec)
    dependency_ids: list[str] = Field(default_factory=list)


class ImplBudgetItem(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    category: ImplBudgetCategory
    value_type: ImplBudgetValueType = ImplBudgetValueType.UNKNOWN
    minimum: str | None = Field(default=None, max_length=64)
    recommended: str | None = Field(default=None, max_length=64)
    maximum: str | None = Field(default=None, max_length=64)
    currency: str = Field(default="RUB", max_length=8)
    rationale: str = Field(default="", max_length=2000)
    release_condition: str = Field(default="", max_length=2000)
    linked_workstream_ids: list[str] = Field(default_factory=list)
    risk: str = Field(default="", max_length=1000)
    learning_objective: str = Field(default="", max_length=1000)
    requires_approval: bool = True


class ImplBudgetPlan(BaseModel):
    currency: str = Field(default="RUB", max_length=8)
    notes: str = Field(default="Planned structure only Р Р†Р вЂљРІР‚Сњ not budget authorization", max_length=2000)
    items: list[ImplBudgetItem] = Field(default_factory=list)


class ImplBudgetGate(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=240)
    amount_or_range: str = Field(default="unknown", max_length=240)
    prerequisite: str = Field(default="", max_length=2000)
    approval_owner_role: str = Field(min_length=1, max_length=120)
    release_condition: str = Field(default="", max_length=2000)
    blocked_workstream_ids: list[str] = Field(default_factory=list)
    required_evidence_ids: list[str] = Field(default_factory=list)
    lifecycle_status: ImplLocalGateStatus = ImplLocalGateStatus.PENDING


class ImplApprovalGate(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    gate_type: ImplApprovalGateType
    title: str = Field(min_length=1, max_length=240)
    decision_owner_role: str = Field(min_length=1, max_length=120)
    subject_refs: list[str] = Field(default_factory=list)
    required_artifact_ids: list[str] = Field(default_factory=list)
    required_evidence_ids: list[str] = Field(default_factory=list)
    target_milestone_id: str | None = Field(default=None, max_length=64)
    lifecycle_status: ImplLocalGateStatus = ImplLocalGateStatus.PENDING
    consequence_if_rejected: str = Field(default="", max_length=2000)
    affected_task_ids: list[str] = Field(default_factory=list)


class ImplConditionRef(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    source_type: ImplConditionSourceType
    source_id: str = Field(min_length=1, max_length=128)
    source_version: int = Field(ge=1)
    current_status_snapshot: str = Field(default="open", max_length=64)
    required_action: str = Field(default="", max_length=2000)
    owner_role: str = Field(default="Client Owner", max_length=120)
    validation_method: str = Field(default="", max_length=1000)
    success_criterion: str = Field(default="", max_length=1000)
    required_evidence: bool = True
    blocking_task_ids: list[str] = Field(default_factory=list)
    execution_impact: str = Field(
        default="Does not authorize execution; blocks handoff readiness only",
        max_length=2000,
    )


class ImplRisk(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=240)
    source_ref: str = Field(default="", max_length=240)
    probability: ImplPriority = ImplPriority.MEDIUM
    severity: ImplPriority = ImplPriority.MEDIUM
    affected_workstream_ids: list[str] = Field(default_factory=list)
    early_warning_indicator: str = Field(default="", max_length=1000)
    mitigation: str = Field(default="", max_length=2000)
    contingency_action: str = Field(default="", max_length=2000)
    owner_role: str = Field(default="Risk Officer", max_length=120)
    stop_condition: str = Field(default="", max_length=2000)
    lifecycle_status: ImplRiskStatus = ImplRiskStatus.OPEN
    linked_strategy_risk_id: str | None = Field(default=None, max_length=64)


class ImplAssumption(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    statement: str = Field(min_length=1, max_length=2000)
    source_ref: str = Field(default="", max_length=240)
    confidence: ImplPriority = ImplPriority.MEDIUM
    validation_action: str = Field(default="", max_length=2000)
    validation_milestone_id: str | None = Field(default=None, max_length=64)
    owner_role: str = Field(default="Research Director", max_length=120)
    impact_if_false: str = Field(default="", max_length=2000)
    linked_task_ids: list[str] = Field(default_factory=list)
    lifecycle_status: ImplAssumptionStatus = ImplAssumptionStatus.REQUIRES_VALIDATION


class ImplRoadmapPhase(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=240)
    horizon: ImplRoadmapHorizon = ImplRoadmapHorizon.TBD
    workstream_ids: list[str] = Field(default_factory=list)
    milestone_ids: list[str] = Field(default_factory=list)
    entry_criteria: list[str] = Field(default_factory=list)
    exit_criteria: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    status: ImplRoadmapPhaseStatus = ImplRoadmapPhaseStatus.PLANNED


class ImplementationPlanCreate(BaseModel):
    marketing_strategy_id: UUID
    marketing_strategy_version: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=240)
    summary: str = Field(min_length=1, max_length=4000)
    implementation_horizon: str = Field(min_length=1, max_length=240)
    workstreams: list[ImplWorkstream] = Field(default_factory=list)
    milestones: list[ImplMilestone] = Field(default_factory=list)
    tasks: list[ImplTask] = Field(default_factory=list)
    role_assignments: list[ImplRoleAssignment] = Field(default_factory=list)
    dependencies: list[ImplDependency] = Field(default_factory=list)
    deliverables: list[ImplDeliverable] = Field(default_factory=list)
    budget_plan: ImplBudgetPlan = Field(default_factory=ImplBudgetPlan)
    budget_gates: list[ImplBudgetGate] = Field(default_factory=list)
    approval_gates: list[ImplApprovalGate] = Field(default_factory=list)
    conditions: list[ImplConditionRef] = Field(default_factory=list)
    implementation_risks: list[ImplRisk] = Field(default_factory=list)
    assumptions: list[ImplAssumption] = Field(default_factory=list)
    roadmap: list[ImplRoadmapPhase] = Field(default_factory=list)
    plan_origin: ImplementationPlanOrigin = ImplementationPlanOrigin.MANUAL
    supersedes_plan_id: UUID | None = None


class ImplementationPlanUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    summary: str | None = Field(default=None, min_length=1, max_length=4000)
    implementation_horizon: str | None = Field(default=None, min_length=1, max_length=240)
    workstreams: list[ImplWorkstream] | None = None
    milestones: list[ImplMilestone] | None = None
    tasks: list[ImplTask] | None = None
    role_assignments: list[ImplRoleAssignment] | None = None
    dependencies: list[ImplDependency] | None = None
    deliverables: list[ImplDeliverable] | None = None
    budget_plan: ImplBudgetPlan | None = None
    budget_gates: list[ImplBudgetGate] | None = None
    approval_gates: list[ImplApprovalGate] | None = None
    conditions: list[ImplConditionRef] | None = None
    implementation_risks: list[ImplRisk] | None = None
    assumptions: list[ImplAssumption] | None = None
    roadmap: list[ImplRoadmapPhase] | None = None


class ImplementationPlanReviewRequest(BaseModel):
    note: str | None = Field(default=None, max_length=2000)
    rejection_reason: str | None = Field(default=None, max_length=2000)
    block_reason: str | None = Field(default=None, max_length=2000)


class ImplementationPlanBuildDraftRequest(BaseModel):
    marketing_strategy_id: UUID
    supersedes_plan_id: UUID | None = None


class ImplementationPlanHandoffPreview(BaseModel):
    plan_id: UUID
    plan_version: int = Field(ge=1)
    eligible: bool
    mapped_task_count: int = 0
    unsupported_task_count: int = 0
    blocked_task_count: int = 0
    unsupported_roles: list[str] = Field(default_factory=list)
    dependency_loss: list[str] = Field(default_factory=list)
    acceptance_criteria_loss: list[str] = Field(default_factory=list)
    budget_gate_gaps: list[str] = Field(default_factory=list)
    approval_gate_gaps: list[str] = Field(default_factory=list)
    readiness: ImplementationPlanReadinessStatus
    blockers: list[str] = Field(default_factory=list)
    creates_marketing_plan: bool = False
    creates_specialist_tasks: bool = False
    note: str = (
        "Read-only eligibility preview from P1.1. Draft create uses "
        "POST .../marketing-plan-handoff/preview|confirm (P1.2)."
    )


class ImplementationPlan(BaseModel):
    """Durable project delivery plan for an approved MarketingStrategy Р Р†Р вЂљРІР‚Сњ not MarketingPlan."""

    id: UUID
    owner_id: UUID
    project_id: UUID
    marketing_strategy_id: UUID
    marketing_strategy_version: int = Field(ge=1)
    business_verdict_id: UUID
    business_verdict_version: int = Field(ge=1)
    evidence_snapshot_id: UUID
    evidence_snapshot_hash: str = Field(min_length=16, max_length=128)
    version: int = Field(ge=1)
    lifecycle_status: ImplementationPlanLifecycleStatus
    plan_origin: ImplementationPlanOrigin
    title: str
    summary: str
    implementation_horizon: str
    workstreams: list[ImplWorkstream] = Field(default_factory=list)
    milestones: list[ImplMilestone] = Field(default_factory=list)
    tasks: list[ImplTask] = Field(default_factory=list)
    role_assignments: list[ImplRoleAssignment] = Field(default_factory=list)
    dependencies: list[ImplDependency] = Field(default_factory=list)
    deliverables: list[ImplDeliverable] = Field(default_factory=list)
    budget_plan: ImplBudgetPlan = Field(default_factory=ImplBudgetPlan)
    budget_gates: list[ImplBudgetGate] = Field(default_factory=list)
    approval_gates: list[ImplApprovalGate] = Field(default_factory=list)
    conditions: list[ImplConditionRef] = Field(default_factory=list)
    implementation_risks: list[ImplRisk] = Field(default_factory=list)
    assumptions: list[ImplAssumption] = Field(default_factory=list)
    roadmap: list[ImplRoadmapPhase] = Field(default_factory=list)
    readiness_status: ImplementationPlanReadinessStatus
    readiness_reasons: list[str] = Field(default_factory=list)
    submitted_by: UUID | None = None
    submitted_at: datetime | None = None
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None
    block_reason: str | None = None
    supersedes_plan_id: UUID | None = None
    creates_marketing_plan: bool = False
    creates_specialist_tasks: bool = False
    creates_campaign: bool = False
    creates_execution_approval: bool = False
    creates_publication_approval: bool = False
    creates_agent_run: bool = False
    is_marketing_plan: bool = False
    budget_gates_authorize_spend: bool = False
    approval_gates_are_local_only: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Commercial MVP P1.2 Р Р†Р вЂљРІР‚Сњ ImplementationPlan Р Р†РІР‚В РІР‚в„ў MarketingPlan draft handoff
# ---------------------------------------------------------------------------

MAPPING_VERSION_V1 = "implementation_to_marketing_plan.v1"


class ImplementationMarketingPlanHandoffStatus(StrEnum):
    PREVIEW = "preview"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    FAILED = "failed"
    SUPERSEDED = "superseded"
    CANCELLED = "cancelled"


class HandoffTaskClassification(StrEnum):
    EXACT = "exact"
    TRANSFORMABLE = "transformable"
    EXCLUDED = "excluded"
    UNSUPPORTED = "unsupported"
    BLOCKED = "blocked"


class HandoffExistingPlanPolicy(StrEnum):
    CREATE_NEW_DRAFT = "create_new_draft"
    CANCEL = "cancel"


class HandoffTaskMappingItem(BaseModel):
    implementation_task_id: str
    title: str
    classification: HandoffTaskClassification
    reason: str = ""
    mapped_specialist: MarketingSpecialistType | None = None
    mapped_objective: str | None = None
    mapped_expected_output: str | None = None
    acceptance_criteria_mode: str = "none"
    dependency_mode: str = "none"
    responsible_role: str = ""


class ImplementationMarketingPlanHandoffConfirmRequest(BaseModel):
    handoff_preview_id: UUID
    mapping_fingerprint: str = Field(min_length=16, max_length=128)
    expected_implementation_plan_version: int = Field(ge=1)
    explicit_confirmation: bool = False
    existing_plan_policy: HandoffExistingPlanPolicy = (
        HandoffExistingPlanPolicy.CREATE_NEW_DRAFT
    )
    note: str | None = Field(default=None, max_length=2000)


class ImplementationMarketingPlanHandoffPreviewResponse(BaseModel):
    handoff_id: UUID
    implementation_plan_id: UUID
    implementation_plan_version: int = Field(ge=1)
    mapping_version: str = MAPPING_VERSION_V1
    mapping_fingerprint: str
    project_id: UUID
    proposed_title: str
    proposed_goal: str
    included_tasks: list[HandoffTaskMappingItem] = Field(default_factory=list)
    transformed_tasks: list[HandoffTaskMappingItem] = Field(default_factory=list)
    excluded_tasks: list[HandoffTaskMappingItem] = Field(default_factory=list)
    unsupported_tasks: list[HandoffTaskMappingItem] = Field(default_factory=list)
    blocked_tasks: list[HandoffTaskMappingItem] = Field(default_factory=list)
    role_mapping_notes: list[str] = Field(default_factory=list)
    dependency_warnings: list[str] = Field(default_factory=list)
    acceptance_criteria_warnings: list[str] = Field(default_factory=list)
    gate_blockers: list[str] = Field(default_factory=list)
    existing_marketing_plans: list[dict[str, Any]] = Field(default_factory=list)
    duplicate_handoff_id: UUID | None = None
    eligible: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    side_effects: list[str] = Field(default_factory=list)
    creates_marketing_plan_draft: bool = False
    creates_marketing_plan_approval: bool = False
    creates_agent_run: bool = False
    creates_campaign: bool = False
    dispatches_specialist_tasks: bool = False


class ImplementationMarketingPlanHandoffConfirmResponse(BaseModel):
    handoff_id: UUID
    lifecycle_status: ImplementationMarketingPlanHandoffStatus
    marketing_plan_id: UUID
    marketing_plan_version: int = Field(ge=1)
    marketing_plan_status: MarketingPlanStatus = MarketingPlanStatus.DRAFT
    mapping_fingerprint: str
    included_task_count: int = 0
    excluded_task_count: int = 0
    blocked_task_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    idempotent_replay: bool = False
    creates_marketing_plan_approval: bool = False
    creates_agent_run: bool = False
    creates_campaign: bool = False
    dispatches_specialist_tasks: bool = False
    side_effects: list[str] = Field(default_factory=list)


class BusinessOperatorBriefResponse(BaseModel):
    """Response for brief complete / confirm endpoints (Phase AI.210)."""

    brief_draft: CampaignBriefFields
    brief_completeness: CampaignBriefCompleteness
    intent: BusinessIntent
    recommended_scenario: str
    recommended_campaign_name: str


class BusinessOperatorBriefConfirmResponse(BusinessOperatorBriefResponse):
    """Confirmed persisted brief."""

    brief: CampaignBrief


class BusinessOperatorAssistFields(BaseModel):
    """Shared assist-mode fields for analyze / clarify responses (Phase AI.188Р Р†Р вЂљРІР‚СљAI.191)."""

    confidence_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
    confidence_gate_passed: bool = False
    clarification_questions: list[BusinessOperatorClarification] = Field(default_factory=list)
    explanation: ScenarioExplanation | None = None
    preview: BusinessOperatorCampaignPreview | None = None
    intent_audit_id: str
    message_preview: str = ""
    source: BusinessOperatorIntentSource = BusinessOperatorIntentSource.RULE_BASED
    confidence_before: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence_after: float = Field(default=0.0, ge=0.0, le=1.0)
    llm_used: bool = False
    llm_provider: str | None = None
    llm_model: str | None = None
    brief_draft: CampaignBriefFields = Field(default_factory=CampaignBriefFields)
    brief_completeness: CampaignBriefCompleteness | None = None
    tool_suggestions: list[MarketingToolSuggestion] = Field(default_factory=list)


class BusinessOperatorAnalyzeResponse(BusinessOperatorAssistFields):
    """Response for POST .../business-operator/analyze (Phase AI.180)."""

    intent: BusinessIntent
    recommended_scenario: str
    recommended_campaign_name: str
    recommendation: ScenarioRecommendation


class BusinessOperatorClarifyResponse(BusinessOperatorAssistFields):
    """Response for POST .../business-operator/clarify (Phase AI.189)."""

    intent: BusinessIntent
    recommended_scenario: str
    recommended_campaign_name: str
    recommendation: ScenarioRecommendation


class MarketingPlan(BaseModel):
    """Persisted marketing execution plan (Phase AI.28)."""

    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    source_run_id: UUID | None = None
    source_session_id: UUID | None = None
    source_scenario_id: str | None = None
    source_scenario_name: str | None = None
    title: str
    goal: str
    project_context: dict[str, Any] = Field(default_factory=dict)
    specialist_tasks: list[MarketingSpecialistTask] = Field(default_factory=list)
    execution_mode: MarketingExecutionMode = MarketingExecutionMode.PLANNING
    status: MarketingPlanStatus = MarketingPlanStatus.DRAFT
    current_version_number: int = 1
    approved_version_number: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MarketingPlanVersion(BaseModel):
    """Immutable snapshot of a marketing plan at a version (Phase AI.28)."""

    id: UUID = Field(default_factory=uuid4)
    marketing_plan_id: UUID
    version_number: int
    goal: str
    project_context: dict[str, Any] = Field(default_factory=dict)
    specialist_tasks: list[MarketingSpecialistTask] = Field(default_factory=list)
    execution_mode: MarketingExecutionMode = MarketingExecutionMode.PLANNING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by_run_id: UUID | None = None


class MarketingPlanExecutionStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MarketingPlanExecutionTaskStatus(StrEnum):
    PENDING = "pending"
    SKIPPED = "skipped"
    PLACEHOLDER_COMPLETED = "placeholder_completed"
    SPECIALIST_COMPLETED = "specialist_completed"


class MarketingPlanExecutionTaskSnapshot(BaseModel):
    """Frozen specialist task row for an execution run (Phase AI.29)."""

    specialist: MarketingSpecialistType
    objective: str
    expected_output: str
    status: MarketingPlanExecutionTaskStatus = MarketingPlanExecutionTaskStatus.PENDING
    output_ref: str | None = None
    safe_notes: str | None = None


class MarketingPlanExecutionRun(BaseModel):
    """Execution-run skeleton for an approved marketing plan (Phase AI.29)."""

    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    marketing_plan_id: UUID
    marketing_plan_version_number: int
    status: MarketingPlanExecutionStatus = MarketingPlanExecutionStatus.QUEUED
    task_snapshots: list[MarketingPlanExecutionTaskSnapshot] = Field(default_factory=list)
    result_summary: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    finished_at: datetime | None = None


class MarketingSpecialistPriorOutput(BaseModel):
    """Safe prior specialist output context for desk research (Phase AI.32)."""

    specialist: MarketingSpecialistType
    title: str
    output_type: str
    safe_summary: str | None = None
    structured_data: dict[str, Any] | None = None
    content_excerpt: str | None = None


class MarketingSpecialistExecutionInput(BaseModel):
    """Input for a single marketing specialist execution (Phase AI.31)."""

    execution_run_id: UUID
    task_index: int = Field(ge=0)
    marketing_plan_id: UUID
    marketing_plan_version_number: int = Field(ge=1)
    specialist: MarketingSpecialistType
    objective: str
    expected_output: str
    plan_goal: str
    project_context: dict[str, Any] | None = None
    prior_outputs: list[MarketingSpecialistPriorOutput] = Field(default_factory=list)


class MarketingSpecialistExecutionOutput(BaseModel):
    """Normalized specialist execution result before persistence (Phase AI.31)."""

    title: str
    output_type: str
    content: str
    structured_data: dict[str, Any]
    safe_summary: str


class ExecuteMarketingSpecialistTaskResponse(BaseModel):
    """API response after executing one specialist task (Phase AI.31)."""

    execution_run_id: UUID
    task_index: int = Field(ge=0)
    specialist: MarketingSpecialistType
    specialist_output_id: UUID
    status: MarketingSpecialistOutputStatus
    safe_summary: str
    execution_run_status: MarketingPlanExecutionStatus = MarketingPlanExecutionStatus.RUNNING
    run_completed: bool = False


class MarketingSpecialistOutputStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    ARCHIVED = "archived"


class MarketingSpecialistOutput(BaseModel):
    """Persisted specialist output artifact (Phase AI.30)."""

    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    marketing_plan_id: UUID
    execution_run_id: UUID
    task_index: int = Field(ge=0)
    specialist: MarketingSpecialistType
    title: str
    output_type: str = "placeholder"
    content: str
    structured_data: dict[str, Any] | None = None
    status: MarketingSpecialistOutputStatus = MarketingSpecialistOutputStatus.DRAFT
    current_version_number: int = 1
    approved_version_number: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ContentFactoryGenerationStage(StrEnum):
    """Real backend stages for Content Factory copywriter generation (R3.3B-LITE)."""

    PREPARING_CONTENT_PLAN = "preparing_content_plan"
    HANDING_TO_COPYWRITER = "handing_to_copywriter"
    FORMING_MATERIALS = "forming_materials"
    VERIFYING_RESULT = "verifying_result"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


class ContentFactoryGenerationStep(StrEnum):
    """Single advance step for staged UI polling."""

    PREPARE_PLAN = "prepare_plan"
    COPYWRITER = "copywriter"
    FINALIZE = "finalize"
    ALL = "all"


class ContentFactoryBriefInput(BaseModel):
    """Brief fields from Commercial Home Content Factory вЂ” no parallel brief entity."""

    topic: str = Field(min_length=1, max_length=512)
    goal: str = Field(min_length=1, max_length=4096)
    audience: str = Field(min_length=1, max_length=2048)
    channel: str = Field(min_length=1, max_length=64)
    period: str = Field(default="", max_length=256)
    frequency: str = Field(default="", max_length=256)
    format: str = Field(default="", max_length=256)
    tone_brand_constraints: str = Field(default="", max_length=2048)
    source_materials: str = Field(default="", max_length=8000)
    idempotency_key: str | None = Field(default=None, max_length=128)


class ContentFactoryProviderReadiness(BaseModel):
    """Safe provider gate for commercial copywriter generation вЂ” no secrets."""

    ready: bool
    blocked_reason: str | None = None
    blocked_message_ru: str | None = None
    provider: str | None = None
    model: str | None = None
    estimated_input_tokens_min: int | None = None
    estimated_input_tokens_max: int | None = None
    mock_provider: bool = False


class ContentFactoryGeneratedAssetLineage(BaseModel):
    content_asset_id: UUID
    content_slot: int
    title: str
    status: str
    source_marketing_plan_id: UUID
    source_execution_run_id: UUID
    source_content_planner_output_id: UUID
    source_copywriter_output_id: UUID
    llm_provider: str | None = None
    llm_model: str | None = None


class ContentFactoryGenerateMaterialsResponse(BaseModel):
    stage: ContentFactoryGenerationStage
    safe_message: str
    marketing_plan_id: UUID | None = None
    execution_run_id: UUID | None = None
    content_planner_output_id: UUID | None = None
    copywriter_output_id: UUID | None = None
    content_assets: list[ContentFactoryGeneratedAssetLineage] = Field(default_factory=list)
    blocked_reason: str | None = None


class ContentFactoryGenerateMaterialsRequest(BaseModel):
    brief: ContentFactoryBriefInput
    execution_run_id: UUID | None = None
    step: ContentFactoryGenerationStep = ContentFactoryGenerationStep.ALL
    idempotency_key: str | None = Field(default=None, max_length=128)


class CreateContentAssetFromCopywriterResponse(BaseModel):
    """Explicit Copywriter в†’ ContentAsset conversion (Phase AI.40)."""

    specialist_output_id: UUID
    content_asset_id: UUID
    content_asset_status: str = "draft"


class CreateContentAssetsFromCopywriterResponse(BaseModel):
    """Copywriter в†’ multiple ContentAsset drafts (R3.3B-LITE)."""

    specialist_output_id: UUID
    content_asset_ids: list[UUID]
    content_asset_status: str = "draft"




class CreateContentAssetFromCopywriterResponse(BaseModel):
    """Explicit Copywriter Р Р†РІР‚В РІР‚в„ў ContentAsset conversion (Phase AI.40)."""

    specialist_output_id: UUID
    content_asset_id: UUID
    content_asset_status: str = "draft"


class PublicationPackageChannel(StrEnum):
    TELEGRAM = "telegram"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    BLOG = "blog"


class PublicationPackageStatus(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    ARCHIVED = "archived"


class PublicationPackage(BaseModel):
    """Publication package draft Р Р†Р вЂљРІР‚Сњ no outbound send (Phase AI.43)."""

    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    content_asset_id: UUID
    source_content_asset_id: UUID
    channel: PublicationPackageChannel
    title: str
    body: str = ""
    cta: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: PublicationPackageStatus = PublicationPackageStatus.DRAFT
    submitted_for_review_at: datetime | None = None
    approved_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PublishingFoundationChannelType(StrEnum):
    TELEGRAM = "telegram"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    BLOG = "blog"


class PublishingFoundationChannelStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class PublishingFoundationChannel(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    channel_type: PublishingFoundationChannelType
    name: str
    status: PublishingFoundationChannelStatus = PublishingFoundationChannelStatus.DRAFT
    config_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PublishingProviderType(StrEnum):
    DRY_RUN = "dry_run"
    TELEGRAM = "telegram"


class PublicationPackageJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DRY_RUN_SUCCEEDED = "dry_run_succeeded"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PublicationPackageJobScheduleStatus(StrEnum):
    UNSCHEDULED = "unscheduled"
    SCHEDULED = "scheduled"
    DUE = "due"
    DISPATCHED = "dispatched"
    CANCELLED = "cancelled"


class PublishingDispatchMode(StrEnum):
    DRY_RUN = "dry_run"
    REAL = "real"


class PublicationPackageJob(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    publication_package_id: UUID
    channel_id: UUID
    status: PublicationPackageJobStatus = PublicationPackageJobStatus.QUEUED
    payload_snapshot: dict[str, Any] = Field(default_factory=dict)
    snapshot_hash: str | None = None
    result_metadata: dict[str, Any] = Field(default_factory=dict)
    error: dict[str, Any] | None = None
    replay_of_job_id: UUID | None = None
    scheduled_for: datetime | None = None
    schedule_status: PublicationPackageJobScheduleStatus = (
        PublicationPackageJobScheduleStatus.UNSCHEDULED
    )
    dispatch_attempts: int = 0
    last_dispatch_error: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    finished_at: datetime | None = None


class CreatePublicationPackageFromAssetResponse(BaseModel):
    """Explicit approved asset Р Р†РІР‚В РІР‚в„ў PublicationPackage draft (Phase AI.44)."""

    content_asset_id: UUID
    publication_package_id: UUID
    publication_package_status: str = "draft"
    channel: str


class MediaBriefStatus(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    ARCHIVED = "archived"


class MediaAssetType(StrEnum):
    IMAGE = "image"
    VIDEO = "video"
    CAROUSEL = "carousel"


class MediaAssetStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    ARCHIVED = "archived"
    GENERATION_FAILED = "generation_failed"


class MediaBrief(BaseModel):
    """Visual task brief Р Р†Р вЂљРІР‚Сњ no generation (Phase AI.50)."""

    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    content_asset_id: UUID
    source_content_asset_id: UUID
    status: MediaBriefStatus = MediaBriefStatus.DRAFT
    title: str
    goal: str = ""
    target_audience: str = ""
    platform: str = ""
    creative_direction: str = ""
    visual_style: str = ""
    composition: str = ""
    text_overlay: str = ""
    references: list[Any] = Field(default_factory=list)
    submitted_for_review_at: datetime | None = None
    approved_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MediaAsset(BaseModel):
    """Media asset with generation provenance (Phase AI.53Р Р†Р вЂљРІР‚СљAI.58)."""

    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    media_brief_id: UUID
    source_media_brief_id: UUID
    media_type: MediaAssetType
    status: MediaAssetStatus = MediaAssetStatus.DRAFT
    generation_provider: str | None = None
    generation_metadata: dict[str, Any] = Field(default_factory=dict)
    source_generation_job_id: UUID | None = None
    provider: str | None = None
    provider_asset_ref: str | None = None
    storage_uri: str | None = None
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None
    current_version_number: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MediaAssetVersion(BaseModel):
    """Immutable generated media snapshot (Phase AI.58)."""

    version_number: int
    media_asset_id: UUID
    source_generation_job_id: UUID | None = None
    storage_uri: str | None = None
    provider_asset_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CreateMediaBriefFromAssetResponse(BaseModel):
    """Explicit approved asset Р Р†РІР‚В РІР‚в„ў MediaBrief draft (Phase AI.51)."""

    content_asset_id: UUID
    media_brief_id: UUID
    media_brief_status: str = "draft"


class CreateMediaAssetFromBriefResponse(BaseModel):
    """Explicit approved brief Р Р†РІР‚В РІР‚в„ў MediaAsset placeholder (Phase AI.54)."""

    media_brief_id: UUID
    media_asset_id: UUID
    media_asset_status: str = "draft"
    media_type: str


class MediaGenerationProvider(StrEnum):
    MOCK = "mock"
    OPENAI_IMAGES = "openai_images"
    FLUX = "flux"


class MediaGenerationJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MediaGenerationJob(BaseModel):
    """Controlled media generation job (Phase AI.56)."""

    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    media_brief_id: UUID
    media_asset_id: UUID | None = None
    provider: MediaGenerationProvider
    media_type: str
    prompt: str
    status: MediaGenerationJobStatus = MediaGenerationJobStatus.QUEUED
    result_metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    finished_at: datetime | None = None


class CreateMediaGenerationJobRequest(BaseModel):
    provider: str = "mock"
    media_type: str = "image"


class MarketingSpecialistOutputVersion(BaseModel):
    """Immutable specialist output snapshot at a version (Phase AI.30)."""

    id: UUID = Field(default_factory=uuid4)
    specialist_output_id: UUID
    version_number: int
    title: str
    output_type: str
    content: str
    structured_data: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by_run_id: UUID | None = None


class ChatAssistantMessageBlockType(StrEnum):
    TEXT = "text"
    CLARIFICATION = "clarification"
    DRAFT = "draft"
    BRIEF = "brief"
    MARKETING_PLAN = "marketing_plan"
    ERROR = "error"


class ChatAssistantMessageDomain(StrEnum):
    GENERAL = "general"
    MARKETING = "marketing"
    PROGRAMMER = "programmer"
    MEDIA = "media"
    UNKNOWN = "unknown"


class ChatBlockActionType(StrEnum):
    CREATE_MARKETING_ASSET = "create_marketing_asset"
    CREATE_MARKETING_BRIEF = "create_marketing_brief"
    CREATE_REVISION_FROM_APPROVED = "create_revision_from_approved"
    SAVE_MARKETING_PLAN = "save_marketing_plan"
    COPY_TEXT = "copy_text"
    EXPORT_MARKDOWN = "export_markdown"


class ChatBlockAction(BaseModel):
    """Safe action offered for a chat block (Phase AI.22)."""

    type: ChatBlockActionType
    label: str
    enabled: bool = True
    reason: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ChatAssistantMessageBlock(BaseModel):
    """Frontend-safe assistant payload (Phase AI.21Р Р†Р вЂљРІР‚СљAI.22)."""

    type: ChatAssistantMessageBlockType
    domain: ChatAssistantMessageDomain
    content: str
    title: str | None = None
    data: dict[str, Any] | None = None
    persisted: bool | None = None
    created_at: datetime | None = None
    actions: list[ChatBlockAction] = Field(default_factory=list)


class ChatMessage(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    role: AgentChatMessageRole
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    agent_run_id: UUID | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    blocks: list[ChatAssistantMessageBlock] = Field(default_factory=list)


class AgentChatSession(ChatSession):
    """Backward-compatible alias for chat session contracts."""


class AgentChatSessionListItem(ChatSessionListItem):
    """Backward-compatible alias for session list items."""


class AgentChatMessage(ChatMessage):
    """Backward-compatible alias for chat message contracts."""


class AgentChatWorkflowContext(BaseModel):
    """Compact campaign workflow snapshot for agent chat runs (Phase AI.2)."""

    campaign_id: UUID
    workflow_state: CampaignWorkflowState
    next_recommended_action: CampaignWorkflowRecommendedAction
    pending_review_assets: int = 0


class ReviewQueueItemType(StrEnum):
    CONTENT_ASSET = "content_asset"


# ---------------------------------------------------------------------------
# Architecture v2.0 Р Р†Р вЂљРІР‚Сњ Phase V2.1 additive compatibility contracts
# ---------------------------------------------------------------------------
# These types map Marketsynth Architecture targets onto future adapters.
# They MUST NOT be required by existing API serializers in V2.1.
# No DB tables / migrations / runtime wiring in this phase.
# ---------------------------------------------------------------------------


class ArchitectureV2Phase(StrEnum):
    """Migration program phase identifiers (documentation + gating)."""

    V2_1_CONTRACTS = "v2.1_contracts"
    V2_2_VERIFIED_EXECUTION = "v2.2_verified_execution"
    V2_3_PROVIDER_ABSTRACTION = "v2.3_provider_abstraction"
    V2_4_BUSINESS_TOOL_LAYER = "v2.4_business_tool_layer"
    V2_5_DYNAMIC_TOOL_PROFILES = "v2.5_dynamic_tool_profiles"
    V2_6_REASONING_ARTIFACTS = "v2.6_reasoning_artifacts"
    V2_7_ABSTENTION = "v2.7_abstention"
    V2_8_QUALITY_FRAMEWORK = "v2.8_quality_framework"
    V2_9_SNAPSHOT_REUSE = "v2.9_snapshot_reuse"
    V2_10_MCP_BOUNDARY = "v2.10_mcp_boundary"
    V2_11_FRONTEND_SEMANTIC_STATES = "v2.11_frontend_semantic_states"
    V2_12_FREEZE = "v2.12_freeze"


class VerificationStatus(StrEnum):
    """Provider verification after external write (Architecture v2 Verified Execution)."""

    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    VERIFIED = "verified"
    VERIFICATION_LIMITED = "verification_limited"
    FAILED = "failed"
    SKIPPED = "skipped"


class ProviderKind(StrEnum):
    """High-level external provider categories (abstraction stub)."""

    PUBLISHING = "publishing"
    ADS = "ads"
    ANALYTICS = "analytics"
    WORKFLOW = "workflow"
    LLM = "llm"
    MEDIA = "media"
    MOCK = "mock"


class ToolLayerKind(StrEnum):
    """Internal Capability vs Business Tool split (metadata layer)."""

    INTERNAL_CAPABILITY = "internal_capability"
    BUSINESS_TOOL = "business_tool"


class ReasoningArtifactKind(StrEnum):
    """Structured reasoning artifacts Р Р†Р вЂљРІР‚Сњ never chain-of-thought text."""

    HYPOTHESIS = "hypothesis"
    EVIDENCE = "evidence"
    COUNTER_EVIDENCE = "counter_evidence"
    ASSUMPTION = "assumption"
    MISSING_DATA = "missing_data"
    RISK_FACTOR = "risk_factor"
    DECISION_CANDIDATE = "decision_candidate"
    CONFIDENCE_ASSESSMENT = "confidence_assessment"


class VerdictKind(StrEnum):
    """Business verdict vocabulary including formal abstention."""

    GO = "go"
    CONDITIONAL_GO = "conditional_go"
    NO_GO = "no_go"
    INSUFFICIENT_DATA = "insufficient_data"


class EvidenceState(StrEnum):
    CONFIRMED = "confirmed"
    PARTIAL = "partial"
    CONFLICTING = "conflicting"
    MISSING = "missing"
    OUTDATED = "outdated"
    UNVERIFIED = "unverified"


class ApprovalState(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ExecutionLifecycleState(StrEnum):
    """Semantic execution states (UI + future Verified Execution)."""

    READY = "ready"
    BLOCKED = "blocked"
    RUNNING = "running"
    VERIFYING = "verifying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class AiQualityGate(StrEnum):
    """AI Quality Framework ladder Q0Р Р†Р вЂљРІР‚СљQ6 (scaffold only)."""

    Q0_INPUT = "q0_input"
    Q1_RETRIEVAL = "q1_retrieval"
    Q2_CONTEXT = "q2_context"
    Q3_STRUCTURED_OUTPUT = "q3_structured_output"
    Q4_TOOL_AGENT_WORKFLOW = "q4_tool_agent_workflow"
    Q5_INCOMPLETE_OR_CONFLICTING = "q5_incomplete_or_conflicting"
    Q6_BUSINESS_VERDICT = "q6_business_verdict"


class MarketsynthCompatibilityMapping(BaseModel):
    """Maps a Marketsynth Architecture concept to a BotFazer legacy artifact.

    V2.1 documentation aid Р Р†Р вЂљРІР‚Сњ not persisted, not served by APIs.
    """

    marketsynth_concept: str
    legacy_artifact: str | None = None
    compatibility: str = Field(
        description="compatible | partially_compatible | absent | conflicting",
    )
    notes: str = ""


# Frozen inventory for characterization tests (do not mutate values casually).
ARCHITECTURE_V2_1_COMPATIBILITY_MAPPINGS: tuple[MarketsynthCompatibilityMapping, ...] = (
    MarketsynthCompatibilityMapping(
        marketsynth_concept="AgentRun",
        legacy_artifact="app.schemas.contracts.AgentRun / AgentRunService",
        compatibility="compatible",
        notes="Preserve execute-specialist and AgentRunStatus.",
    ),
    MarketsynthCompatibilityMapping(
        marketsynth_concept="ToolRegistry",
        legacy_artifact="app.tools.registry.ToolRegistry + allowlists",
        compatibility="compatible",
        notes="Extend with metadata; do not delete.",
    ),
    MarketsynthCompatibilityMapping(
        marketsynth_concept="HumanApproval",
        legacy_artifact="asset/plan/package approve gates",
        compatibility="partially_compatible",
        notes="No ApprovalRequest entity yet.",
    ),
    MarketsynthCompatibilityMapping(
        marketsynth_concept="VerifiedExecution",
        legacy_artifact="Telegram publish write-ack",
        compatibility="partially_compatible",
        notes="Transport success Р Р†РІР‚В°Р’В  provider verification.",
    ),
    MarketsynthCompatibilityMapping(
        marketsynth_concept="EvidenceRecord",
        legacy_artifact=None,
        compatibility="absent",
        notes="Introduce in later phase with append-only persistence.",
    ),
    MarketsynthCompatibilityMapping(
        marketsynth_concept="KnowledgeCandidate",
        legacy_artifact=None,
        compatibility="absent",
        notes="Align with Marketsynth CORE_CONTRACT_DEFINITIONS when persisted.",
    ),
    MarketsynthCompatibilityMapping(
        marketsynth_concept="ProviderInterface",
        legacy_artifact="publishing/media provider registries",
        compatibility="partially_compatible",
        notes="Generalize in V2.3 with mock provider.",
    ),
    MarketsynthCompatibilityMapping(
        marketsynth_concept="Abstention.INSUFFICIENT_DATA",
        legacy_artifact=None,
        compatibility="absent",
        notes="VerdictKind.INSUFFICIENT_DATA reserved in V2.1.",
    ),
    MarketsynthCompatibilityMapping(
        marketsynth_concept="tenant_id",
        legacy_artifact="owner_id + project_id scoping",
        compatibility="partially_compatible",
        notes="Do not rename owner_id; dual-field later if required.",
    ),
    MarketsynthCompatibilityMapping(
        marketsynth_concept="MCP Boundary",
        legacy_artifact="FastAPI application services",
        compatibility="absent",
        notes="No MCP server in V2.1; keep logic in application layer.",
    ),
)

ARCHITECTURE_V2_1_ACTIVE_PHASE: ArchitectureV2Phase = ArchitectureV2Phase.V2_1_CONTRACTS


class ResearchProviderState(StrEnum):
    READY = "ready"
    PARTIALLY_READY = "partially_ready"
    UNAVAILABLE = "unavailable"
    INVALID_CREDENTIALS = "invalid_credentials"
    BLOCKED_BY_POLICY = "blocked_by_policy"


class ResearchProviderReadiness(BaseModel):
    """Safe per-provider readiness РІР‚вЂќ never includes secrets or raw dumps."""

    provider: str
    state: ResearchProviderState = ResearchProviderState.UNAVAILABLE
    configured: bool = False
    reachable: bool = False
    authentication_valid: bool | None = None
    read_only_capability: bool = True
    supported_operations: list[str] = Field(default_factory=list)
    rate_limit_state: str = "unknown"
    safe_error_code: str | None = None
    last_checked_at: datetime | None = None
    latency_ms: int | None = None
    probe_result_count: int | None = None


# ---------------------------------------------------------------------------
# Phase 1B.1 РІР‚вЂќ Commercial Research orchestration (no Source/Evidence yet)
# UserRequest РІвЂ вЂ™ Project РІвЂ вЂ™ Brief РІвЂ вЂ™ Investigation РІвЂ вЂ™ CommercialResearchRun
# ---------------------------------------------------------------------------


class CommercialResearchRunStatus(StrEnum):
    DRAFT = "draft"
    PREFLIGHT_READY = "preflight_ready"
    QUOTE_READY = "quote_ready"
    AWAITING_APPROVAL = "awaiting_approval"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    OUTCOME_UNKNOWN = "outcome_unknown"


class CommercialResearchStageId(StrEnum):
    BOOTSTRAP = "bootstrap"
    PREFLIGHT = "preflight"
    QUOTE = "quote"
    APPROVAL = "approval"
    SOURCE_COLLECTION = "source_collection"
    SOURCE_VALIDATION = "source_validation"
    EVIDENCE_EXTRACTION = "evidence_extraction"
    FINDINGS = "findings"
    VERDICT = "verdict"
    COMPLETED = "completed"


class CommercialResearchApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"


class CommercialResearchQuote(BaseModel):
    quote_id: UUID
    request_hash: str = Field(max_length=128)
    tenant_id: UUID
    estimated_search_queries: int = Field(ge=0)
    estimated_fetched_pages: int = Field(ge=0)
    estimated_llm_calls: int = Field(ge=0)
    estimated_llm_tokens: int = Field(ge=0)
    estimated_cost_min: str = Field(max_length=64)
    estimated_cost_max: str = Field(max_length=64)
    currency: str = Field(default="RUB", max_length=8)
    assumptions: list[str] = Field(default_factory=list)
    provider_capabilities: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    expires_at: datetime


class CommercialResearchApproval(BaseModel):
    approval_id: UUID
    status: CommercialResearchApprovalStatus = CommercialResearchApprovalStatus.APPROVED
    tenant_id: UUID
    owner_id: UUID
    user_request_id: UUID
    project_id: UUID
    project_brief_id: UUID
    project_brief_version: int = Field(ge=1)
    investigation_id: UUID
    research_run_id: UUID
    request_hash: str = Field(max_length=128)
    quote_id: UUID
    owner_confirmed: bool = True
    approved_at: datetime
    expires_at: datetime


class CommercialResearchEstimatedScope(BaseModel):
    estimated_search_queries: int = Field(ge=0)
    estimated_fetched_pages: int = Field(ge=0)
    estimated_llm_calls: int = Field(ge=0)
    scope_note_ru: str = Field(default="", max_length=2000)


class CommercialResearchPreflightCommercial(BaseModel):
    ready: bool
    paid_execution_required: bool = True
    blocking_reasons: list[str] = Field(default_factory=list)
    estimated_scope: CommercialResearchEstimatedScope
    research_not_executed: bool = True


class CommercialResearchPreflightResponse(BaseModel):
    run_id: UUID
    status: CommercialResearchRunStatus
    commercial: CommercialResearchPreflightCommercial
    developer: dict[str, Any] | None = None


class CommercialResearchQuoteCommercial(BaseModel):
    cost_range_label: str
    currency: str = "RUB"
    expires_at: datetime
    assumptions: list[str] = Field(default_factory=list)
    research_not_executed: bool = True


class CommercialResearchQuoteResponse(BaseModel):
    run_id: UUID
    quote_id: UUID
    status: CommercialResearchRunStatus
    commercial: CommercialResearchQuoteCommercial
    developer: dict[str, Any] | None = None


class CommercialResearchApproveRequest(BaseModel):
    quote_id: UUID
    owner_confirmed: bool = True


class CommercialResearchApproveResponse(BaseModel):
    run_id: UUID
    approval_id: UUID
    status: CommercialResearchRunStatus
    approval_status: CommercialResearchApprovalStatus
    expires_at: datetime


class CommercialResearchExecuteRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=128)
    owner_confirmed: bool = True


class CommercialResearchExecuteResponse(BaseModel):
    run_id: UUID
    status: CommercialResearchRunStatus
    error_code: str | None = None
    safe_message: str


class CommercialResearchStatusCommercial(BaseModel):
    status_label: str
    stage_label: str
    completed_stage_labels: list[str] = Field(default_factory=list)
    blocking_reason: str | None = None
    quote_summary: str | None = None
    approval_status_label: str | None = None
    retryable: bool = False
    outcome_unknown: bool = False
    research_not_executed: bool = True


class CommercialResearchStatusResponse(BaseModel):
    run_id: UUID
    user_request_id: UUID
    project_id: UUID | None = None
    investigation_id: UUID | None = None
    status: CommercialResearchRunStatus
    current_stage: CommercialResearchStageId
    commercial: CommercialResearchStatusCommercial
    developer: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class CommercialResearchRun(BaseModel):
    id: UUID
    tenant_id: UUID
    owner_id: UUID
    user_request_id: UUID
    project_id: UUID
    project_brief_id: UUID
    project_brief_version: int = Field(ge=1)
    investigation_id: UUID
    status: CommercialResearchRunStatus
    current_stage: CommercialResearchStageId
    completed_stages: list[CommercialResearchStageId] = Field(default_factory=list)
    progress_pct: int = Field(ge=0, le=100, default=0)
    request_hash: str = Field(max_length=128)
    run_version: int = Field(ge=1, default=1)
    idempotency_key: str | None = None
    quote_id: UUID | None = None
    approval_id: UUID | None = None
    provider_operation_id: str | None = None
    error_code: str | None = None
    safe_error_message: str | None = None
    outcome_unknown: bool = False
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    updated_at: datetime


class CommercialResearchBootstrapResponse(BaseModel):
    run: CommercialResearchRun
    lineage_reused: bool = False


# --- PRODUCT-01.3A BIV Analysis Context (intake gate) ---


class AnalysisContextState(StrEnum):
    EMPTY = "empty"
    DRAFT_ENTERED = "draft_entered"
    HYDRATED_UNCONFIRMED = "hydrated_unconfirmed"
    CONFIRMED = "confirmed"
    EDITING = "editing"
    ANALYSIS_REQUESTED = "analysis_requested"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class AnalysisContextSourceMode(StrEnum):
    NEW_USER_INPUT = "new_user_input"
    RESTORED_PROJECT_CONTEXT = "restored_project_context"
    EDITED_RESTORED_CONTEXT = "edited_restored_context"


class AnalysisContextDataSourceLabel(StrEnum):
    SAVED_PROJECT = "saved_project"
    PREVIOUS_SESSION = "previous_session"
    RESTORED_DRAFT = "restored_draft"


class AnalysisContextFields(BaseModel):
    idea_description: str = Field(default="", max_length=8000)
    product_or_service: str | None = Field(default=None, max_length=2000)
    target_customer: str | None = Field(default=None, max_length=2000)
    geography: str | None = Field(default=None, max_length=500)
    business_model: str | None = Field(default=None, max_length=1000)
    pricing_or_revenue_model: str | None = Field(default=None, max_length=1000)
    current_stage: str | None = Field(default=None, max_length=500)
    budget_context: str | None = Field(default=None, max_length=500)
    known_competitors: str | None = Field(default=None, max_length=2000)
    analysis_goal: str | None = Field(default=None, max_length=1000)
    target_customer_unknown: bool = False
    geography_unknown: bool = False


class AnalysisContextCreateDraftRequest(AnalysisContextFields):
    pass


class AnalysisContextEditRequest(AnalysisContextFields):
    pass


class AnalysisContextConfirmRequest(BaseModel):
    input_snapshot_hash: str | None = Field(default=None, min_length=64, max_length=64)


class AnalysisContextRecord(BaseModel):
    context_id: UUID
    owner_id: UUID
    project_id: UUID
    state: AnalysisContextState
    source_mode: AnalysisContextSourceMode | None = None
    data_source_label: AnalysisContextDataSourceLabel | None = None
    idea_description: str = ""
    product_or_service: str | None = None
    target_customer: str | None = None
    geography: str | None = None
    business_model: str | None = None
    pricing_or_revenue_model: str | None = None
    current_stage: str | None = None
    budget_context: str | None = None
    known_competitors: str | None = None
    analysis_goal: str | None = None
    target_customer_unknown: bool = False
    geography_unknown: bool = False
    confirmed_by_user: bool = False
    confirmed_at: datetime | None = None
    input_snapshot_hash: str | None = None
    source_snapshot_id: UUID | None = None
    is_active: bool = True
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class AnalysisContextCurrentResponse(BaseModel):
    project_id: UUID
    context: AnalysisContextRecord | None = None
    has_completed_analysis: bool = False
    completed_run_id: UUID | None = None


class AnalysisContextStartNewResponse(BaseModel):
    project_id: UUID
    context: AnalysisContextRecord


# --- CMVP.1 Business Idea Validation ---


class BusinessIdeaValidationVerdictKind(StrEnum):
    PROCEED = "proceed"
    PROCEED_WITH_CONDITIONS = "proceed_with_conditions"
    REVISE = "revise"
    REJECT = "reject"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class BusinessIdeaValidationRunStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class BivResearchMode(StrEnum):
    INITIAL = "initial"
    RERUN = "rerun"
    REFINED_RERUN = "refined_rerun"


class BivCommercialVerdictKind(StrEnum):
    GO = "GO"
    CONDITIONAL_GO = "CONDITIONAL_GO"
    PILOT_ONLY = "PILOT_ONLY"
    HOLD = "HOLD"
    NO_GO = "NO_GO"


class BivPipelineStage(StrEnum):
    NORMALIZING_INPUT = "normalizing_input"
    DECOMPOSING_QUERIES = "decomposing_queries"
    SEARCHING_DIRECT = "searching_direct"
    SEARCHING_INDIRECT = "searching_indirect"
    SEARCHING_INTERNATIONAL = "searching_international"
    SEARCHING_LOCAL = "searching_local"
    SEARCHING_ADJACENT = "searching_adjacent"
    VALIDATING_SOURCES = "validating_sources"
    EXTRACTING_EVIDENCE = "extracting_evidence"
    SYNTHESIZING_FINDINGS = "synthesizing_findings"
    CALCULATING_CONFIDENCE = "calculating_confidence"
    CALCULATING_COVERAGE = "calculating_coverage"
    GENERATING_VERDICT = "generating_verdict"
    BUILDING_REPORT = "building_report"
    COMPLETED = "completed"


class BivRunProgressFailure(BaseModel):
    error_code: str = Field(min_length=1, max_length=128)
    safe_message: str = Field(min_length=1, max_length=1000)


class BivRunProgress(BaseModel):
    run_id: UUID
    state: BusinessIdeaValidationRunStatus
    current_stage: BivPipelineStage
    completed_stages: list[BivPipelineStage] = Field(default_factory=list)
    started_at: datetime
    updated_at: datetime
    progress_percent: int = Field(ge=0, le=100)
    failure: BivRunProgressFailure | None = None
    correlation_id: str = Field(min_length=1, max_length=128)


class BivRunStateTransition(BaseModel):
    state: str = Field(min_length=1, max_length=64)
    stage: str | None = Field(default=None, max_length=64)
    at: datetime


class BivFetchOutcomeCode(StrEnum):
    SUCCESS = "success"
    TIMEOUT = "timeout"
    DNS_ERROR = "dns_error"
    CONNECTION_ERROR = "connection_error"
    TLS_ERROR = "tls_error"
    HTTP_401 = "http_401"
    HTTP_403 = "http_403"
    HTTP_404 = "http_404"
    HTTP_409 = "http_409"
    HTTP_429 = "http_429"
    HTTP_5XX = "http_5xx"
    ROBOTS_BLOCKED = "robots_blocked"
    JAVASCRIPT_REQUIRED = "javascript_required"
    UNSUPPORTED_CONTENT_TYPE = "unsupported_content_type"
    EMPTY_CONTENT = "empty_content"
    CONTENT_TOO_SHORT = "content_too_short"
    MALFORMED_CONTENT = "malformed_content"
    PROVIDER_REJECTED = "provider_rejected"
    RATE_LIMITED = "rate_limited"
    CREDITS_EXHAUSTED = "credits_exhausted"
    UNSAFE_URL = "unsafe_url"
    DUPLICATE_URL = "duplicate_url"
    CANCELLED = "cancelled"
    UNKNOWN_ERROR = "unknown_error"


class BivFetchLedgerEntry(BaseModel):
    fetch_id: UUID
    run_id: UUID
    correlation_id: str = Field(min_length=1, max_length=128)
    query_id: str = Field(default="", max_length=128)
    source_url: str = Field(min_length=1, max_length=2048)
    normalized_url: str = Field(min_length=1, max_length=2048)
    provider: str = Field(min_length=1, max_length=64)
    attempt_number: int = Field(ge=1, le=20)
    started_at: datetime
    finished_at: datetime
    latency_ms: int = Field(ge=0)
    http_status: int | None = None
    outcome_code: BivFetchOutcomeCode
    content_type: str | None = Field(default=None, max_length=128)
    content_length: int | None = Field(default=None, ge=0)
    retryable: bool = False
    fallback_used: bool = False
    error_class: str | None = Field(default=None, max_length=64)
    safe_error_message: str | None = Field(default=None, max_length=500)
    raw_content_stored: bool = False
    extracted_text_length: int = Field(default=0, ge=0)
    created_at: datetime


class BivDiscoveryMetrics(BaseModel):
    queries_generated: int = Field(default=0, ge=0)
    queries_executed: int = Field(default=0, ge=0)
    search_requests: int = Field(default=0, ge=0)
    search_success_count: int = Field(default=0, ge=0)
    discovered_urls: int = Field(default=0, ge=0)
    unique_urls: int = Field(default=0, ge=0)
    duplicate_urls: int = Field(default=0, ge=0)
    ineligible_urls: int = Field(default=0, ge=0)
    search_coverage: float = Field(default=0.0, ge=0.0, le=1.0)


class BivFetchStageMetrics(BaseModel):
    fetch_attempts: int = Field(default=0, ge=0)
    fetch_success_count: int = Field(default=0, ge=0)
    fetch_failure_count: int = Field(default=0, ge=0)
    eligible_urls: int = Field(default=0, ge=0)
    attempted_eligible_urls: int = Field(default=0, ge=0)
    fetch_success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    failures_by_outcome: dict[str, int] = Field(default_factory=dict)
    fallback_success_count: int = Field(default=0, ge=0)
    provider_circuit_state: dict[str, str] = Field(default_factory=dict)
    fetch_attempts_by_provider: dict[str, int] = Field(default_factory=dict)
    fetch_success_by_provider: dict[str, int] = Field(default_factory=dict)
    fetch_fallback_total: dict[str, int] = Field(default_factory=dict)
    duplicate_url_skipped_total: int = Field(default=0, ge=0)
    cache_hit_total: int = Field(default=0, ge=0)
    provider_credits_exhausted_total: dict[str, int] = Field(default_factory=dict)
    all_providers_failed_total: int = Field(default=0, ge=0)


class BivExtractMetrics(BaseModel):
    extraction_attempts: int = Field(default=0, ge=0)
    extraction_success_count: int = Field(default=0, ge=0)
    extraction_success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    empty_extractions: int = Field(default=0, ge=0)
    rejected_boilerplate: int = Field(default=0, ge=0)


class BivNormalizeMetrics(BaseModel):
    normalized_documents: int = Field(default=0, ge=0)
    duplicate_documents: int = Field(default=0, ge=0)
    metadata_complete_rate: float = Field(default=0.0, ge=0.0, le=1.0)


class BivEvidenceStageMetrics(BaseModel):
    evidence_candidates: int = Field(default=0, ge=0)
    accepted_evidence: int = Field(default=0, ge=0)
    rejected_evidence: int = Field(default=0, ge=0)
    evidence_by_category: dict[str, int] = Field(default_factory=dict)
    evidence_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    rejection_reasons: dict[str, int] = Field(default_factory=dict)


class BivReasoningMetrics(BaseModel):
    findings_count: int = Field(default=0, ge=0)
    findings_with_evidence: int = Field(default=0, ge=0)
    unsupported_findings: int = Field(default=0, ge=0)
    citation_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    contradiction_count: int = Field(default=0, ge=0)


class BivReportStageMetrics(BaseModel):
    report_generated: bool = False
    report_validation_passed: bool = False
    empty_links: int = Field(default=0, ge=0)
    raw_dom_detected: int = Field(default=0, ge=0)
    unsupported_claims: int = Field(default=0, ge=0)
    export_validation_passed: bool = False


class BivCategoryFloorStatus(BaseModel):
    category: str = Field(min_length=1, max_length=64)
    required_floor: int = Field(ge=0)
    accepted_count: int = Field(default=0, ge=0)
    independent_source_count: int = Field(default=0, ge=0)
    status: str = Field(default="insufficient", max_length=32)
    attempts_summary: str = Field(default="", max_length=500)
    gap_reason: str | None = Field(default=None, max_length=500)
    impact_on_verdict: str | None = Field(default=None, max_length=500)


class BivNormalizedDocumentEntry(BaseModel):
    document_id: UUID
    run_id: UUID
    fetch_id: UUID | None = None
    source_url: str = Field(min_length=8, max_length=2048)
    title: str | None = Field(default=None, max_length=500)
    publisher: str | None = Field(default=None, max_length=255)
    published_at: str | None = Field(default=None, max_length=64)
    language: str = Field(default="unknown", max_length=16)
    region: str | None = Field(default=None, max_length=64)
    content_type: str = Field(default="text/plain", max_length=128)
    raw_length: int = Field(default=0, ge=0)
    clean_length: int = Field(default=0, ge=0)
    content_fingerprint: str = Field(default="", max_length=64)
    extraction_status: str = Field(default="rejected", max_length=32)
    rejection_reason: str | None = Field(default=None, max_length=64)
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)


class BivReportValidationResult(BaseModel):
    passed: bool = False
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocking_errors: list[str] = Field(default_factory=list)
    validated_at: datetime
    category_floors: list[BivCategoryFloorStatus] = Field(default_factory=list)


class BivPipelineMetrics(BaseModel):
    discovery: BivDiscoveryMetrics = Field(default_factory=BivDiscoveryMetrics)
    fetch: BivFetchStageMetrics = Field(default_factory=BivFetchStageMetrics)
    extract: BivExtractMetrics = Field(default_factory=BivExtractMetrics)
    normalize: BivNormalizeMetrics = Field(default_factory=BivNormalizeMetrics)
    evidence: BivEvidenceStageMetrics = Field(default_factory=BivEvidenceStageMetrics)
    reasoning: BivReasoningMetrics = Field(default_factory=BivReasoningMetrics)
    report: BivReportStageMetrics = Field(default_factory=BivReportStageMetrics)


class BivPipelineFailure(BaseModel):
    failure_stage: str = Field(min_length=1, max_length=64)
    failure_code: str = Field(min_length=1, max_length=128)
    retryable: bool = False
    safe_message: str = Field(min_length=1, max_length=1000)


class BivRunObservability(BaseModel):
    correlation_id: str = Field(min_length=1, max_length=128)
    run_id: UUID
    parent_run_id: UUID | None = None
    research_mode: BivResearchMode = BivResearchMode.INITIAL
    project_id: UUID
    user_request_id: UUID
    state_transitions: list[BivRunStateTransition] = Field(default_factory=list)
    stage_timings: dict[str, float] = Field(default_factory=dict)
    search_count: int = Field(default=0, ge=0)
    fetch_count: int = Field(default=0, ge=0)
    accepted_sources_count: int = Field(default=0, ge=0)
    rejected_sources_count: int = Field(default=0, ge=0)
    duplicate_sources_count: int = Field(default=0, ge=0)
    provider_errors: list[str] = Field(default_factory=list)
    confidence: int | None = Field(default=None, ge=0, le=100)
    coverage: int | None = Field(default=None, ge=0, le=100)
    verdict: BivCommercialVerdictKind | None = None
    export_status: str | None = Field(default=None, max_length=64)
    total_latency_ms: int | None = Field(default=None, ge=0)
    started_at: datetime
    finished_at: datetime | None = None
    pipeline_metrics: BivPipelineMetrics = Field(default_factory=BivPipelineMetrics)
    pipeline_failure: BivPipelineFailure | None = None
    fetch_ledger_count: int = Field(default=0, ge=0)


class BivEvidenceItem(BaseModel):
    evidence_id: UUID
    source_url: str = Field(min_length=8, max_length=2048)
    source_title: str = Field(min_length=1, max_length=500)
    publisher: str | None = Field(default=None, max_length=255)
    published_at: datetime | None = None
    accessed_at: datetime
    source_type: str = Field(default="observation", max_length=64)
    region: str | None = Field(default=None, max_length=64)
    language: str | None = Field(default=None, max_length=16)
    excerpt: str = Field(min_length=1, max_length=500)
    claim_supported: str = Field(min_length=1, max_length=500)
    relevance_score: float = Field(ge=0.0, le=1.0)
    quality_score: float = Field(ge=0.0, le=1.0)
    freshness_score: float = Field(ge=0.0, le=1.0)
    independence_group: str = Field(default="", max_length=128)
    category: str | None = Field(default=None, max_length=64)
    accepted: bool = False
    rejection_reason: str | None = Field(default=None, max_length=128)


class BivFindingItem(BaseModel):
    finding_id: UUID
    category: str = Field(min_length=1, max_length=64)
    claim: str = Field(min_length=1, max_length=500)
    interpretation: str = Field(min_length=1, max_length=500)
    business_impact: str = Field(min_length=1, max_length=500)
    evidence_ids: list[UUID] = Field(min_length=1)
    source_groups: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    limitations: list[str] = Field(default_factory=list)


class BivCommercialVerdict(BaseModel):
    kind: BivCommercialVerdictKind
    rationale: str = Field(min_length=1, max_length=2000)
    confirmed_assumptions: list[str] = Field(default_factory=list)
    unconfirmed_assumptions: list[str] = Field(default_factory=list)
    critical_risks: list[str] = Field(default_factory=list)
    go_no_go_conditions: list[str] = Field(default_factory=list)
    confidence: int = Field(ge=0, le=100)
    next_validation_action: str = Field(min_length=1, max_length=1000)


class BivResearchTerminalState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED_INSUFFICIENT = "succeeded_insufficient"
    SUCCEEDED_COMPLETE = "succeeded_complete"
    FAILED = "failed"


class BivResearchResultKind(StrEnum):
    COMPLETE_RESEARCH = "complete_research"
    PARTIAL_RESEARCH = "partial_research"


class BivStructuredEvidenceType(StrEnum):
    SOURCE_REFERENCE = "source_reference"
    OBSERVATION = "observation"
    STRUCTURED_FACT = "structured_fact"
    MARKET_SIGNAL = "market_signal"
    COMPETITOR_SIGNAL = "competitor_signal"
    CUSTOMER_SIGNAL = "customer_signal"
    ECONOMIC_SIGNAL = "economic_signal"
    RISK_SIGNAL = "risk_signal"
    HYPOTHESIS = "hypothesis"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    RESEARCH_GAP = "research_gap"


class BivEvidenceClassification(StrEnum):
    CONFIRMED = "confirmed"
    HYPOTHESIS = "hypothesis"
    RESEARCH_GAP = "research_gap"
    UNSUPPORTED_CLAIM = "unsupported_claim"


class BivSourceQualityTier(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class BivSourceReference(BaseModel):
    source_id: UUID
    title: str = Field(max_length=500)
    domain: str | None = Field(default=None, max_length=255)
    publisher: str | None = Field(default=None, max_length=255)
    published_at: datetime | None = None
    retrieved_at: datetime | None = None


class BusinessIdeaValidationInput(BaseModel):
    tenant_id: UUID
    project_id: UUID
    user_request_id: UUID
    idea: str = Field(min_length=8, max_length=8000)
    market: str | None = Field(default=None, max_length=500)
    location: str | None = Field(default=None, max_length=500)
    target_audience: str | None = Field(default=None, max_length=1000)
    budget: str | None = Field(default=None, max_length=500)
    constraints: str | None = Field(default=None, max_length=2000)
    product_or_service: str | None = Field(default=None, max_length=500)
    pricing_or_revenue_model: str | None = Field(default=None, max_length=500)
    known_competitors: str | None = Field(default=None, max_length=2000)
    analysis_goal: str | None = Field(default=None, max_length=500)
    current_stage: str | None = Field(default=None, max_length=240)


class BusinessIdeaValidationResearchPlanItem(BaseModel):
    category: str = Field(min_length=1, max_length=64)
    query: str = Field(min_length=1, max_length=512)
    rationale: str = Field(default="", max_length=1000)
    round_number: int = Field(default=1, ge=1, le=6)
    gap_directed: bool = False
    pipeline_phase: str = Field(default="direct", max_length=32)


class ResearchCoverageCategoryStatus(StrEnum):
    NOT_STARTED = "not_started"
    SEARCHING = "searching"
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    INSUFFICIENT = "insufficient"


class BusinessIdeaValidationSourceClass(StrEnum):
    OFFICIAL_STATISTICS = "official_statistics"
    REGULATORY = "regulatory"
    INDUSTRY_RESEARCH = "industry_research"
    FINANCIAL_RESEARCH = "financial_research"
    PROFESSIONAL_MEDIA = "professional_media"
    COMMERCIAL_BLOG = "commercial_blog"
    MARKETPLACE = "marketplace"
    USER_GENERATED = "user_generated"
    UNKNOWN = "unknown"


class ResearchCoverageCategoryItem(BaseModel):
    category: str = Field(min_length=1, max_length=64)
    required: bool = True
    status: ResearchCoverageCategoryStatus = ResearchCoverageCategoryStatus.NOT_STARTED
    source_ids: list[UUID] = Field(default_factory=list)
    evidence_ids: list[UUID] = Field(default_factory=list)
    finding_ids: list[str] = Field(default_factory=list)
    hypothesis_ids: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    follow_up_queries: list[str] = Field(default_factory=list)


class ResearchCoveragePlan(BaseModel):
    categories: list[ResearchCoverageCategoryItem] = Field(default_factory=list)
    research_rounds_completed: int = Field(default=0, ge=0, le=6)
    targeted_retry_categories: list[str] = Field(default_factory=list)
    independent_source_groups: list[str] = Field(default_factory=list)


class AudienceSegmentRecord(BaseModel):
    segment_id: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=240)
    needs: list[str] = Field(default_factory=list)
    purchase_context: str = Field(default="", max_length=1000)
    barriers: list[str] = Field(default_factory=list)
    price_sensitivity: str = Field(default="unknown", max_length=64)
    frequency: str = Field(default="unknown", max_length=64)
    acquisition_channels: list[str] = Field(default_factory=list)
    linked_evidence_ids: list[UUID] = Field(default_factory=list)
    is_hypothesis: bool = False
    limitations: list[str] = Field(default_factory=list)


class AudienceSegmentationOutput(BaseModel):
    segments: list[AudienceSegmentRecord] = Field(default_factory=list)
    hypotheses: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class BusinessIdeaValidationSourceSummary(BaseModel):
    source_id: UUID
    url: str
    title: str
    publisher: str | None = None
    domain: str | None = None
    published_at: datetime | None = None
    retrieved_at: datetime
    source_type: SourceType
    status: SourceStatus
    mcp_server_role: str
    mcp_tool_name: str
    content_hash: str | None = None
    source_class: BusinessIdeaValidationSourceClass = BusinessIdeaValidationSourceClass.UNKNOWN
    independence_group: str = Field(default="", max_length=128)
    reliability_rationale: str = Field(default="", max_length=500)
    research_category: str | None = Field(default=None, max_length=64)


class BusinessIdeaValidationEvidenceSummary(BaseModel):
    evidence_id: UUID
    source_id: UUID
    category: str = Field(default="other", max_length=64)
    evidence_type: BivStructuredEvidenceType = BivStructuredEvidenceType.OBSERVATION
    classification: BivEvidenceClassification = BivEvidenceClassification.HYPOTHESIS
    claim: str
    observation: str = Field(default="", max_length=2000)
    inference: str | None = Field(default=None, max_length=1000)
    supporting_excerpt: str
    source_reference: BivSourceReference | None = None
    source_url: str
    source_title: str
    publisher: str | None = None
    published_at: datetime | None = None
    retrieved_at: datetime
    relevance_score: float = Field(ge=0.0, le=1.0)
    reliability_score: float = Field(ge=0.0, le=1.0)
    freshness_score: float = Field(ge=0.0, le=1.0)
    source_quality_tier: BivSourceQualityTier = BivSourceQualityTier.D
    contradiction_status: str = Field(default="none", max_length=32)
    limitations: list[str] = Field(default_factory=list)
    sanitized: bool = True
    is_search_snippet: bool = False
    mcp_server_role: str
    mcp_tool_name: str


class BusinessIdeaValidationFinding(BaseModel):
    category: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=240)
    statement: str = Field(min_length=1, max_length=4000)
    linked_evidence_ids: list[UUID] = Field(default_factory=list)
    finding_type: VerdictFindingType = VerdictFindingType.STRENGTH
    is_hypothesis: bool = False


class BusinessIdeaValidationRisk(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(min_length=1, max_length=2000)
    severity: str = Field(default="medium", max_length=32)
    linked_evidence_ids: list[UUID] = Field(default_factory=list)


class BusinessIdeaValidationOpportunity(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(min_length=1, max_length=2000)
    linked_evidence_ids: list[UUID] = Field(default_factory=list)


class BusinessIdeaValidationConfidenceFactor(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    score: float = Field(ge=0.0, le=1.0)
    weight: float = Field(ge=0.0, le=1.0)
    weighted_score: float = Field(ge=0.0, le=1.0)


class BusinessIdeaValidationConfidence(BaseModel):
    total_score: int = Field(ge=0, le=100)
    calculation_version: str = Field(default="cmvp1_1_v1", max_length=32)
    factors: list[BusinessIdeaValidationConfidenceFactor] = Field(default_factory=list)
    penalties: list[str] = Field(default_factory=list)


class BusinessIdeaValidationNextStep(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=240)
    action: str = Field(min_length=1, max_length=64)


class BivResearchGapPresentation(BaseModel):
    """Customer-safe research gap — never expose raw codes alone in UI."""

    code: str = Field(min_length=1, max_length=128)
    message_key: str = Field(min_length=1, max_length=128)
    customer_message: str = Field(min_length=1, max_length=1000)
    recommended_action: str | None = Field(default=None, max_length=500)
    intake_field: str | None = Field(default=None, max_length=64)
    semantic_group: str | None = Field(default=None, max_length=64)


class BivCoverageAttemptStatus(StrEnum):
    NOT_RESEARCHED = "not_researched"
    NOT_FOUND = "not_found"
    FOUND_BUT_IRRELEVANT = "found_but_irrelevant"
    FOUND_BUT_LOW_QUALITY = "found_but_low_quality"
    NOT_CONFIRMED = "not_confirmed"
    CONFIRMED = "confirmed"
    CONFLICTED = "conflicted"
    USER_HYPOTHESIS = "user_hypothesis"


class BivResearchStopReasonCode(StrEnum):
    QUERY_TOO_BROAD = "query_too_broad"
    FEW_INDEPENDENT_SOURCES = "few_independent_sources"
    LOW_QUALITY_SOURCES = "low_quality_sources"
    MARKET_POORLY_COVERED = "market_poorly_covered"
    ICP_UNKNOWN = "icp_unknown"
    CONNECTOR_INSUFFICIENT = "connector_insufficient"
    CATEGORIES_NOT_RESEARCHED = "categories_not_researched"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class BivCategoryCoverageSummary(BaseModel):
    category: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=120)
    executed_query: str | None = Field(default=None, max_length=512)
    coverage_status: BivCoverageAttemptStatus = BivCoverageAttemptStatus.NOT_RESEARCHED
    customer_status_label: str = Field(default="", max_length=240)
    sources_found: int = Field(default=0, ge=0)
    sources_relevant: int = Field(default=0, ge=0)
    evidence_confirmed: int = Field(default=0, ge=0)
    evidence_hypothesis: int = Field(default=0, ge=0)
    stop_reason: str | None = Field(default=None, max_length=500)


class BivIntakeHypothesis(BaseModel):
    field: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=1000)
    message: str = Field(min_length=1, max_length=500)


class BivRemediationQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    intake_field: str | None = Field(default=None, max_length=64)
    related_categories: list[str] = Field(default_factory=list)
    semantic_group: str | None = Field(default=None, max_length=64)


class BivSemanticGapGroup(BaseModel):
    group_id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=1000)
    related_categories: list[str] = Field(default_factory=list)
    questions: list[BivRemediationQuestion] = Field(default_factory=list)


class BivResearchStopReason(BaseModel):
    code: BivResearchStopReasonCode
    customer_message: str = Field(min_length=1, max_length=1000)


class BivPartialResearchReport(BaseModel):
    established_findings: list[str] = Field(default_factory=list)
    probable_signals: list[str] = Field(default_factory=list)
    user_hypotheses: list[BivIntakeHypothesis] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    interim_conclusion: str = Field(default="", max_length=2000)


class BivCustomerSourceCitation(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    url: str | None = Field(default=None, max_length=2048)
    domain: str | None = Field(default=None, max_length=255)


class BivConfirmedFinding(BaseModel):
    headline: str = Field(min_length=1, max_length=500)
    explanation: str = Field(min_length=1, max_length=2000)
    sources: list[BivCustomerSourceCitation] = Field(default_factory=list)
    category: str = Field(default="", max_length=64)


class BivUnconfirmedTopic(BaseModel):
    topic: str = Field(min_length=1, max_length=240)
    reason: str = Field(min_length=1, max_length=1000)
    methods_used: list[str] = Field(default_factory=list)
    result_summary: str = Field(min_length=1, max_length=1000)
    confidence_impact: str | None = Field(default=None, max_length=500)


class BivDimensionConfidenceScore(BaseModel):
    dimension_id: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=120)
    score: int = Field(ge=0, le=100)


class BivResearchCoverageScore(BaseModel):
    dimensions_researched: list[str] = Field(default_factory=list)
    overall_percent: int = Field(ge=0, le=100)


class BivExecutiveSummary(BaseModel):
    title: str = Field(default="Предварительная оценка", max_length=120)
    status_line: str = Field(min_length=1, max_length=500)
    confidence_percent: int = Field(ge=0, le=100)
    primary_risk: str | None = Field(default=None, max_length=500)
    primary_advantage: str | None = Field(default=None, max_length=500)


class BivStructuredResearchVerdict(BaseModel):
    confirmed_summary: list[str] = Field(default_factory=list)
    unconfirmed_summary: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    verification_needed: list[str] = Field(default_factory=list)
    recommendation: str = Field(min_length=1, max_length=2000)
    confidence_percent: int = Field(ge=0, le=100)


class BivCustomerResearchReport(BaseModel):
    """Commercial-mode research conclusion — no engine diagnostics."""

    executive_summary: BivExecutiveSummary
    confirmed_findings: list[BivConfirmedFinding] = Field(default_factory=list)
    unconfirmed_topics: list[BivUnconfirmedTopic] = Field(default_factory=list)
    dimension_confidence: list[BivDimensionConfidenceScore] = Field(default_factory=list)
    overall_confidence_percent: int = Field(ge=0, le=100)
    coverage: BivResearchCoverageScore
    clarification_questions: list[str] = Field(default_factory=list)
    structured_verdict: BivStructuredResearchVerdict


class BivInternalResearchDiagnostics(BaseModel):
    """Debug / operator view — never shown in commercial UI by default."""

    search_queries: list[BusinessIdeaValidationResearchPlanItem] = Field(default_factory=list)
    raw_research_gaps: list[str] = Field(default_factory=list)
    raw_limitations: list[str] = Field(default_factory=list)
    category_coverage_internal: list[BivCategoryCoverageSummary] = Field(default_factory=list)
    confidence_calculation: BusinessIdeaValidationConfidence | None = None
    pipeline_phases_completed: list[str] = Field(default_factory=list)
    mcp_search_calls: int = Field(default=0, ge=0)
    mcp_fetch_calls: int = Field(default=0, ge=0)
    research_rounds_completed: int = Field(default=0, ge=0)
    tool_call_audit_ids: list[UUID] = Field(default_factory=list)
    raw_evidence: list[BusinessIdeaValidationEvidenceSummary] = Field(default_factory=list)
    raw_sources: list[BusinessIdeaValidationSourceSummary] = Field(default_factory=list)
    research_stop_reason_code: str | None = Field(default=None, max_length=64)
    coverage_plan: ResearchCoveragePlan = Field(default_factory=ResearchCoveragePlan)
    partial_report_internal: BivPartialResearchReport | None = None
    research_gap_items_internal: list[BivResearchGapPresentation] = Field(default_factory=list)
    pipeline_metrics: BivPipelineMetrics | None = None
    pipeline_failure: BivPipelineFailure | None = None


class BusinessIdeaValidationOutput(BaseModel):
    investigation_id: UUID
    business_verdict_id: UUID | None = None
    run_id: UUID | None = None
    owner_id: UUID | None = None
    project_id: UUID | None = None
    analysis_context_id: UUID | None = None
    input_snapshot_hash: str | None = None
    research_terminal_state: BivResearchTerminalState = BivResearchTerminalState.PENDING
    result_kind: BivResearchResultKind | None = None
    partial_failure_code: str | None = Field(default=None, max_length=128)
    partial_safe_message: str | None = Field(default=None, max_length=1000)
    research_gaps: list[str] = Field(default_factory=list)
    research_gap_items: list[BivResearchGapPresentation] = Field(default_factory=list)
    semantic_gap_groups: list[BivSemanticGapGroup] = Field(default_factory=list)
    remediation_questions: list[BivRemediationQuestion] = Field(default_factory=list)
    category_coverage: list[BivCategoryCoverageSummary] = Field(default_factory=list)
    research_stop_reason: BivResearchStopReason | None = None
    partial_report: BivPartialResearchReport | None = None
    research_plan: list[BusinessIdeaValidationResearchPlanItem] = Field(default_factory=list)
    coverage_plan: ResearchCoveragePlan = Field(default_factory=ResearchCoveragePlan)
    audience_segmentation: AudienceSegmentationOutput | None = None
    sources: list[BusinessIdeaValidationSourceSummary] = Field(default_factory=list)
    evidence: list[BusinessIdeaValidationEvidenceSummary] = Field(default_factory=list)
    findings: list[BusinessIdeaValidationFinding] = Field(default_factory=list)
    risks: list[BusinessIdeaValidationRisk] = Field(default_factory=list)
    opportunities: list[BusinessIdeaValidationOpportunity] = Field(default_factory=list)
    verdict: BusinessIdeaValidationVerdictKind
    confidence: BusinessIdeaValidationConfidence
    limitations: list[str] = Field(default_factory=list)
    next_steps: list[BusinessIdeaValidationNextStep] = Field(default_factory=list)
    tool_call_audit_ids: list[UUID] = Field(default_factory=list)
    research_rounds_completed: int = Field(default=0, ge=0, le=6)
    mcp_search_calls: int = Field(default=0, ge=0)
    mcp_fetch_calls: int = Field(default=0, ge=0)
    customer_report: BivCustomerResearchReport | None = None
    internal_diagnostics: BivInternalResearchDiagnostics | None = None
    research_mode: BivResearchMode | None = None
    parent_run_id: UUID | None = None
    evidence_items: list[BivEvidenceItem] = Field(default_factory=list)
    finding_items: list[BivFindingItem] = Field(default_factory=list)
    commercial_verdict: BivCommercialVerdict | None = None
    run_progress: BivRunProgress | None = None


class BusinessIdeaValidationRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idempotency_key: str = Field(min_length=8, max_length=128)
    analysis_context_id: UUID
    input_snapshot_hash: str = Field(min_length=64, max_length=64)
    research_mode: BivResearchMode = BivResearchMode.INITIAL
    research_intent: bool = False
    rerun_intent: bool = False
    parent_run_id: UUID | None = None
    rerun_reason: str | None = Field(default=None, max_length=240)
    changed_fields: list[str] = Field(default_factory=list)
    idea: str | None = Field(default=None, max_length=8000)
    market: str | None = Field(default=None, max_length=500)
    location: str | None = Field(default=None, max_length=500)
    target_audience: str | None = Field(default=None, max_length=1000)
    budget: str | None = Field(default=None, max_length=500)
    constraints: str | None = Field(default=None, max_length=2000)


class BusinessIdeaValidationRunResponse(BaseModel):
    run_id: UUID
    user_request_id: UUID
    project_id: UUID | None = None
    analysis_context_id: UUID | None = None
    input_snapshot_hash: str | None = None
    status: BusinessIdeaValidationRunStatus
    research_mode: BivResearchMode | None = None
    parent_run_id: UUID | None = None
    output: BusinessIdeaValidationOutput | None = None
    error_code: str | None = None
    safe_message: str | None = None
    lineage_reused: bool = False
    progress: BivRunProgress | None = None


class BusinessIdeaValidationAsyncRunAcceptedResponse(BaseModel):
    """202 Accepted — async research enqueue; state is persisted before dispatch."""

    run_id: UUID
    user_request_id: UUID
    project_id: UUID
    analysis_context_id: UUID
    input_snapshot_hash: str
    status: BusinessIdeaValidationRunStatus
    progress: BivRunProgress | None = None
    created_at: datetime
    lineage_reused: bool = False


class BusinessIdeaValidationProjectHydration(BaseModel):
    """Backend source of truth for restoring a validation journey on a project."""
    project_id: UUID
    user_request_id: UUID
    user_request_text: str
    run_id: UUID
    analysis_context_id: UUID | None = None
    input_snapshot_hash: str | None = None
    status: BusinessIdeaValidationRunStatus
    output: BusinessIdeaValidationOutput
    updated_at: datetime


class BusinessIdeaValidationProjectLatestRunSummary(BaseModel):
    """Project-level latest BIV run for recovery (active or terminal)."""

    project_id: UUID
    run_id: UUID
    user_request_id: UUID
    status: BusinessIdeaValidationRunStatus
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    progress: BivRunProgress | None = None
    result_kind: str | None = None
    research_terminal_state: BivResearchTerminalState | None = None
    safe_error_code: str | None = None
    safe_message: str | None = None
    has_output: bool = False
    retry_allowed: bool = False
    analysis_context_id: UUID | None = None
    input_snapshot_hash: str | None = None


# --- CWF.1a Launch Pack decision + request ---


class LaunchPackRequestStatus(StrEnum):
    NOT_REQUESTED = "not_requested"
    REQUESTED = "requested"
    BLOCKED = "blocked"
    IN_PROGRESS = "in_progress"
    READY = "ready"
    CANCELLED = "cancelled"


class CommercialNextStepAction(StrEnum):
    PREPARE_LAUNCH = "prepare_launch"
    REVISE_IDEA = "revise_idea"
    REFINE_INPUTS = "refine_inputs"
    REQUEST_ALTERNATIVE = "request_alternative"
    STOP_PROJECT = "stop_project"


class VerdictDecisionCta(BaseModel):
    action: CommercialNextStepAction
    label_key: str = Field(min_length=1, max_length=128)
    is_primary: bool = False
    requires_conditions_acceptance: bool = False
    requires_risk_override: bool = False


class VerdictDecisionBranch(BaseModel):
    """Backend-computed commercial branch — frontend must not infer verdict routing."""
    verdict: BusinessIdeaValidationVerdictKind
    headline_key: str = Field(min_length=1, max_length=128)
    explanation: str = Field(min_length=1, max_length=4000)
    recommended_next_step_key: str = Field(min_length=1, max_length=128)
    launch_pack_allowed: bool
    conditions: list[str] = Field(default_factory=list)
    primary_cta: VerdictDecisionCta | None = None
    secondary_ctas: list[VerdictDecisionCta] = Field(default_factory=list)
    launch_pack_included_keys: list[str] = Field(default_factory=list)
    launch_pack_excluded_keys: list[str] = Field(default_factory=list)


class CommercialNextStepDecisionCreate(BaseModel):
    selected_action: CommercialNextStepAction
    accepted_conditions: list[str] = Field(default_factory=list)
    override_reason: str | None = Field(default=None, max_length=2000)
    idempotency_key: str = Field(min_length=8, max_length=128)


class CommercialNextStepDecision(BaseModel):
    id: UUID
    tenant_id: UUID
    project_id: UUID
    user_request_id: UUID
    business_verdict_id: UUID
    selected_action: CommercialNextStepAction
    accepted_conditions: list[str] = Field(default_factory=list)
    override_reason: str | None = None
    created_at: datetime
    updated_at: datetime


# --- PRODUCT-01 Offer Builder + CWF integration ---


class UpstreamSourceMode(StrEnum):
    NATIVE_SKILL_OUTPUT = "native_skill_output"
    BRIDGED_BIV_SNAPSHOT = "bridged_biv_snapshot"


class UpstreamSnapshotSummary(BaseModel):
    artifact_type: str
    source_skill_id: str
    source_skill_version: str
    source_mode: UpstreamSourceMode
    bridge_version: str | None = None
    source_biv_id: UUID | None = None
    source_biv_hash: str | None = None
    generated_from_fields: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    replacement_required: bool = False
    source_output_hash: str = ""


class LaunchPackOfferWorkflowStatus(StrEnum):
    NOT_STARTED = "not_started"
    REQUESTED = "requested"
    BUILDING_OFFER = "building_offer"
    OFFER_REVIEW_REQUIRED = "offer_review_required"
    OFFER_APPROVED = "offer_approved"
    READY_FOR_NEXT_STAGE = "ready_for_next_stage"
    BLOCKED_BY_VERDICT = "blocked_by_verdict"
    BLOCKED_BY_MISSING_POSITIONING = "blocked_by_missing_positioning"
    BLOCKED_BY_CLAIMS = "blocked_by_claims"
    BLOCKED_BY_EVIDENCE = "blocked_by_evidence"
    OFFER_GENERATION_FAILED = "offer_generation_failed"
    OFFER_REJECTED = "offer_rejected"
    REVISION_REQUIRED = "revision_required"


class OfferArtifactStatus(StrEnum):
    REQUESTED = "requested"
    GENERATING = "generating"
    GENERATED = "generated"
    REVIEW_REQUIRED = "review_required"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OfferApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


class UpstreamArtifactReference(BaseModel):
    artifact_id: UUID
    source_skill_id: str
    source_skill_version: str
    source_package_hash: str = Field(min_length=64, max_length=64)
    source_output_hash: str = Field(min_length=64, max_length=64)
    source_status: str = "complete"
    tenant_id: UUID
    project_id: UUID
    evidence_references: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)


class OfferArtifactSummary(BaseModel):
    id: UUID
    launch_pack_request_id: UUID
    project_id: UUID
    skill_id: str
    skill_version: str
    status: OfferArtifactStatus
    approval_status: OfferApprovalStatus
    version_number: int = Field(ge=1)
    offer_title: str = ""
    offer_summary: str = ""
    human_review_required: bool = True
    output_hash: str = ""
    blocker_code: str | None = None
    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None = None


class OfferArtifactDetail(OfferArtifactSummary):
    problem_statement: str = ""
    promised_outcome: str = ""
    value_proposition: str = ""
    offer_components: list[str] = Field(default_factory=list)
    proof_references: list[str] = Field(default_factory=list)
    objection_handling: list[dict[str, Any]] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    cta: str = ""
    unsupported_claims: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    target_segment_ids: list[str] = Field(default_factory=list)
    preferred_offer_id: str | None = None
    offer_readiness: str = ""
    revision_of_id: UUID | None = None
    lineage_metadata: dict[str, Any] = Field(default_factory=dict)
    upstream_sources: list[UpstreamSnapshotSummary] = Field(default_factory=list)


class OfferRecoverResponse(BaseModel):
    offer: OfferArtifactDetail
    recovered_from: str
    launch_pack_workflow_status: LaunchPackOfferWorkflowStatus


class OfferVersionHistoryItem(BaseModel):
    id: UUID
    version_number: int
    status: OfferArtifactStatus
    output_hash: str
    offer_title: str
    created_at: datetime
    approval_status: OfferApprovalStatus


class OfferGenerateRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=128)


class OfferReviewDecisionCreate(BaseModel):
    expected_output_hash: str = Field(min_length=64, max_length=64)
    comment: str | None = Field(default=None, max_length=2000)


class OfferRevisionRequestCreate(BaseModel):
    expected_output_hash: str = Field(min_length=64, max_length=64)
    comment: str = Field(min_length=1, max_length=2000)


class OfferGenerateResponse(BaseModel):
    offer: OfferArtifactDetail | None = None
    launch_pack_workflow_status: LaunchPackOfferWorkflowStatus
    blocker_code: str | None = None
    lineage_reused: bool = False


class LaunchPackRequest(BaseModel):
    id: UUID
    tenant_id: UUID
    project_id: UUID
    user_request_id: UUID
    business_verdict_id: UUID
    next_step_decision_id: UUID
    status: LaunchPackRequestStatus
    selected_next_step: CommercialNextStepAction
    accepted_conditions: list[str] = Field(default_factory=list)
    source_verdict_type: BusinessIdeaValidationVerdictKind
    source_confidence: int = Field(ge=0, le=100)
    offer_workflow_status: LaunchPackOfferWorkflowStatus = LaunchPackOfferWorkflowStatus.NOT_STARTED
    offer_artifact_id: UUID | None = None
    offer_version: int | None = None
    offer_status: OfferArtifactStatus | None = None
    blocker_codes: list[str] = Field(default_factory=list)
    next_allowed_action: str | None = None
    created_at: datetime
    updated_at: datetime


class LaunchPackJourneyHydration(BaseModel):
    """CWF.1a — restore verdict decision + launch pack request from backend."""
    project_id: UUID
    user_request_id: UUID
    user_request_text: str
    validation: BusinessIdeaValidationProjectHydration
    decision_branch: VerdictDecisionBranch
    next_step_decision: CommercialNextStepDecision | None = None
    launch_pack_request: LaunchPackRequest | None = None
    offer: OfferArtifactDetail | None = None
    updated_at: datetime


class CommercialNextStepSubmitResponse(BaseModel):
    decision: CommercialNextStepDecision
    launch_pack_request: LaunchPackRequest | None = None
    offer: OfferArtifactDetail | None = None
    decision_branch: VerdictDecisionBranch
    lineage_reused: bool = False


class McpServerRole(StrEnum):
    SEARCH_MCP = "search_mcp"
    WEB_FETCH_MCP = "web_fetch_mcp"


class McpToolCallStatus(StrEnum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"


class McpToolCallAuditRecord(BaseModel):
    id: UUID
    tenant_id: UUID
    owner_id: UUID
    user_request_id: UUID
    investigation_id: UUID | None = None
    server_role: McpServerRole
    server_id: str
    tool_name: str
    tool_schema_fingerprint: str
    status: McpToolCallStatus
    duration_ms: int = Field(ge=0)
    response_size_bytes: int = Field(ge=0)
    error_code: str | None = None
    created_at: datetime


# --- SKILL-01.1 Skill Package Domain Contracts (RFC-SKILL-001/002) ---


class SkillLifecycleStatus(StrEnum):
    """Skill registry lifecycle — no ``paused`` (OD-003)."""

    CANDIDATE = "candidate"
    QUARANTINED = "quarantined"
    AUDITED = "audited"
    APPROVED = "approved"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    REJECTED = "rejected"
    TENANT_PRIVATE = "tenant_private"
    TENANT_ACTIVE = "tenant_active"


class SkillSourceType(StrEnum):
    PLATFORM_NATIVE = "platform_native"
    PLATFORM_ADAPTED = "platform_adapted"
    TENANT_PRIVATE = "tenant_private"
    EXTERNAL_IMPORT = "external_import"


class SkillTenantScope(StrEnum):
    GLOBAL = "global"
    TENANT_PRIVATE = "tenant_private"


class SkillDependencyRelationship(StrEnum):
    OPTIONAL_DEPENDENCY = "optional_dependency"
    DECLARED_FUTURE_DEPENDENCY = "declared_future_dependency"
    UNRESOLVED_DEPENDENCY = "unresolved_dependency"
    REQUIRED_DEPENDENCY = "required_dependency"


class SkillNetworkPolicyDefault(StrEnum):
    DENY = "deny"
    ALLOW = "allow"


class SkillEvidenceClass(StrEnum):
    USER_STATEMENT = "user_statement"
    MARKET_SOURCE = "market_source"
    COMPETITOR_SOURCE = "competitor_source"
    DEMAND_SIGNAL = "demand_signal"
    PRICING_SIGNAL = "pricing_signal"
    AUDIENCE_SIGNAL = "audience_signal"
    ASSUMPTION = "assumption"
    INFERENCE = "inference"


class SkillValidationVerdict(StrEnum):
    """Package I/O verdict values — distinct from ``BusinessIdeaValidationVerdictKind``."""

    PROCEED = "proceed"
    PROCEED_WITH_CONDITIONS = "proceed_with_conditions"
    REVISE = "revise"
    DEFER = "defer"
    STOP = "stop"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class SkillContextReadiness(StrEnum):
    """Context-normalization output readiness — not a commercial viability verdict."""

    READY = "ready"
    PARTIALLY_READY = "partially_ready"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    CONFLICTED = "conflicted"


class SkillOutputContractType(StrEnum):
    """Output I/O contract class — validator checks discriminators by type, not skill_id."""

    CONTEXT = "context"
    RESEARCH = "research"
    DECISION = "decision"
    EXECUTION = "execution"


class SkillResearchStatus(StrEnum):
    """Research output status — not a commercial viability verdict."""

    COMPLETE = "complete"
    PARTIALLY_COMPLETE = "partially_complete"
    INSUFFICIENT_SOURCES = "insufficient_sources"
    CONFLICTED = "conflicted"
    OUT_OF_SCOPE = "out_of_scope"


class SkillEvidenceQuality(StrEnum):
    """Research evidence quality assessment — distinct from claim confidence."""

    COMPREHENSIVE = "comprehensive"
    PARTIAL = "partial"
    INSUFFICIENT = "insufficient"
    CONFLICTED = "conflicted"
    UNKNOWN = "unknown"


class SkillResearchCoverage(StrEnum):
    """Research scope coverage assessment."""

    FULL = "full"
    PARTIAL = "partial"
    MINIMAL = "minimal"
    UNKNOWN = "unknown"


class SkillExecutionStatus(StrEnum):
    """Execution output status — reserved for future execution Skills (not SKILL-02)."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


SKILL_ID_PATTERN = r"^ms\.skill\.[a-z0-9_]+$"
SKILL_VERSION_PATTERN = r"^\d+\.\d+\.\d+$"


class SkillSchemaReference(BaseModel):
    schema_ref: str = Field(min_length=1, max_length=256)


class SkillInputSchemaReference(SkillSchemaReference):
    """Pointer to package input JSON Schema file."""


class SkillOutputSchemaReference(SkillSchemaReference):
    """Pointer to package output JSON Schema file."""


class SkillEvidenceRule(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    description: str = Field(min_length=1, max_length=2000)
    threshold_ref: str | None = Field(default=None, max_length=128)


class SkillEvidencePolicy(BaseModel):
    classes: list[SkillEvidenceClass] = Field(min_length=1)
    rules: list[SkillEvidenceRule] = Field(default_factory=list)


class SkillApprovalPolicyStage(BaseModel):
    external_side_effects: bool | None = None
    approval_required: bool | None = None
    note: str | None = Field(default=None, max_length=2000)
    governed_by: str | None = Field(default=None, max_length=128)
    skill_bypass_allowed: bool | None = None


class SkillApprovalPolicy(BaseModel):
    analysis_preparation: SkillApprovalPolicyStage | None = None
    verdict_presentation: SkillApprovalPolicyStage | None = None
    launch_or_execution_transition: SkillApprovalPolicyStage | None = None
    paid_or_write_actions: SkillApprovalPolicyStage | None = None
    publication: SkillApprovalPolicyStage | None = None


class SkillNetworkPolicy(BaseModel):
    default: SkillNetworkPolicyDefault = SkillNetworkPolicyDefault.DENY
    allowed_hosts: list[str] = Field(default_factory=list)
    allowed_connectors_only: bool = True


class SkillScriptPolicy(BaseModel):
    enabled: bool = False
    reason: str | None = Field(default=None, max_length=500)


class SkillActivationConditions(BaseModel):
    runtime_compatibility: list[str] = Field(default_factory=list)
    requires_governed_context: bool = False
    executable: bool = False


class SkillDependency(BaseModel):
    id: str = Field(min_length=1, max_length=128, pattern=SKILL_ID_PATTERN)
    relationship: SkillDependencyRelationship
    note: str | None = Field(default=None, max_length=2000)


class SkillDependencies(BaseModel):
    declared_future_dependencies: list[SkillDependency] = Field(default_factory=list)


class SkillQualityThreshold(BaseModel):
    eval_required_before_active: bool = True
    minimum_eval_cases: int = Field(default=1, ge=0)
    current_state: str | None = Field(default=None, max_length=64)


class SkillTestSuiteRef(BaseModel):
    manifest: str | None = Field(default=None, max_length=256)
    backend_tests: str | None = Field(default=None, max_length=256)


class SkillExternalMethodologyReference(BaseModel):
    audit_card: str | None = None
    reuse: str | None = None
    license: str | None = None
    note: str | None = None


class SkillProvenance(BaseModel):
    origin: SkillSourceType | str
    methodology: list[str] = Field(default_factory=list)
    external_methodology_references: list[SkillExternalMethodologyReference] = Field(
        default_factory=list
    )
    external_code_dependency: bool = False
    direct_external_skill_install: bool = False
    audit_research_id: str | None = Field(
        default=None,
        description="Research audit label only (e.g. MS-SKILL-005) — not production skill_id.",
    )


class SkillResourceLimits(BaseModel):
    max_package_size_mib: int = Field(default=10, ge=1)
    max_skill_md_kib: int = Field(default=256, ge=1)


class SkillManifest(BaseModel):
    """Domain contract for MSP manifest.yaml — canonical for registry/validator."""

    id: str = Field(min_length=1, max_length=128, pattern=SKILL_ID_PATTERN)
    name: str = Field(min_length=1, max_length=240)
    version: str = Field(min_length=1, max_length=32, pattern=SKILL_VERSION_PATTERN)
    description: str = Field(min_length=1, max_length=4000)
    owner: str = Field(min_length=1, max_length=240)
    source: SkillSourceType
    license: str = Field(min_length=1, max_length=64)
    status: SkillLifecycleStatus
    output_contract_type: SkillOutputContractType | None = None
    capabilities: list[str] = Field(min_length=1)
    activation_conditions: SkillActivationConditions
    required_inputs: SkillInputSchemaReference
    output_schema: SkillOutputSchemaReference
    required_evidence: SkillEvidencePolicy
    dependencies: SkillDependencies
    allowed_tools: list[str] = Field(default_factory=list)
    approval_policy: SkillApprovalPolicy
    tenant_scope: SkillTenantScope
    quality_threshold: SkillQualityThreshold
    known_limitations: list[str] = Field(default_factory=list)
    test_suite: SkillTestSuiteRef
    provenance: SkillProvenance
    runtime_compatibility: list[str] = Field(default_factory=list)
    knowledge_scopes: list[str] = Field(default_factory=list)
    network_policy: SkillNetworkPolicy = Field(default_factory=SkillNetworkPolicy)
    script_policy: SkillScriptPolicy = Field(default_factory=SkillScriptPolicy)
    resource_limits: SkillResourceLimits | None = None

    def normalized_registry_snapshot(self) -> dict[str, Any]:
        """Deterministic dict for round-trip tests and future registry read model."""
        return self.model_dump(mode="json", exclude_none=True)

    def is_non_active_skeleton(self) -> bool:
        return self.status in {
            SkillLifecycleStatus.CANDIDATE,
            SkillLifecycleStatus.QUARANTINED,
        }

    def permissions_deny_by_default(self) -> bool:
        return (
            self.allowed_tools == []
            and self.network_policy.default == SkillNetworkPolicyDefault.DENY
            and not self.script_policy.enabled
        )


class SkillPackageDescriptor(BaseModel):
    """Immutable package identity + frozen content hash — no file I/O."""

    skill_id: str = Field(pattern=SKILL_ID_PATTERN)
    version: str = Field(pattern=SKILL_VERSION_PATTERN)
    status: SkillLifecycleStatus
    package_root: str = Field(min_length=1, max_length=256)
    content_hash_sha256: str = Field(min_length=64, max_length=64)
    manifest: SkillManifest


SKILL_LIFECYCLE_TRANSITIONS: dict[SkillLifecycleStatus, frozenset[SkillLifecycleStatus]] = {
    SkillLifecycleStatus.CANDIDATE: frozenset(
        {SkillLifecycleStatus.QUARANTINED, SkillLifecycleStatus.AUDITED, SkillLifecycleStatus.REJECTED}
    ),
    SkillLifecycleStatus.QUARANTINED: frozenset(
        {SkillLifecycleStatus.AUDITED, SkillLifecycleStatus.REJECTED}
    ),
    SkillLifecycleStatus.AUDITED: frozenset(
        {SkillLifecycleStatus.APPROVED, SkillLifecycleStatus.REJECTED}
    ),
    SkillLifecycleStatus.APPROVED: frozenset(
        {SkillLifecycleStatus.ACTIVE, SkillLifecycleStatus.QUARANTINED, SkillLifecycleStatus.REJECTED}
    ),
    SkillLifecycleStatus.ACTIVE: frozenset(
        {SkillLifecycleStatus.DEPRECATED, SkillLifecycleStatus.SUSPENDED, SkillLifecycleStatus.REJECTED}
    ),
    SkillLifecycleStatus.SUSPENDED: frozenset(
        {SkillLifecycleStatus.ACTIVE, SkillLifecycleStatus.ARCHIVED, SkillLifecycleStatus.REJECTED}
    ),
    SkillLifecycleStatus.DEPRECATED: frozenset({SkillLifecycleStatus.ARCHIVED}),
    SkillLifecycleStatus.TENANT_PRIVATE: frozenset(
        {SkillLifecycleStatus.TENANT_ACTIVE, SkillLifecycleStatus.REJECTED}
    ),
    SkillLifecycleStatus.TENANT_ACTIVE: frozenset(
        {SkillLifecycleStatus.SUSPENDED, SkillLifecycleStatus.AUDITED, SkillLifecycleStatus.REJECTED}
    ),
    SkillLifecycleStatus.ARCHIVED: frozenset(),
    SkillLifecycleStatus.REJECTED: frozenset(),
}


def skill_lifecycle_transition_allowed(
    from_status: SkillLifecycleStatus,
    to_status: SkillLifecycleStatus,
) -> bool:
    allowed = SKILL_LIFECYCLE_TRANSITIONS.get(from_status, frozenset())
    return to_status in allowed


def skill_lifecycle_forbids_paused() -> bool:
    return "paused" not in {member.value for member in SkillLifecycleStatus}


SkillId = str
SkillVersion = str
SkillCapability = str


# --- Media Renderer / Higgsfield connector (CONN-HF-01) ---


class MediaRenderAssetType(StrEnum):
    """Fully-specified render target — renderer must not infer asset intent."""

    IMAGE = "image"
    VIDEO = "video"


class MediaRenderJobStatus(StrEnum):
    PLANNED_ONLY = "planned_only"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    APPROVAL_REQUIRED = "approval_required"


class MediaCanonicalOperation(StrEnum):
    """Marketsynth-internal media operations — not provider MCP tool names."""

    IMAGE_GENERATE = "media.image.generate"
    VIDEO_GENERATE = "media.video.generate"
    JOB_GET_STATUS = "media.job.get_status"
    ASSET_FETCH = "media.asset.fetch"


class MediaProviderJobStatus(StrEnum):
    """Normalized provider job statuses — unknown provider states stay unknown."""

    SUBMITTED = "submitted"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


class MediaRenderPlanStatus(StrEnum):
    PLANNED_ONLY = "planned_only"


class MediaOperationMappingStatus(StrEnum):
    UNVERIFIED = "unverified"
    MAPPED = "mapped"
    UNSUPPORTED = "unsupported"


class MediaRenderPlan(BaseModel):
    """Local dry-run plan — zero MCP network traffic."""

    model_config = ConfigDict(extra="forbid")

    status: MediaRenderPlanStatus = MediaRenderPlanStatus.PLANNED_ONLY
    spec_hash: str = ""
    canonical_operation: MediaCanonicalOperation
    connector_requirements: dict[str, Any] = Field(default_factory=dict)
    policy_summary: dict[str, Any] = Field(default_factory=dict)
    estimated_cost_visibility: Literal["known", "unknown"] = "unknown"
    provider_tool_mapping_status: MediaOperationMappingStatus = (
        MediaOperationMappingStatus.UNVERIFIED
    )
    connector_verification_status: str = "sandbox_verification_required"


class MediaRenderReference(BaseModel):
    """Reference asset for renderer — URL or internal asset id only."""

    model_config = ConfigDict(extra="forbid")

    ref_type: Literal["url", "asset_id"] = "url"
    value: str = Field(min_length=1, max_length=2048)
    role: str = Field(default="reference", max_length=64)


class MediaRenderSpec(BaseModel):
    """Complete render specification from upstream Skills — no business inference."""

    model_config = ConfigDict(extra="forbid")

    asset_type: MediaRenderAssetType
    style: str = Field(min_length=1, max_length=128)
    aspect_ratio: str = Field(default="16:9", max_length=16)
    brand: str = Field(default="", max_length=256)
    prompt: str = Field(min_length=1, max_length=8000)
    negative_prompt: str = Field(default="", max_length=4000)
    references: list[MediaRenderReference] = Field(default_factory=list, max_length=10)
    approval_required: bool = True
    model: str | None = Field(default=None, max_length=128)
    duration_seconds: int | None = Field(default=None, ge=1, le=60)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MediaRenderRequest(BaseModel):
    """Explicit render invocation — upstream skill must have produced the spec."""

    model_config = ConfigDict(extra="forbid")

    spec: MediaRenderSpec
    upstream_skill_id: str = Field(min_length=1, max_length=128)
    upstream_skill_version: str = Field(default="0.1.0", max_length=32)
    explicit_confirmation: bool = False
    dry_run: bool = True
    approval_reference: str | None = Field(default=None, max_length=128)
    idempotency_key: str | None = Field(default=None, max_length=128)
    accept_unknown_cost: bool = False


class MediaRenderJobResponse(BaseModel):
    job_id: str
    status: MediaRenderJobStatus
    connector_id: str = "connector.higgsfield"
    renderer: str = "higgsfield_mcp"
    asset_type: MediaRenderAssetType
    dry_run: bool = True
    paid_call_performed: bool = False
    result_url: str | None = None
    mime_type: str | None = None
    external_reference_id: str | None = None
    detail_code: str = ""
    detail_message: str = ""
    spec_hash: str = ""
    evidence_id: UUID | None = None


class MediaRendererReadiness(BaseModel):
    enabled: bool = False
    configured: bool = False
    connector_status: str = "quarantined"
    connector_verification_status: str = "sandbox_verification_required"
    sandbox_verified: bool = False
    live_render_available: bool = False
    image_render_available: bool = False
    video_render_available: bool = False
    requires_explicit_confirmation: bool = True
    requires_approval: bool = True
    detail_code: str = ""
    detail_message: str = ""
    discovered_mcp_tools: list[str] = Field(default_factory=list)


# --- PRODUCT-CD-RUNTIME-01 Content Director (Text Golden Path) ---


class ContentRequestContextSource(StrEnum):
    MANUAL = "manual"


class ContentDirectorChannel(StrEnum):
    TELEGRAM = "telegram"


class ContentDirectorContentType(StrEnum):
    TELEGRAM_POST = "telegram_post"


class ContentRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class ContentRequestCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    objective: str = Field(min_length=1, max_length=2000)
    channel: ContentDirectorChannel = ContentDirectorChannel.TELEGRAM
    content_type: ContentDirectorContentType = ContentDirectorContentType.TELEGRAM_POST
    audience_description: str = Field(min_length=1, max_length=2000)
    key_message: str = Field(min_length=1, max_length=2000)
    offer_value_proposition: str = Field(default="", max_length=2000)
    tone: str = Field(default="professional", max_length=120)
    language: str = Field(default="ru", max_length=16)
    length: str = Field(default="medium", max_length=64)
    cta: str = Field(default="", max_length=500)
    must_include: str = Field(default="", max_length=2000)
    must_avoid: str = Field(default="", max_length=2000)
    requested_variants: int = Field(default=2, ge=1, le=3)
    context_source: ContentRequestContextSource = ContentRequestContextSource.MANUAL


class ContentRequestUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    objective: str | None = Field(default=None, min_length=1, max_length=2000)
    audience_description: str | None = Field(default=None, min_length=1, max_length=2000)
    key_message: str | None = Field(default=None, min_length=1, max_length=2000)
    offer_value_proposition: str | None = Field(default=None, max_length=2000)
    tone: str | None = Field(default=None, max_length=120)
    language: str | None = Field(default=None, max_length=16)
    length: str | None = Field(default=None, max_length=64)
    cta: str | None = Field(default=None, max_length=500)
    must_include: str | None = Field(default=None, max_length=2000)
    must_avoid: str | None = Field(default=None, max_length=2000)
    requested_variants: int | None = Field(default=None, ge=1, le=3)


class ContentRequestRead(BaseModel):
    id: UUID
    owner_id: UUID
    project_id: UUID
    version: int
    context_source: ContentRequestContextSource
    title: str
    objective: str
    channel: ContentDirectorChannel
    content_type: ContentDirectorContentType
    audience_description: str
    key_message: str
    offer_value_proposition: str
    tone: str
    language: str
    length: str
    cta: str
    must_include: str
    must_avoid: str
    requested_variants: int
    current_run_id: UUID | None = None
    approved_asset_id: UUID | None = None
    approved_version_number: int | None = None
    created_at: datetime
    updated_at: datetime


class ContentInputSnapshotRead(BaseModel):
    id: UUID
    content_request_id: UUID
    content_request_version: int
    payload: dict[str, Any]
    created_at: datetime


class ContentRunRead(BaseModel):
    id: UUID
    owner_id: UUID
    project_id: UUID
    content_request_id: UUID
    content_request_version: int
    snapshot_id: UUID
    status: ContentRunStatus
    attempt: int
    error_code: str | None = None
    error_message: str | None = None
    provider: str | None = None
    model: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class ContentDirectorCandidateRead(BaseModel):
    asset_id: UUID
    content_run_id: UUID
    content_request_id: UUID
    content_request_version: int
    candidate_index: int
    title: str
    body: str
    status: str
    current_version_number: int
    approved_version_number: int | None = None
    rejected: bool = False


class ContentDirectorGenerateRequest(BaseModel):
    idempotency_key: str | None = Field(default=None, max_length=128)


class ContentDirectorEditRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=512)
    body: str = Field(min_length=1, max_length=20000)


class ContentDirectorApproveRequest(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


class ContentDirectorWorkspaceState(BaseModel):
    request: ContentRequestRead | None = None
    active_run: ContentRunRead | None = None
    candidates: list[ContentDirectorCandidateRead] = Field(default_factory=list)
    approved_asset_id: UUID | None = None
    approved_version_number: int | None = None
    next_action: str = "create_request"
    applied_skill_id: str | None = None
    applied_skill_version: str | None = None


# --- PRODUCT-CD-RUNTIME-02 Visual Director (Image Golden Path) ---


class VisualRequestContextSource(StrEnum):
    MANUAL = "manual"


class VisualFormat(StrEnum):
    SOCIAL_POST_IMAGE = "social_post_image"


class VisualAspectRatio(StrEnum):
    RATIO_1_1 = "1:1"
    RATIO_16_9 = "16:9"
    RATIO_9_16 = "9:16"


class VisualRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class ImageAssetStatus(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    ARCHIVED = "archived"


class VisualRequestCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    objective: str = Field(min_length=1, max_length=2000)
    scene_description: str = Field(min_length=1, max_length=4000)
    subject: str = Field(min_length=1, max_length=1000)
    style: str = Field(default="clean commercial", max_length=240)
    audience: str = Field(min_length=1, max_length=2000)
    mood: str = Field(default="confident", max_length=240)
    aspect_ratio: VisualAspectRatio = VisualAspectRatio.RATIO_1_1
    visual_format: VisualFormat = VisualFormat.SOCIAL_POST_IMAGE
    requested_variants: int = Field(default=2, ge=1, le=4)
    text_overlay: str = Field(default="", max_length=500)
    must_include: str = Field(default="", max_length=2000)
    must_avoid: str = Field(default="", max_length=2000)
    related_text_asset_id: UUID | None = None
    reference_asset_ids: list[UUID] = Field(default_factory=list, max_length=5)
    language: str = Field(default="ru", max_length=16)
    context_source: VisualRequestContextSource = VisualRequestContextSource.MANUAL


class VisualRequestUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    objective: str | None = Field(default=None, min_length=1, max_length=2000)
    scene_description: str | None = Field(default=None, min_length=1, max_length=4000)
    subject: str | None = Field(default=None, min_length=1, max_length=1000)
    style: str | None = Field(default=None, max_length=240)
    audience: str | None = Field(default=None, min_length=1, max_length=2000)
    mood: str | None = Field(default=None, max_length=240)
    aspect_ratio: VisualAspectRatio | None = None
    requested_variants: int | None = Field(default=None, ge=1, le=4)
    text_overlay: str | None = Field(default=None, max_length=500)
    must_include: str | None = Field(default=None, max_length=2000)
    must_avoid: str | None = Field(default=None, max_length=2000)
    related_text_asset_id: UUID | None = None
    reference_asset_ids: list[UUID] | None = Field(default=None, max_length=5)
    language: str | None = Field(default=None, max_length=16)


class VisualRequestRead(BaseModel):
    id: UUID
    owner_id: UUID
    project_id: UUID
    version: int
    context_source: VisualRequestContextSource
    title: str
    objective: str
    scene_description: str
    subject: str
    style: str
    audience: str
    mood: str
    aspect_ratio: VisualAspectRatio
    visual_format: VisualFormat
    requested_variants: int
    text_overlay: str
    must_include: str
    must_avoid: str
    related_text_asset_id: UUID | None = None
    reference_asset_ids: list[UUID] = Field(default_factory=list)
    language: str
    current_run_id: UUID | None = None
    approved_asset_id: UUID | None = None
    approved_version_number: int | None = None
    created_at: datetime
    updated_at: datetime


class VisualInputSnapshotRead(BaseModel):
    id: UUID
    visual_request_id: UUID
    visual_request_version: int
    payload: dict[str, Any]
    created_at: datetime


class VisualRunRead(BaseModel):
    id: UUID
    owner_id: UUID
    project_id: UUID
    visual_request_id: UUID
    visual_request_version: int
    snapshot_id: UUID
    status: VisualRunStatus
    attempt: int
    error_code: str | None = None
    error_message: str | None = None
    provider: str | None = None
    model: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class VisualDirectorCandidateRead(BaseModel):
    asset_id: UUID
    visual_run_id: UUID
    visual_request_id: UUID
    visual_request_version: int
    candidate_index: int
    title: str
    status: str
    current_version_number: int
    approved_version_number: int | None = None
    rejected: bool = False
    stale: bool = False
    mime_type: str = "image/png"
    width: int | None = None
    height: int | None = None
    checksum: str | None = None
    content_url: str | None = None
    safe_metadata: dict[str, Any] = Field(default_factory=dict)


class VisualDirectorGenerateRequest(BaseModel):
    idempotency_key: str | None = Field(default=None, max_length=128)


class VisualDirectorApproveRequest(BaseModel):
    note: str | None = Field(default=None, max_length=1000)
    confirm_text_overlay: bool = False


class VisualDirectorWorkspaceState(BaseModel):
    request: VisualRequestRead | None = None
    active_run: VisualRunRead | None = None
    candidates: list[VisualDirectorCandidateRead] = Field(default_factory=list)
    approved_asset_id: UUID | None = None
    approved_version_number: int | None = None
    next_action: str = "create_request"
    applied_skill_id: str | None = None
    applied_skill_version: str | None = None
    related_text_preview: str | None = None


# --- PRODUCT Skill Runtime (PROGRAM-CONTENT-01-SKILL-RUNTIME-01) ---


class ProductSkillType(StrEnum):
    INSTRUCTION = "instruction"
    TOOL = "tool"
    INTEGRATION = "integration"


class ProductSkillExternalAction(StrEnum):
    NONE = "none"
    READ = "read"
    WRITE = "write"


class ProductSkillInstallStatus(StrEnum):
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    READY = "ready"
    BLOCKED = "blocked"
    INSTALLED = "installed"
    INSTALLED_UNCONFIGURED = "installed_unconfigured"
    DISABLED = "disabled"
    SUPERSEDED = "superseded"


class ProductSkillRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class ProductSkillManifest(BaseModel):
    """Runtime SoT for Marketsynth product skills (ZIP/SKILL.md is import format only)."""

    skill_id: str = Field(min_length=3, max_length=128, pattern=r"^[a-z0-9]+(\.[a-z0-9_-]+)+$")
    name: str = Field(min_length=1, max_length=240)
    version: str = Field(min_length=1, max_length=32, pattern=r"^\d+\.\d+\.\d+$")
    description: str = Field(min_length=1, max_length=4000)
    type: ProductSkillType
    triggers: list[str] = Field(default_factory=list, max_length=32)
    accepted_input_types: list[str] = Field(default_factory=list)
    output_types: list[str] = Field(default_factory=list)
    instruction_entrypoint: str = Field(default="SKILL.md", max_length=256)
    allowed_tools: list[str] = Field(default_factory=list)
    allowed_network_hosts: list[str] = Field(default_factory=list)
    required_secret_aliases: list[str] = Field(default_factory=list)
    external_action: ProductSkillExternalAction = ProductSkillExternalAction.NONE
    human_approval_required: bool = False
    timeout_seconds: int = Field(default=60, ge=5, le=600)
    retry_max: int = Field(default=1, ge=0, le=5)
    enabled: bool = True
    provenance: str = Field(default="owner_curated", max_length=240)
    checksum_sha256: str | None = Field(default=None, min_length=64, max_length=64)


class ProductSkillIndexItem(BaseModel):
    skill_id: str
    name: str
    version: str
    description: str
    type: ProductSkillType
    triggers: list[str] = Field(default_factory=list)
    accepted_input_types: list[str] = Field(default_factory=list)
    output_types: list[str] = Field(default_factory=list)
    install_status: ProductSkillInstallStatus
    configured: bool
    enabled: bool
    required_secret_aliases: list[str] = Field(default_factory=list)
    permissions_summary: str = ""
    last_run_status: str | None = None
    last_run_at: datetime | None = None
    safe_error: str | None = None


class ProductSkillRunCreate(BaseModel):
    skill_id: str | None = Field(default=None, max_length=128)
    trigger: str | None = Field(default=None, max_length=128)
    input_type: str = Field(default="content_request", max_length=64)
    input_ref: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, max_length=128)
    explicit: bool = False


class ProductSkillRunRead(BaseModel):
    id: UUID
    owner_id: UUID
    project_id: UUID
    skill_id: str
    skill_version: str
    status: ProductSkillRunStatus
    selection_mode: str
    selection_reason: str
    input_type: str
    input_ref: dict[str, Any] = Field(default_factory=dict)
    result_ref: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    safe_error: str | None = None
    error_code: str | None = None
    idempotency_key: str | None = None
    correlation_id: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ProductSkillWorkspaceState(BaseModel):
    skills: list[ProductSkillIndexItem] = Field(default_factory=list)
    next_action: str = "browse"


# ── Project Command Center (PROJECT-COMMAND-CENTER-CANONICAL-01) ─────────────


class PccCapabilityStatus(StrEnum):
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    REQUIRES_INPUT = "requires_input"
    REQUIRES_APPROVAL = "requires_approval"
    COMPLETED = "completed"
    PAUSED = "paused"
    PLANNED = "planned"
    UNCONFIGURED = "unconfigured"
    BLOCKED = "blocked"
    COMING_SOON = "coming_soon"


class PccCapabilityCard(BaseModel):
    capability_id: str
    title: str
    value_proposition: str
    status: PccCapabilityStatus
    status_label: str
    last_result_summary: str | None = None
    last_changed_at: datetime | None = None
    primary_cta_label: str | None = None
    primary_cta_href: str | None = None
    secondary_cta_label: str | None = None
    secondary_cta_href: str | None = None
    cta_enabled: bool = True
    placeholder_note: str | None = None


class PccActivityItem(BaseModel):
    id: str
    title: str
    kind: str
    status: str
    status_label: str
    updated_at: datetime | None = None
    open_href: str | None = None


class PccRecentResult(BaseModel):
    id: str
    title: str
    kind: str
    status: str
    status_label: str
    version: int | None = None
    updated_at: datetime | None = None
    open_href: str | None = None


class PccAttentionItem(BaseModel):
    id: str
    title: str
    message: str
    severity: str = "info"
    cta_label: str | None = None
    cta_href: str | None = None


class PccSkillChip(BaseModel):
    skill_id: str
    name: str
    status: str
    status_label: str


class ProjectCommandCenterSummary(BaseModel):
    project_id: UUID
    project_name: str
    project_status: str
    project_summary: str | None = None
    last_changed_at: datetime | None = None
    capabilities: list[PccCapabilityCard] = Field(default_factory=list)
    active_work: list[PccActivityItem] = Field(default_factory=list)
    recent_results: list[PccRecentResult] = Field(default_factory=list)
    attention: list[PccAttentionItem] = Field(default_factory=list)
    skills: list[PccSkillChip] = Field(default_factory=list)


class PccGeneralMessage(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: datetime
    capability_id: str | None = None
    skill_id: str | None = None
    next_href: str | None = None
    next_action_label: str | None = None
    requires_paid: bool = False
    requires_external: bool = False
    requires_approval: bool = False
    status_notes: str | None = None


class PccGeneralConversation(BaseModel):
    session_id: UUID
    project_id: UUID
    messages: list[PccGeneralMessage] = Field(default_factory=list)


class PccGeneralSendRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class PccGeneralSendResponse(BaseModel):
    conversation: PccGeneralConversation
    assistant: PccGeneralMessage

