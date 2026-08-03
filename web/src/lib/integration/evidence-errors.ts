/**
 * P0.4 — Evidence domain error normalization.
 */

import { ApiError } from "@/lib/api/errors";

export type EvidenceErrorKind =
  | "evidence_not_found"
  | "source_not_found"
  | "investigation_not_found"
  | "project_not_found"
  | "unauthorized"
  | "forbidden"
  | "cross_project_source"
  | "source_not_available"
  | "missing_source"
  | "non_atomic_claim"
  | "duplicate_evidence"
  | "fingerprint_conflict"
  | "immutable_evidence"
  | "invalid_transition"
  | "backend_unavailable"
  | "network_error"
  | "unsupported_automation"
  | "unknown_error";

export type EvidenceError = {
  kind: EvidenceErrorKind;
  message: string;
  status: number | null;
  actionHint: string;
};

const SAFE: Record<string, EvidenceErrorKind> = {
  missing_source: "missing_source",
  non_atomic_claim: "non_atomic_claim",
  duplicate_evidence: "duplicate_evidence",
  fingerprint_conflict: "fingerprint_conflict",
  immutable_evidence: "immutable_evidence",
  invalid_transition: "invalid_transition",
  cross_project_source: "cross_project_source",
  source_not_available: "source_not_available",
};

export function normalizeEvidenceError(err: unknown): EvidenceError {
  if (err instanceof ApiError) {
    if (err.status === 401) {
      return {
        kind: "unauthorized",
        message: "Требуется авторизация.",
        status: 401,
        actionHint: "Укажите API key.",
      };
    }
    if (err.status === 404) {
      return {
        kind: "evidence_not_found",
        message: "Evidence не найдено.",
        status: 404,
        actionHint: "Создайте Evidence явно — page load ничего не создаёт.",
      };
    }
    if (err.status >= 500) {
      return {
        kind: "backend_unavailable",
        message: "Backend недоступен.",
        status: err.status,
        actionHint: "Mock Evidence не подставляется в backend mode.",
      };
    }
    const body = err.body;
    const raw =
      (typeof body === "object" &&
        body &&
        "safe_message" in body &&
        String((body as { safe_message?: string }).safe_message)) ||
      (typeof body === "object" &&
        body &&
        "detail" in body &&
        String((body as { detail?: string }).detail)) ||
      "";
    const kind = SAFE[raw] ?? "unknown_error";
    return {
      kind,
      message:
        kind === "non_atomic_claim"
          ? "Нужно одно проверяемое утверждение без вердикта."
          : kind === "missing_source"
            ? "Для Evidence нужен Source (кроме missing)."
            : "Ошибка Evidence domain.",
      status: err.status,
      actionHint: "Исправьте claim/Source links и повторите.",
    };
  }
  return {
    kind: "unknown_error",
    message: "Неизвестная ошибка Evidence.",
    status: null,
    actionHint: "Обновите страницу.",
  };
}
