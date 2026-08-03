/**
 * Product Alpha Phase A2 — Project intake draft types (frontend-only).
 * Not synced to backend contracts.
 */

export type IntakeStepId =
  | "basics"
  | "product"
  | "market"
  | "audience"
  | "economics"
  | "materials"
  | "review";

export type BusinessType =
  | "local_business"
  | "online_service"
  | "saas"
  | "ecommerce"
  | "marketplace"
  | "franchise"
  | "professional_services"
  | "mobile_application"
  | "media_content"
  | "other";

export type ProjectStage =
  | "idea_only"
  | "validating_demand"
  | "preparing_launch"
  | "already_operating"
  | "scaling"
  | "relaunching";

export type InterfaceLanguage = "ru" | "en";

export type CustomerModel = "b2b" | "b2c" | "b2g" | "mixed" | "unknown";

export type MoneyMode = "exact" | "range" | "unknown";

export type MoneyValue = {
  mode: MoneyMode;
  exact?: string;
  min?: string;
  max?: string;
};

export type ProjectBasics = {
  name: string;
  ideaDescription: string;
  businessType: BusinessType | "";
  projectStage: ProjectStage | "";
  geography: string;
  interfaceLanguage: InterfaceLanguage;
};

export type ProductDraft = {
  whatIsSold: string;
  primaryProblem: string;
  valueProposition: string;
  price: MoneyValue;
  deliveryModel: string;
  differentiators: string;
  knownLimitations: string;
  /** Explicit unknowns — not silent blanks */
  priceUnknown: boolean;
  deliveryUnknown: boolean;
};

export type MarketDraft = {
  targetMarket: string;
  geography: string;
  knownCompetitors: string;
  competitorUrls: string;
  marketAssumptions: string;
  demandEvidence: string;
  seasonality: string;
  restrictions: string;
  competitorsUnknown: boolean;
  demandUnavailable: boolean;
  marketSizeUnknown: boolean;
};

export type AudienceSegment = {
  id: string;
  label: string;
  notes: string;
};

export type AudienceDraft = {
  customerModel: CustomerModel;
  segments: AudienceSegment[];
  decisionMaker: string;
  buyerUserDistinction: string;
  customerLocation: string;
  expectedPains: string;
  expectedObjections: string;
  currentResearch: string;
};

export type EconomicsDraft = {
  launchBudget: MoneyValue;
  monthlyMarketingBudget: MoneyValue;
  targetRevenue: MoneyValue;
  paybackPeriod: string;
  paybackUnknown: boolean;
  averageOrderValue: MoneyValue;
  grossMargin: string;
  grossMarginUnknown: boolean;
  teamSize: string;
  teamSizeUnknown: boolean;
  internalResources: string;
  launchDeadline: string;
  launchDeadlineUnknown: boolean;
  criticalConstraints: string;
};

export type MockMaterialKind =
  | "document"
  | "spreadsheet"
  | "presentation"
  | "website_url"
  | "social_profile"
  | "research"
  | "customer_interview"
  | "analytics_export"
  | "competitor_list";

export type MockMaterial = {
  id: string;
  kind: MockMaterialKind;
  label: string;
  note?: string;
};

export type MaterialsDraft = {
  websiteUrl: string;
  socialProfiles: string;
  items: MockMaterial[];
};

export type IntakeReadinessStatus =
  | "ready"
  | "conditionally_ready"
  | "insufficient_data";

export type IntakeReadinessResult = {
  status: IntakeReadinessStatus;
  completedSections: string[];
  missingCritical: string[];
  missingOptional: string[];
  assumptions: string[];
  contradictions: string[];
  recommendedAdditions: string[];
};

export type ProjectIntakeDraft = {
  id: string;
  projectBasics: ProjectBasics;
  product: ProductDraft;
  market: MarketDraft;
  audience: AudienceDraft;
  economics: EconomicsDraft;
  materials: MaterialsDraft;
  assumptions: string[];
  missingData: string[];
  readiness: IntakeReadinessResult | null;
  currentStep: IntakeStepId;
  updatedAt: string;
  savedAsDraftAt?: string;
  /** I2 — link to existing backend Project (frontend integration only) */
  backendSync?: IntakeBackendSyncMeta | null;
  /** P0.1 — link to durable ProjectBrief */
  briefSync?: IntakeBriefSyncMeta | null;
};

/** Frontend sync states — not backend Project.status */
export type IntakeBackendSyncState =
  | "local_only"
  | "creating"
  | "synced"
  | "partially_synced"
  | "update_pending"
  | "conflict"
  | "failed";

export type IntakeBackendSyncMeta = {
  backendProjectId: string | null;
  backendSyncState: IntakeBackendSyncState;
  backendSyncedAt: string | null;
  backendUpdatedAt: string | null;
  lastSyncError: string | null;
  submissionFingerprint: string | null;
  localDraftVersion: string;
};

export type IntakeBriefSyncState =
  | "not_linked"
  | "draft_saved"
  | "submitted"
  | "stale"
  | "conflict"
  | "failed";

export type IntakeBriefSyncMeta = {
  backendBriefId: string | null;
  backendBriefVersion: number | null;
  backendBriefStatus: string | null;
  backendBriefFingerprint: string | null;
  briefSyncState: IntakeBriefSyncState;
  lastBriefSyncAt: string | null;
  lastBriefSyncError: string | null;
};

export type MockInvestigationProject = {
  id: string;
  name: string;
  status: "investigation_queued";
  statusLabel: string;
  createdAt: string;
  readiness: IntakeReadinessResult;
  draftSnapshot: ProjectIntakeDraft;
};
