"""SQLModel tables РІР‚вЂќ import all models so metadata is complete for Alembic."""

from sqlmodel import SQLModel

from app.db.models.agent import AgentTable
from app.db.models.agent_chat import AgentChatMessageTable, AgentChatSessionTable
from app.db.models.chat_audit_event import ChatAuditEventTable
from app.db.models.agent_run import AgentRunTable
from app.db.models.api_key import ApiKeyTable
from app.db.models.beta_feedback_report import BetaFeedbackReportTable
from app.db.models.campaign import CampaignTable
from app.db.models.campaign_brief import CampaignBriefTable
from app.db.models.campaign_plan_drafts import CampaignPlanDraftTable
from app.db.models.event_outbox import EventOutboxTable
from app.db.models.llm import LLMRequestTable, LLMResponseTable
from app.db.models.marketing import (
    ContentAssetTable,
    ContentAssetVersionTable,
    MarketingBriefTable,
    PublicationPackageTable,
)
from app.db.models.media import (
    MediaAssetTable,
    MediaAssetVersionTable,
    MediaBriefTable,
    MediaGenerationJobTable,
)
from app.db.models.marketing_plan import MarketingPlanTable, MarketingPlanVersionTable
from app.db.models.marketing_plan_execution_run import MarketingPlanExecutionRunTable
from app.db.models.marketing_specialist_output import (
    MarketingSpecialistOutputTable,
    MarketingSpecialistOutputVersionTable,
)
from app.db.models.marketing_campaigns import MarketingCampaignTable
from app.db.models.marketing_funnels import (
    FunnelStepAssetLinkTable,
    MarketingFunnelStepTable,
    MarketingFunnelTable,
)
from app.db.models.campaign_workflow_run import CampaignWorkflowRunTable
from app.db.models.marketing_skill_run import MarketingSkillRunTable
from app.db.models.marketing_tool_call import MarketingToolCallTable
from app.db.models.project import ProjectTable
from app.db.models.project_brief import ProjectBriefTable
from app.db.models.investigation import InvestigationTable
from app.db.models.source import InvestigationSourceLinkTable, SourceTable
from app.db.models.evidence import EvidenceSourceLinkTable, InvestigationEvidenceTable
from app.db.models.business_verdict import (
    BusinessVerdictEvidenceLinkTable,
    BusinessVerdictEvidenceSnapshotTable,
    BusinessVerdictTable,
)
from app.db.models.marketing_strategy import MarketingStrategyTable
from app.db.models.implementation_plan import ImplementationPlanTable
from app.db.models.implementation_marketing_plan_handoff import (
    ImplementationMarketingPlanHandoffTable,
)
from app.db.models.project_webhook import ProjectWebhookTable
from app.db.models.scenario_wizard_run import ScenarioWizardRunTable
from app.db.models.publication_package_job import PublicationPackageJobTable
from app.db.models.publishing import PublicationJobTable, PublishingChannelTable
from app.db.models.publishing_audit_event import PublishingAuditEventTable
from app.db.models.task import TaskTable
from app.db.models.tool_execution_log import ToolExecutionLogTable
from app.db.models.user import UserTable
from app.db.models.browser_session import BrowserSessionTable
from app.db.models.pilot_invite import PilotInviteTable
from app.db.models.password_reset_token import PasswordResetTokenTable
from app.db.models.user_request import UserRequestTable
from app.db.models.knowledge_item import KnowledgeItemTable, KnowledgeSnapshotTable
from app.db.models.knowledge_governance import (
    BenchmarkCaseTable,
    BenchmarkDatasetTable,
    CitationRecordTable,
    KnowledgeAuditEventTable,
    KnowledgeFreshnessCheckTable,
    KnowledgeObjectTable,
    KnowledgeOwnershipTable,
    KnowledgeReviewTable,
    KnowledgeVersionTable,
    SemanticChunkTable,
)
from app.db.models.generated_visual_asset import GeneratedVisualAssetTable
from app.db.models.video_clip_request import VideoClipRequestTable
from app.db.models.reference_visual import ReferenceSetTable, ReferenceVisualAssetTable
from app.db.models.identity_generation import (
    IdentityQualificationRunTable,
    IdentityReferenceManifestTable,
)
from app.db.models.commercial_research_run import CommercialResearchRunTable
from app.db.models.content_director import (
    ContentInputSnapshotTable,
    ContentRequestTable,
    ContentRunCandidateTable,
    ContentRunTable,
)
from app.db.models.visual_director import (
    ImageAssetTable,
    ImageAssetVersionTable,
    VisualInputSnapshotTable,
    VisualRequestTable,
    VisualRunCandidateTable,
    VisualRunTable,
)
from app.db.models.product_skills import (
    ProductSkillInstallationTable,
    ProductSkillRunTable,
)
from app.db.models.analysis_context import AnalysisContextTable
from app.db.models.business_idea_validation_run import BusinessIdeaValidationRunTable
from app.db.models.biv_e2e_deterministic_fixture import BivE2eDeterministicFixtureTable
from app.db.models.biv_fetch_ledger import BivFetchLedgerTable
from app.db.models.commercial_next_step_decision import CommercialNextStepDecisionTable
from app.db.models.launch_pack_request import LaunchPackRequestTable
from app.db.models.commercial_upstream_snapshot import CommercialUpstreamSnapshotTable
from app.db.models.offer_artifact import (
    OfferArtifactTable,
    OfferArtifactVersionTable,
    OfferReviewEventTable,
)
from app.db.models.mcp_tool_call_audit import McpToolCallAuditTable
from app.db.models.webhook_delivery_log import WebhookDeliveryLogTable

__all__ = [
    "AgentChatMessageTable",
    "AgentChatSessionTable",
    "ChatAuditEventTable",
    "AgentRunTable",
    "AgentTable",
    "EventOutboxTable",
    "ApiKeyTable",
    "BetaFeedbackReportTable",
    "LLMRequestTable",
    "LLMResponseTable",
    "ContentAssetTable",
    "ContentAssetVersionTable",
    "PublicationPackageTable",
    "MediaBriefTable",
    "MediaAssetTable",
    "MediaAssetVersionTable",
    "MediaGenerationJobTable",
    "FunnelStepAssetLinkTable",
    "CampaignPlanDraftTable",
    "CampaignTable",
    "CampaignBriefTable",
    "CampaignWorkflowRunTable",
    "MarketingCampaignTable",
    "MarketingPlanTable",
    "MarketingPlanVersionTable",
    "MarketingPlanExecutionRunTable",
    "MarketingSpecialistOutputTable",
    "MarketingSpecialistOutputVersionTable",
    "MarketingBriefTable",
    "MarketingFunnelStepTable",
    "MarketingFunnelTable",
    "MarketingSkillRunTable",
    "MarketingToolCallTable",
    "MemoryItemTable",
    "ProjectTable",
    "ProjectBriefTable",
    "InvestigationTable",
    "SourceTable",
    "InvestigationSourceLinkTable",
    "InvestigationEvidenceTable",
    "EvidenceSourceLinkTable",
    "BusinessVerdictTable",
    "BusinessVerdictEvidenceSnapshotTable",
    "BusinessVerdictEvidenceLinkTable",
    "MarketingStrategyTable",
    "ImplementationPlanTable",
    "ImplementationMarketingPlanHandoffTable",
    "ProjectWebhookTable",
    "PublicationDeliveryLogTable",
    "PublicationJobTable",
    "PublicationPackageJobTable",
    "ScenarioWizardRunTable",
    "PublishingAuditEventTable",
    "PublishingChannelTable",
    "SQLModel",
    "TaskTable",
    "ToolExecutionLogTable",
    "WebhookDeliveryLogTable",
    "UserTable",
    "BrowserSessionTable",
    "PilotInviteTable",
    "PasswordResetTokenTable",
    "UserRequestTable",
    "KnowledgeItemTable",
    "KnowledgeSnapshotTable",
    "KnowledgeObjectTable",
    "KnowledgeVersionTable",
    "SemanticChunkTable",
    "KnowledgeReviewTable",
    "KnowledgeOwnershipTable",
    "BenchmarkDatasetTable",
    "BenchmarkCaseTable",
    "CitationRecordTable",
    "KnowledgeFreshnessCheckTable",
    "KnowledgeAuditEventTable",
    "GeneratedVisualAssetTable",
    "VideoClipRequestTable",
    "ReferenceVisualAssetTable",
    "ReferenceSetTable",
    "IdentityReferenceManifestTable",
    "IdentityQualificationRunTable",
    "CommercialResearchRunTable",
    "ContentRequestTable",
    "ContentInputSnapshotTable",
    "ContentRunTable",
    "ContentRunCandidateTable",
    "VisualRequestTable",
    "VisualInputSnapshotTable",
    "VisualRunTable",
    "VisualRunCandidateTable",
    "ImageAssetTable",
    "ImageAssetVersionTable",
    "ProductSkillInstallationTable",
    "ProductSkillRunTable",
    "AnalysisContextTable",
    "BusinessIdeaValidationRunTable",
    "BivE2eDeterministicFixtureTable",
    "BivFetchLedgerTable",
    "CommercialNextStepDecisionTable",
    "LaunchPackRequestTable",
    "CommercialUpstreamSnapshotTable",
    "OfferArtifactTable",
    "OfferArtifactVersionTable",
    "OfferReviewEventTable",
    "McpToolCallAuditTable",
]
