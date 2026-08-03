import type { BusinessIdeaValidationOutput } from "@/lib/api/types/business-idea-validation";
import {
  isPartialResearchOutput,
  isResearchTerminal,
} from "@/lib/api/types/business-idea-validation";
import type { CommercialErrorView } from "@/lib/errors/commercial-error-mapper";

export type BivWorkspaceState =
  | "idle"
  | "intake"
  | "context_confirmed"
  | "research_starting"
  | "research_running"
  | "report_building"
  | "completed"
  | "failed"
  | "partial_research"
  | "session_expired"
  | "legacy_migration_required";

export type BivWorkspaceViewModel = {
  state: BivWorkspaceState;
  activeRunId: string | null;
  latestCompletedRunId: string | null;
  customerReport: BusinessIdeaValidationOutput["customer_report"];
  validationResult: BusinessIdeaValidationOutput | null;
  progressVisible: boolean;
  failure: CommercialErrorView | null;
  canRerun: boolean;
  canRefine: boolean;
  canDownload: boolean;
  sessionExpired: boolean;
  showLegacyMigrationOnly: boolean;
  showCompletedReport: boolean;
  showResearchProgress: boolean;
  showFailurePanel: boolean;
  showControlledRecovery: boolean;
  showIntake: boolean;
  showConfirmedReady: boolean;
  showPartialResearchPanel: boolean;
  duplicateActionsBlocked: boolean;
};

type DeriveArgs = {
  phase: "intake" | "analyzing" | "verdict";
  intakeView: "start" | "recovery" | "form" | "confirmed";
  loading: boolean;
  rerunStarting: boolean;
  sessionExpiredDuringResearch: boolean;
  validationResult: BusinessIdeaValidationOutput | null;
  activeRunId: string | null;
  researchFailure: CommercialErrorView | null;
  runInFlight: boolean;
  confirmedContextConfirmed: boolean;
};

export function deriveBivWorkspaceViewModel(args: DeriveArgs): BivWorkspaceViewModel {
  const {
    phase,
    intakeView,
    loading,
    rerunStarting,
    sessionExpiredDuringResearch,
    validationResult,
    activeRunId,
    researchFailure,
    runInFlight,
    confirmedContextConfirmed,
  } = args;

  const terminal = validationResult ? isResearchTerminal(validationResult) : false;
  const partialResearch = isPartialResearchOutput(validationResult);
  const hasCustomerReport = Boolean(validationResult?.customer_report);
  const legacyNeedsMigration = terminal && !hasCustomerReport && !partialResearch;

  const startingFreshRun =
    rerunStarting || (runInFlight && loading && !validationResult);

  let state: BivWorkspaceState = "idle";
  if (sessionExpiredDuringResearch) {
    state = "session_expired";
  } else if (partialResearch && phase === "analyzing" && !startingFreshRun) {
    state = "partial_research";
  } else if (partialResearch && phase === "analyzing" && startingFreshRun) {
    state = "research_running";
  } else if (researchFailure && phase === "analyzing") {
    state = "failed";
  } else if (legacyNeedsMigration && phase === "verdict" && !runInFlight) {
    state = "legacy_migration_required";
  } else if (rerunStarting || (phase === "analyzing" && loading && !validationResult)) {
    state = "research_starting";
  } else if (phase === "analyzing" && (loading || runInFlight)) {
    state = "research_running";
  } else if (hasCustomerReport && phase === "verdict") {
    state = "completed";
  } else if (phase === "intake" && intakeView === "confirmed" && confirmedContextConfirmed) {
    state = "context_confirmed";
  } else if (phase === "intake") {
    state = "intake";
  } else if (researchFailure && phase === "verdict") {
    state = "failed";
  } else if (phase === "verdict" && terminal) {
    state = legacyNeedsMigration ? "legacy_migration_required" : "completed";
  }

  const showFailurePanel = state === "failed" && Boolean(researchFailure) && !partialResearch;
  const showResearchProgress =
    state === "research_starting" ||
    state === "research_running" ||
    state === "session_expired" ||
    (phase === "analyzing" && runInFlight && !researchFailure && !partialResearch);
  const showLegacyMigrationOnly = state === "legacy_migration_required" && !runInFlight;
  const showCompletedReport =
    state === "completed" && hasCustomerReport && !showResearchProgress && !showFailurePanel;
  const progressVisible =
    (showResearchProgress || showFailurePanel) &&
    !showLegacyMigrationOnly &&
    !showCompletedReport;

  const showIntake = phase === "intake" && intakeView !== "confirmed";
  const showConfirmedReady = state === "context_confirmed" && !loading;
  const showControlledRecovery =
    !showIntake &&
    !showConfirmedReady &&
    !progressVisible &&
    !showCompletedReport &&
    !showLegacyMigrationOnly &&
    !partialResearch &&
    state !== "partial_research" &&
    (phase === "analyzing" || (phase === "verdict" && !hasCustomerReport && !researchFailure));

  return {
    state,
    activeRunId,
    latestCompletedRunId: validationResult?.run_id ?? activeRunId,
    customerReport: validationResult?.customer_report ?? null,
    validationResult,
    progressVisible,
    failure: researchFailure,
    canRerun: Boolean(
      confirmedContextConfirmed &&
        (partialResearch || (validationResult && terminal)),
    ),
    canRefine: Boolean(validationResult && terminal && !partialResearch),
    canDownload: hasCustomerReport,
    sessionExpired: sessionExpiredDuringResearch,
    showLegacyMigrationOnly,
    showCompletedReport,
    showResearchProgress: progressVisible,
    showFailurePanel,
    showControlledRecovery,
    showIntake,
    showConfirmedReady,
    showPartialResearchPanel: state === "partial_research" && partialResearch,
    duplicateActionsBlocked:
      showLegacyMigrationOnly ||
      showResearchProgress ||
      showFailurePanel ||
      (state === "partial_research" && runInFlight),
  };
}
