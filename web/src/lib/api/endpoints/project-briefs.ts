import { apiJson } from "@/lib/api/client";
import type {
  ProjectBriefCreateBody,
  ProjectBriefDto,
  ProjectBriefStatus,
} from "@/lib/api/types/project-briefs";

export function createProjectBrief(projectId: string, body: ProjectBriefCreateBody) {
  return apiJson<ProjectBriefDto>(`/projects/${projectId}/briefs`, {
    method: "POST",
    body,
  });
}

export function fetchProjectBriefs(
  projectId: string,
  params?: { status?: ProjectBriefStatus; limit?: number },
) {
  const search = new URLSearchParams();
  if (params?.status) search.set("status", params.status);
  if (params?.limit !== undefined) search.set("limit", String(params.limit));
  const q = search.toString();
  return apiJson<ProjectBriefDto[]>(
    `/projects/${projectId}/briefs${q ? `?${q}` : ""}`,
  );
}

export function fetchLatestProjectBrief(projectId: string) {
  return apiJson<ProjectBriefDto>(`/projects/${projectId}/briefs/latest`);
}

export function fetchProjectBrief(projectId: string, briefId: string) {
  return apiJson<ProjectBriefDto>(`/projects/${projectId}/briefs/${briefId}`);
}

export function updateProjectBrief(
  projectId: string,
  briefId: string,
  body: Partial<ProjectBriefCreateBody>,
) {
  return apiJson<ProjectBriefDto>(`/projects/${projectId}/briefs/${briefId}`, {
    method: "PATCH",
    body,
  });
}

export function submitProjectBrief(projectId: string, briefId: string) {
  return apiJson<ProjectBriefDto>(`/projects/${projectId}/briefs/${briefId}/submit`, {
    method: "POST",
  });
}

export function supersedeProjectBrief(
  projectId: string,
  briefId: string,
  body?: ProjectBriefCreateBody,
) {
  return apiJson<ProjectBriefDto>(
    `/projects/${projectId}/briefs/${briefId}/supersede`,
    { method: "POST", body },
  );
}
