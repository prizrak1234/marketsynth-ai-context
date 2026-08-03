/** Guards against stale context hydration clobbering active BIV research UI. */

export type AgencyPhase = "intake" | "analyzing" | "verdict";

export type ContextApplyAction =
  | { kind: "start_empty" }
  | { kind: "recovery" }
  | { kind: "completed_hydrate" }
  | { kind: "confirmed_ready" }
  | { kind: "analyzing_resume" }
  | { kind: "intake_form" }
  | { kind: "noop_active_research"; reason: string };

export function resolveContextApplyAction(input: {
  contextState: string | null;
  hasCompleted: boolean;
  confirmedByUser: boolean;
  runInFlight: boolean;
  currentPhase: AgencyPhase;
}): ContextApplyAction {
  if (!input.contextState) {
    return { kind: "start_empty" };
  }

  if (input.runInFlight || input.currentPhase === "analyzing") {
    return { kind: "noop_active_research", reason: "active_research" };
  }

  if (input.contextState === "hydrated_unconfirmed") {
    return { kind: "recovery" };
  }
  if (input.contextState === "completed" && input.hasCompleted) {
    return { kind: "completed_hydrate" };
  }
  if (
    input.contextState === "analyzing" ||
    input.contextState === "analysis_requested"
  ) {
    return { kind: "analyzing_resume" };
  }
  if (input.confirmedByUser && input.contextState === "confirmed") {
    return { kind: "confirmed_ready" };
  }
  return { kind: "intake_form" };
}

export function shouldBlockProjectHydrate(input: {
  runInFlight: boolean;
  currentPhase: AgencyPhase;
}): boolean {
  return input.runInFlight || input.currentPhase === "analyzing";
}

export function shouldShowIntakeForm(input: {
  phase: AgencyPhase;
  intakeView: string;
  sessionExpiredDuringResearch: boolean;
}): boolean {
  if (input.sessionExpiredDuringResearch) {
    return false;
  }
  return (
    input.phase === "intake" &&
    (input.intakeView === "form" || input.intakeView === "confirmed")
  );
}

export function mapPollingAuthErrorCode(
  status: number,
  code: string | undefined,
): "session_expired" | "authentication_required" | null {
  if (status !== 401) {
    return null;
  }
  const normalized = (code ?? "").toLowerCase();
  if (normalized.includes("session_expired") || normalized.includes("session_revoked")) {
    return "session_expired";
  }
  return "authentication_required";
}
