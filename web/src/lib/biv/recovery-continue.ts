import type { AnalysisContextRecord } from "@/lib/api/endpoints/analysis-contexts";
import { ApiError } from "@/lib/api/client";

export type RecoveryContinuePlan =
  | { action: "open_incomplete_form"; missingFields: string[] }
  | { action: "confirm" };

/** Decide recovery «Continue» without bypassing backend specificity gate. */
export function planRecoveryContinue(context: AnalysisContextRecord): RecoveryContinuePlan {
  if (context.missing_fields.length > 0) {
    return { action: "open_incomplete_form", missingFields: [...context.missing_fields] };
  }
  return { action: "confirm" };
}

export function readCommercialErrorCode(err: unknown): string | null {
  if (!(err instanceof ApiError)) {
    return null;
  }
  const body = err.body as { error_code?: string; detail?: string } | undefined;
  if (body?.error_code) {
    return body.error_code;
  }
  if (typeof err.message === "string" && err.message) {
    return err.message;
  }
  return null;
}

export function shouldOpenFormAfterConfirmError(err: unknown): boolean {
  const code = readCommercialErrorCode(err);
  return code === "analysis_context_incomplete";
}
