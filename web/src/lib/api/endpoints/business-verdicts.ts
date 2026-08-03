import { apiJson } from "@/lib/api/client";
import type {
  BackendEvidenceSnapshotDto,
  BackendVerdictDto,
} from "@/lib/api/types/business-verdicts";

export function fetchBusinessVerdicts(projectId: string) {
  return apiJson<BackendVerdictDto[]>(`/projects/${projectId}/business-verdicts`);
}

export function fetchLatestBusinessVerdict(projectId: string) {
  return apiJson<BackendVerdictDto>(`/projects/${projectId}/business-verdicts/latest`);
}

export function fetchBusinessVerdict(projectId: string, verdictId: string) {
  return apiJson<BackendVerdictDto>(
    `/projects/${projectId}/business-verdicts/${verdictId}`,
  );
}

export function fetchVerdictEvidenceSnapshot(projectId: string, verdictId: string) {
  return apiJson<BackendEvidenceSnapshotDto>(
    `/projects/${projectId}/business-verdicts/${verdictId}/evidence-snapshot`,
  );
}

export function buildDeterministicVerdictDraft(
  projectId: string,
  investigationId: string,
) {
  return apiJson<BackendVerdictDto>(
    `/projects/${projectId}/investigations/${investigationId}/business-verdicts/build-draft`,
    { method: "POST" },
  );
}

export function submitBusinessVerdictReview(projectId: string, verdictId: string) {
  return apiJson<BackendVerdictDto>(
    `/projects/${projectId}/business-verdicts/${verdictId}/submit-review`,
    { method: "POST" },
  );
}

export function approveBusinessVerdict(projectId: string, verdictId: string) {
  return apiJson<BackendVerdictDto>(
    `/projects/${projectId}/business-verdicts/${verdictId}/approve`,
    { method: "POST" },
  );
}

export function rejectBusinessVerdict(
  projectId: string,
  verdictId: string,
  rejectionReason: string,
) {
  return apiJson<BackendVerdictDto>(
    `/projects/${projectId}/business-verdicts/${verdictId}/reject`,
    { method: "POST", body: { rejection_reason: rejectionReason } },
  );
}
