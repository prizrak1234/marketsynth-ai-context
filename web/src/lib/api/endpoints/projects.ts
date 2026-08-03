import { apiJson } from "@/lib/api/client";
import type { OperationalMetricsResponse } from "@/lib/api/types/operational-metrics";
import type { ReviewQueueResponse } from "@/lib/api/types/review-queue";

export type Project = {
  id: string;
  owner_id: string;
  name: string;
  description: string | null;
  config?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ProjectCreateRequest = {
  name: string;
  description?: string | null;
};

export type ProjectUpdateRequest = {
  name?: string;
  description?: string | null;
  config?: Record<string, unknown>;
};

export function fetchProjects() {
  return apiJson<Project[]>("/projects");
}

export function fetchProject(projectId: string) {
  return apiJson<Project>(`/projects/${projectId}`);
}

export function createProject(body: ProjectCreateRequest) {
  return apiJson<Project>("/projects", {
    method: "POST",
    body,
  });
}

export function updateProject(projectId: string, body: ProjectUpdateRequest) {
  return apiJson<Project>(`/projects/${projectId}`, {
    method: "PATCH",
    body,
  });
}

export function fetchProjectOperationalMetrics(projectId: string) {
  return apiJson<OperationalMetricsResponse>(
    `/projects/${projectId}/operational-metrics`,
  );
}

export function fetchProjectReviewQueue(projectId: string) {
  return apiJson<ReviewQueueResponse>(`/projects/${projectId}/review-queue`);
}
