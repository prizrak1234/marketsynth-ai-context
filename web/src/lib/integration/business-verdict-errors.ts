/**
 * P0.5 — BusinessVerdict error normalization.
 */

import { ApiError } from "@/lib/api/errors";
import {
  normalizeVerdictError,
  type VerdictError,
} from "@/lib/integration/verdict-errors";

export type BusinessVerdictErrorKind =
  | VerdictError["kind"]
  | "verdict_not_found"
  | "evidence_snapshot_invalid"
  | "immutable_verdict"
  | "verdict_type_not_allowed"
  | "invalid_transition"
  | "strategy_not_allowed"
  | "local_backend_conflict";

export function normalizeBusinessVerdictError(err: unknown): VerdictError {
  if (err instanceof ApiError) {
    const detail = String(
      (err.body as { safe_message?: string; detail?: string } | null)?.safe_message ||
        (err.body as { detail?: string } | null)?.detail ||
        err.message ||
        "",
    );
    if (detail.includes("immutable_verdict")) {
      return {
        kind: "invalid_transition",
        message: "Утверждённый BusinessVerdict неизменяем.",
        status: err.status,
        actionHint: "Создайте новую версию через supersede.",
      };
    }
    if (detail.includes("verdict_type_not_allowed")) {
      return {
        kind: "insufficient_evidence",
        message: "Тип вердикта не допускается при текущей readiness/Evidence базе.",
        status: err.status,
        actionHint: "Проверьте Evidence Summary — readiness ≠ вердикт.",
      };
    }
  }
  return normalizeVerdictError(err);
}
