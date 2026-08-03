import { apiJson } from "@/lib/api/client";
import type {
  BetaFeedbackCreateBody,
  BetaFeedbackReport,
  BetaQaExport,
} from "@/lib/api/types/beta-feedback";

export function createBetaFeedback(body: BetaFeedbackCreateBody) {
  return apiJson<BetaFeedbackReport>("/me/beta-feedback", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchMyBetaFeedback() {
  return apiJson<BetaFeedbackReport[]>("/me/beta-feedback");
}

export function fetchBetaAdminFeedback() {
  return apiJson<BetaFeedbackReport[]>("/me/beta-admin/feedback");
}

export function triageBetaAdminFeedback(reportId: string) {
  return apiJson<BetaFeedbackReport>(`/me/beta-admin/feedback/${reportId}/triage`, {
    method: "POST",
  });
}

export function resolveBetaAdminFeedback(reportId: string) {
  return apiJson<BetaFeedbackReport>(`/me/beta-admin/feedback/${reportId}/resolve`, {
    method: "POST",
  });
}

export function fetchBetaQaExport() {
  return apiJson<BetaQaExport>("/me/beta-admin/qa-export");
}
