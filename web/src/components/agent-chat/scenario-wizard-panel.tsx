"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import {
  advanceScenarioWizardRun,
  fetchScenarioWizardRuns,
} from "@/lib/api/endpoints/scenario-wizard-runs";
import {
  SCENARIO_WIZARD_STEPS,
  type ScenarioWizardRun,
  wizardStepLabel,
} from "@/lib/api/types/scenario-wizard-runs";

type ScenarioWizardPanelProps = {
  projectId: string;
  activeRunId?: string | null;
  onRefreshPlans?: () => void;
};

function statusLabel(status: ScenarioWizardRun["status"]) {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function resourceSummary(stepResults: Record<string, unknown>) {
  const keys = [
    "marketing_plan_id",
    "execution_run_id",
    "content_asset_id",
    "media_brief_id",
    "publication_package_id",
    "publication_package_job_id",
  ];
  return keys
    .filter((key) => stepResults[key])
    .map((key) => `${key.replace(/_id$/, "")}: ${String(stepResults[key]).slice(0, 8)}…`);
}

export function ScenarioWizardPanel({
  projectId,
  activeRunId,
  onRefreshPlans,
}: ScenarioWizardPanelProps) {
  const queryClient = useQueryClient();
  const runsQuery = useQuery({
    queryKey: ["scenario-wizard-runs", projectId],
    queryFn: () => fetchScenarioWizardRuns(projectId),
    enabled: Boolean(projectId),
  });

  const run =
    runsQuery.data?.find((item) => item.id === activeRunId) ?? runsQuery.data?.[0] ?? null;

  const advanceMutation = useMutation({
    mutationFn: () => {
      if (!run) {
        throw new Error("No wizard run selected");
      }
      return advanceScenarioWizardRun(projectId, run.id);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["scenario-wizard-runs", projectId] });
      void queryClient.invalidateQueries({ queryKey: ["marketing-plans", projectId] });
      onRefreshPlans?.();
    },
  });

  const terminal = run && ["succeeded", "failed", "cancelled"].includes(run.status);
  const completedSteps = new Set(
    Array.isArray(run?.step_results?.steps_completed)
      ? (run?.step_results?.steps_completed as string[])
      : [],
  );
  const error =
    advanceMutation.error instanceof ApiError ? advanceMutation.error.message : null;

  if (runsQuery.isLoading) {
    return <p className="text-[10px] text-muted-foreground">Loading wizard runs…</p>;
  }

  if (!run) {
    return (
      <p className="text-[10px] text-muted-foreground">
        Start a wizard from a scenario card to walk through the campaign pipeline one step at a
        time.
      </p>
    );
  }

  return (
    <div className="rounded-md border border-border bg-muted/10 p-2">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-semibold text-foreground">{run.scenario_name} wizard</p>
          <p className="text-[10px] text-muted-foreground">
            {statusLabel(run.status)} · current: {wizardStepLabel(run.current_step)}
          </p>
        </div>
        {!terminal ? (
          <Button
            type="button"
            variant="default"
            size="sm"
            className="h-7 text-[10px]"
            disabled={advanceMutation.isPending}
            onClick={() => advanceMutation.mutate()}
          >
            {advanceMutation.isPending ? "Advancing…" : "Advance step"}
          </Button>
        ) : null}
      </div>

      <ol className="mb-2 max-h-36 space-y-1 overflow-y-auto text-[10px]">
        {SCENARIO_WIZARD_STEPS.map((step) => {
          const done = completedSteps.has(step);
          const current = run.current_step === step && !terminal;
          return (
            <li
              key={step}
              className={
                current
                  ? "font-medium text-foreground"
                  : done
                    ? "text-green-700 dark:text-green-400"
                    : "text-muted-foreground"
              }
            >
              {done ? "✓ " : current ? "→ " : "· "}
              {wizardStepLabel(step)}
            </li>
          );
        })}
      </ol>

      {resourceSummary(run.step_results).length ? (
        <p className="text-[10px] text-muted-foreground">
          {resourceSummary(run.step_results).join(" · ")}
        </p>
      ) : null}

      {run.failure_reason ? (
        <p className="mt-1 text-[10px] text-destructive">{run.failure_reason}</p>
      ) : null}
      {error ? <p className="mt-1 text-[10px] text-destructive">{error}</p> : null}
      {run.status === "succeeded" ? (
        <p className="mt-1 text-[10px] font-medium text-green-700 dark:text-green-400">
          Wizard complete — dry-run job queued (no real publish).
        </p>
      ) : null}
    </div>
  );
}
