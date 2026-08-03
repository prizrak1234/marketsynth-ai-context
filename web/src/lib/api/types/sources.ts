/** Commercial MVP P0.3 — Source API types */

export type SourceType =
  | "website"
  | "competitor_website"
  | "market_report"
  | "public_dataset"
  | "analytics_export"
  | "uploaded_document"
  | "spreadsheet"
  | "presentation"
  | "interview"
  | "user_statement"
  | "customer_interview"
  | "crm_export"
  | "api_reference"
  | "internal_calculation"
  | "internal_document"
  | "other";

export type SourceProvenanceType =
  | "official"
  | "primary"
  | "secondary"
  | "user_provided"
  | "uploaded"
  | "internal"
  | "generated"
  | "unknown";

export type SourceCapability =
  | "text"
  | "table"
  | "image"
  | "audio"
  | "video"
  | "structured_data"
  | "webpage"
  | "pdf"
  | "spreadsheet"
  | "presentation"
  | "api_payload";

export type SourceFreshnessStatus = "current" | "acceptable" | "outdated" | "unknown";
export type SourceReliabilityLevel = "high" | "medium" | "low" | "unverified";
export type SourceStatus =
  | "registered"
  | "available"
  | "unavailable"
  | "rejected"
  | "superseded"
  | "archived";

export type InvestigationSourceLinkStatus =
  | "proposed"
  | "accepted"
  | "rejected"
  | "excluded";

export type SourceDto = {
  id: string;
  owner_id: string;
  project_id: string;
  source_type: SourceType;
  provenance_type: SourceProvenanceType;
  title: string;
  origin: string;
  url: string | null;
  domain: string | null;
  publisher: string | null;
  language: string | null;
  country: string | null;
  published_at: string | null;
  captured_at: string | null;
  accessed_at: string | null;
  freshness_status: SourceFreshnessStatus;
  reliability_level: SourceReliabilityLevel;
  status: SourceStatus;
  fingerprint: string;
  content_hash: string | null;
  etag: string | null;
  version: number;
  supersedes_source_id: string | null;
  license_type: string | null;
  capabilities: SourceCapability[];
  reusable_within_project: boolean;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type SourceCreateBody = {
  source_type: SourceType;
  provenance_type?: SourceProvenanceType;
  title: string;
  origin?: string;
  url?: string | null;
  domain?: string | null;
  publisher?: string | null;
  language?: string | null;
  country?: string | null;
  published_at?: string | null;
  captured_at?: string | null;
  accessed_at?: string | null;
  freshness_status?: SourceFreshnessStatus | null;
  content_hash?: string | null;
  etag?: string | null;
  license_type?: string | null;
  capabilities?: SourceCapability[];
  metadata?: Record<string, unknown>;
  attach_to_investigation_id?: string | null;
  link_purpose?: string | null;
};

export type InvestigationSourceLinkDto = {
  id: string;
  owner_id: string;
  project_id: string;
  investigation_id: string;
  source_id: string;
  purpose: string | null;
  investigation_area: string | null;
  notes: string | null;
  status: InvestigationSourceLinkStatus;
  added_by: string;
  created_at: string;
  updated_at: string;
};

export type InvestigationSourceItemDto = {
  link: InvestigationSourceLinkDto;
  source: SourceDto;
};
