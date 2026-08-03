import { apiJson } from "@/lib/api/client";
import type {
  EvidenceCreateBody,
  EvidenceDto,
  EvidenceSummaryDto,
} from "@/lib/api/types/evidence";

export function createEvidence(
  projectId: string,
  investigationId: string,
  body: EvidenceCreateBody,
) {
  return apiJson<EvidenceDto>(
    `/projects/${projectId}/investigations/${investigationId}/evidence`,
    { method: "POST", body },
  );
}

export function fetchEvidenceList(projectId: string, investigationId: string) {
  return apiJson<EvidenceDto[]>(
    `/projects/${projectId}/investigations/${investigationId}/evidence`,
  );
}

export function fetchEvidenceSummary(projectId: string, investigationId: string) {
  return apiJson<EvidenceSummaryDto>(
    `/projects/${projectId}/investigations/${investigationId}/evidence/summary`,
  );
}

export function submitEvidenceReview(
  projectId: string,
  investigationId: string,
  evidenceId: string,
) {
  return apiJson<EvidenceDto>(
    `/projects/${projectId}/investigations/${investigationId}/evidence/${evidenceId}/submit-review`,
    { method: "POST" },
  );
}

export function acceptEvidence(
  projectId: string,
  investigationId: string,
  evidenceId: string,
) {
  return apiJson<EvidenceDto>(
    `/projects/${projectId}/investigations/${investigationId}/evidence/${evidenceId}/accept`,
    { method: "POST" },
  );
}
