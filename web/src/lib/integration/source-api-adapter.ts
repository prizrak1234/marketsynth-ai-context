/**
 * P0.3 — Backend Source → Product Alpha Investigation Source view model.
 * No Evidence inference. No content/summary/analysis fields.
 */

import type { SourceDto } from "@/lib/api/types/sources";
import type { DataOrigin } from "@/lib/integration/contracts";
import type {
  FreshnessState,
  InvestigationSource,
  ReliabilityLevel,
  SourceStatus,
  SourceType,
} from "@/lib/investigation/types";

const ALPHA_TYPES = new Set<string>([
  "website",
  "competitor_website",
  "market_report",
  "public_dataset",
  "analytics_export",
  "uploaded_document",
  "interview",
  "user_statement",
  "internal_calculation",
]);

export function mapSourceTypeToAlpha(type: string): SourceType {
  if (ALPHA_TYPES.has(type)) return type as SourceType;
  if (type === "customer_interview") return "interview";
  if (type === "spreadsheet" || type === "presentation" || type === "internal_document")
    return "uploaded_document";
  if (type === "crm_export" || type === "api_reference") return "analytics_export";
  return "website";
}

export function mapBackendSourceToView(
  dto: SourceDto,
  origin: DataOrigin = "backend",
): InvestigationSource & {
  originLabel: DataOrigin;
  provenanceType: string;
  version: number;
  fingerprint: string;
  noEvidence: true;
} {
  return {
    id: dto.id,
    title: dto.title,
    sourceType: mapSourceTypeToAlpha(dto.source_type),
    origin: `${dto.provenance_type} · ${dto.origin || dto.domain || "provenance"}`,
    mockUrl: dto.url ?? undefined,
    accessedAtLabel: dto.accessed_at ?? dto.captured_at ?? "—",
    freshness: dto.freshness_status as FreshnessState,
    reliability: dto.reliability_level as ReliabilityLevel,
    relevance: "medium",
    status: (dto.status === "registered" || dto.status === "available"
      ? "available"
      : dto.status === "rejected"
        ? "rejected"
        : dto.status === "unavailable"
          ? "unavailable"
          : "reviewed") as SourceStatus,
    notes: `v${dto.version} · ${dto.fingerprint.slice(0, 12)}… · analysis deferred to Evidence (P0.4)`,
    originLabel: origin,
    provenanceType: dto.provenance_type,
    version: dto.version,
    fingerprint: dto.fingerprint,
    noEvidence: true,
  };
}

export function sourceCreateBodyFromLocalPreview(local: {
  title: string;
  sourceType: SourceType;
  mockUrl?: string;
  notes?: string;
}): {
  source_type: SourceType;
  provenance_type: "user_provided";
  title: string;
  origin: string;
  url: string | null;
  capabilities: ["text"];
  reliability_default: "unverified";
} {
  return {
    source_type: local.sourceType,
    provenance_type: "user_provided",
    title: local.title,
    origin: "local_preview_registration",
    url: local.mockUrl ?? null,
    capabilities: ["text"],
    reliability_default: "unverified",
  };
}

export function createsEvidenceFromSource(): false {
  return false;
}

export function fetchesUrlOnRegister(): false {
  return false;
}
