/**
 * RUNTIME-01B — persisted BIV run polling (backend is source of truth).
 *
 * Canonical contracts:
 * - GET .../runs/{run_id}/progress — lightweight progress polling
 * - GET .../runs/{run_id} — status + output on terminal transition
 */

import {
  getBusinessIdeaValidationRun,
  getBusinessIdeaValidationRunProgress,
} from "@/lib/api/endpoints/business-idea-validation";
import type {
  BusinessIdeaValidationRunResponse,
  BusinessIdeaValidationRunStatus,
  BivRunProgress,
} from "@/lib/api/types/business-idea-validation";
import {
  isPartialResearchOutput,
  isResearchTerminal,
} from "@/lib/api/types/business-idea-validation";
import { ApiError } from "@/lib/api/client";

export const RESEARCH_POLL_INITIAL_MS = 1_500;
export const RESEARCH_POLL_MAX_MS = 4_000;
export const RESEARCH_POLL_MAX_DURATION_MS = 35 * 60 * 1_000;

export type ResearchPollCallbacks = {
  onProgress?: (progress: BivRunProgress) => void;
  onRunSnapshot?: (run: BusinessIdeaValidationRunResponse) => void;
};

export type ResearchPollResult =
  | { kind: "succeeded"; run: BusinessIdeaValidationRunResponse }
  | { kind: "partial"; run: BusinessIdeaValidationRunResponse }
  | { kind: "failed"; run: BusinessIdeaValidationRunResponse }
  | { kind: "not_found" }
  | { kind: "auth_error"; error: unknown }
  | { kind: "timeout" }
  | { kind: "aborted" };

export function isActiveRunStatus(
  status: BusinessIdeaValidationRunStatus | string | null | undefined,
): boolean {
  return status === "queued" || status === "pending" || status === "running";
}

export function isTerminalRunStatus(
  status: BusinessIdeaValidationRunStatus | string | null | undefined,
): boolean {
  return status === "succeeded" || status === "failed";
}

function pollIntervalMs(elapsedMs: number): number {
  if (elapsedMs < 60_000) {
    return RESEARCH_POLL_INITIAL_MS;
  }
  if (elapsedMs < 180_000) {
    return 2_500;
  }
  return RESEARCH_POLL_MAX_MS;
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }
    const timer = window.setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        window.clearTimeout(timer);
        reject(new DOMException("Aborted", "AbortError"));
      },
      { once: true },
    );
  });
}

export async function pollResearchRunUntilTerminal(input: {
  userRequestId: string;
  runId: string;
  callbacks?: ResearchPollCallbacks;
  signal?: AbortSignal;
  maxDurationMs?: number;
}): Promise<ResearchPollResult> {
  const started = Date.now();
  const maxDuration = input.maxDurationMs ?? RESEARCH_POLL_MAX_DURATION_MS;
  let ticks = 0;

  while (Date.now() - started < maxDuration) {
    if (input.signal?.aborted) {
      return { kind: "aborted" };
    }

    const elapsed = Date.now() - started;
    let progress: BivRunProgress | null = null;

    try {
      progress = await getBusinessIdeaValidationRunProgress(
        input.userRequestId,
        input.runId,
      );
      input.callbacks?.onProgress?.(progress);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401 || err.status === 403) {
          return { kind: "auth_error", error: err };
        }
        if (err.status === 404) {
          return { kind: "not_found" };
        }
        if (err.status >= 500) {
          /* transient — continue polling */
        } else {
          throw err;
        }
      } else {
        throw err;
      }
    }

    ticks += 1;
    const shouldFetchRun =
      ticks === 1 ||
      ticks % 3 === 0 ||
      (progress != null && isTerminalRunStatus(progress.state));

    if (shouldFetchRun) {
      try {
        const run = await getBusinessIdeaValidationRun(
          input.userRequestId,
          input.runId,
        );
        input.callbacks?.onRunSnapshot?.(run);

        if (run.status === "failed") {
          if (isPartialResearchOutput(run.output)) {
            return { kind: "partial", run };
          }
          return { kind: "failed", run };
        }
        if (run.status === "succeeded" && !run.output) {
          /* output hydration may lag status — keep polling */
        } else if (
          run.status === "succeeded" &&
          run.output &&
          isResearchTerminal(run.output)
        ) {
          return { kind: "succeeded", run };
        }
      } catch (err) {
        if (err instanceof ApiError) {
          if (err.status === 401 || err.status === 403) {
            return { kind: "auth_error", error: err };
          }
          if (err.status === 404) {
            return { kind: "not_found" };
          }
          if (err.status < 500) {
            throw err;
          }
        } else {
          throw err;
        }
      }
    }

    await sleep(pollIntervalMs(elapsed), input.signal);
  }

  return { kind: "timeout" };
}
