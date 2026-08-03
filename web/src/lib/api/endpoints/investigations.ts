import { apiJson } from "@/lib/api/client";
import type {
  InvestigationCreateBody,
  InvestigationDto,
  InvestigationLifecycleStatus,
  InvestigationStageId,
  InvestigationStageUpdateBody,
} from "@/lib/api/types/investigations";

export function createInvestigation(projectId: string, body: InvestigationCreateBody) {
  return apiJson<InvestigationDto>(`/projects/${projectId}/investigations`, {
    method: "POST",
    body,
  });
}

export function fetchInvestigations(
  projectId: string,
  params?: { status?: InvestigationLifecycleStatus; limit?: number; offset?: number },
) {
  const search = new URLSearchParams();
  if (params?.status) search.set("status", params.status);
  if (params?.limit !== undefined) search.set("limit", String(params.limit));
  if (params?.offset !== undefined) search.set("offset", String(params.offset));
  const q = search.toString();
  return apiJson<InvestigationDto[]>(
    `/projects/${projectId}/investigations${q ? `?${q}` : ""}`,
  );
}

export function fetchLatestInvestigation(projectId: string) {
  return apiJson<InvestigationDto>(`/projects/${projectId}/investigations/latest`);
}

export function fetchInvestigation(projectId: string, investigationId: string) {
  return apiJson<InvestigationDto>(
    `/projects/${projectId}/investigations/${investigationId}`,
  );
}

export function startInvestigation(projectId: string, investigationId: string) {
  return apiJson<InvestigationDto>(
    `/projects/${projectId}/investigations/${investigationId}/start`,
    { method: "POST" },
  );
}

export function blockInvestigation(
  projectId: string,
  investigationId: string,
  reason?: string,
) {
  return apiJson<InvestigationDto>(
    `/projects/${projectId}/investigations/${investigationId}/block`,
    { method: "POST", body: { reason: reason ?? null } },
  );
}

export function resumeInvestigation(projectId: string, investigationId: string) {
  return apiJson<InvestigationDto>(
    `/projects/${projectId}/investigations/${investigationId}/resume`,
    { method: "POST" },
  );
}

export function submitInvestigationReview(projectId: string, investigationId: string) {
  return apiJson<InvestigationDto>(
    `/projects/${projectId}/investigations/${investigationId}/submit-review`,
    { method: "POST" },
  );
}

export function completeInvestigation(projectId: string, investigationId: string) {
  return apiJson<InvestigationDto>(
    `/projects/${projectId}/investigations/${investigationId}/complete`,
    { method: "POST" },
  );
}

export function cancelInvestigation(projectId: string, investigationId: string) {
  return apiJson<InvestigationDto>(
    `/projects/${projectId}/investigations/${investigationId}/cancel`,
    { method: "POST" },
  );
}

export function supersedeInvestigation(
  projectId: string,
  investigationId: string,
  body: InvestigationCreateBody,
) {
  return apiJson<InvestigationDto>(
    `/projects/${projectId}/investigations/${investigationId}/supersede`,
    { method: "POST", body },
  );
}

export function updateInvestigationStage(
  projectId: string,
  investigationId: string,
  stage: InvestigationStageId,
  body: InvestigationStageUpdateBody,
) {
  return apiJson<InvestigationDto>(
    `/projects/${projectId}/investigations/${investigationId}/stages/${stage}`,
    { method: "PATCH", body },
  );
}
