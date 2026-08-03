import { apiJson } from "@/lib/api/client";
import type {
  InvestigationSourceItemDto,
  InvestigationSourceLinkDto,
  InvestigationSourceLinkStatus,
  SourceCreateBody,
  SourceDto,
  SourceFreshnessStatus,
  SourceProvenanceType,
  SourceReliabilityLevel,
  SourceStatus,
  SourceType,
} from "@/lib/api/types/sources";

export function registerSource(projectId: string, body: SourceCreateBody) {
  return apiJson<SourceDto>(`/projects/${projectId}/sources`, {
    method: "POST",
    body,
  });
}

export function fetchProjectSources(
  projectId: string,
  params?: {
    source_type?: SourceType;
    provenance_type?: SourceProvenanceType;
    freshness_status?: SourceFreshnessStatus;
    reliability_level?: SourceReliabilityLevel;
    status?: SourceStatus;
    limit?: number;
  },
) {
  const search = new URLSearchParams();
  if (params?.source_type) search.set("source_type", params.source_type);
  if (params?.provenance_type) search.set("provenance_type", params.provenance_type);
  if (params?.freshness_status) search.set("freshness_status", params.freshness_status);
  if (params?.reliability_level)
    search.set("reliability_level", params.reliability_level);
  if (params?.status) search.set("status", params.status);
  if (params?.limit !== undefined) search.set("limit", String(params.limit));
  const q = search.toString();
  return apiJson<SourceDto[]>(`/projects/${projectId}/sources${q ? `?${q}` : ""}`);
}

export function fetchSource(projectId: string, sourceId: string) {
  return apiJson<SourceDto>(`/projects/${projectId}/sources/${sourceId}`);
}

export function supersedeSource(
  projectId: string,
  sourceId: string,
  body: SourceCreateBody,
) {
  return apiJson<SourceDto>(`/projects/${projectId}/sources/${sourceId}/supersede`, {
    method: "POST",
    body,
  });
}

export function attachSourceToInvestigation(
  projectId: string,
  investigationId: string,
  sourceId: string,
  body?: { purpose?: string; status?: InvestigationSourceLinkStatus },
) {
  return apiJson<InvestigationSourceLinkDto>(
    `/projects/${projectId}/investigations/${investigationId}/sources/${sourceId}`,
    { method: "POST", body },
  );
}

export function fetchInvestigationSources(
  projectId: string,
  investigationId: string,
  params?: { status?: InvestigationSourceLinkStatus; limit?: number },
) {
  const search = new URLSearchParams();
  if (params?.status) search.set("status", params.status);
  if (params?.limit !== undefined) search.set("limit", String(params.limit));
  const q = search.toString();
  return apiJson<InvestigationSourceItemDto[]>(
    `/projects/${projectId}/investigations/${investigationId}/sources${q ? `?${q}` : ""}`,
  );
}
