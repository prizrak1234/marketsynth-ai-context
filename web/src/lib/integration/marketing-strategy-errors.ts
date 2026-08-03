/** P0.6 marketing strategy errors. */

import { ApiError } from "@/lib/api/errors";
import {
  normalizeStrategyError,
  type StrategyError,
} from "@/lib/integration/strategy-errors";

export function normalizeMarketingStrategyError(err: unknown): StrategyError {
  if (err instanceof ApiError) {
    const detail = String(
      (err.body as { safe_message?: string; detail?: string } | null)?.safe_message ||
        (err.body as { detail?: string } | null)?.detail ||
        err.message ||
        "",
    );
    if (detail.includes("verdict_type_not_eligible") || detail.includes("verdict_not_approved")) {
      return {
        kind: "invalid_strategy_eligibility",
        message: "Strategy blocked by BusinessVerdict eligibility.",
        status: err.status,
        actionHint: "Требуется approved GO или CONDITIONAL_GO.",
      };
    }
    if (detail.includes("immutable_strategy")) {
      return {
        kind: "unsupported_mapping",
        message: "Approved MarketingStrategy is immutable.",
        status: err.status,
        actionHint: "Создайте новую версию через supersede.",
      };
    }
  }
  return normalizeStrategyError(err);
}
