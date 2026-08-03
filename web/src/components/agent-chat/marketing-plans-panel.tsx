"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import { MarketingScenariosPicker } from "@/components/agent-chat/marketing-scenarios-picker";
import { BusinessCampaignsPanel } from "@/components/agent-chat/business-campaigns-panel";
import { BusinessOperatorPanel } from "@/components/agent-chat/business-operator-panel";
import { ScenarioWizardPanel } from "@/components/agent-chat/scenario-wizard-panel";
import {
  approveMarketingPlan,
  archiveMarketingPlan,
  fetchMarketingPlans,
} from "@/lib/api/endpoints/marketing-plans";
import {
  cancelMarketingPlanExecutionRun,
  completePlaceholderMarketingPlanExecutionRun,
  createMarketingPlanExecutionRun,
  executeStrategistTask,
  fetchMarketingPlanExecutionRuns,
  startMarketingPlanExecutionRun,
} from "@/lib/api/endpoints/marketing-plan-execution";
import {
  approveMarketingSpecialistOutput,
  archiveMarketingSpecialistOutput,
  createContentAssetFromCopywriterOutput,
  createTaskPlaceholderSpecialistOutput,
  fetchMarketingSpecialistOutputs,
} from "@/lib/api/endpoints/marketing-specialist-outputs";
import { V2ExecutionRunTasks } from "@/components/agent-chat/v2-execution-run-tasks";
import { V2SpecialistOutputCard } from "@/components/agent-chat/v2-specialist-output-card";
import type { MarketingPlanExecutionRun } from "@/lib/api/types/marketing-plan-execution";
import type { MarketingPlan } from "@/lib/api/types/marketing-plans";
import type { MarketingSpecialistOutput } from "@/lib/api/types/marketing-specialist-outputs";

type MarketingPlansPanelProps = {
  projectId: string;
};

function statusLabel(status: MarketingPlan["status"]) {
  switch (status) {
    case "approved":
      return "Approved";
    case "archived":
      return "Archived";
    default:
      return "Draft";
  }
}

function runStatusLabel(status: MarketingPlanExecutionRun["status"]) {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function PlanRow({
  plan,
  projectId,
  onUpdated,
}: {
  plan: MarketingPlan;
  projectId: string;
  onUpdated: () => void;
}) {
  const createRunMutation = useMutation({
    mutationFn: () => createMarketingPlanExecutionRun(projectId, plan.id),
    onSuccess: onUpdated,
  });
  const approveMutation = useMutation({
    mutationFn: () => approveMarketingPlan(projectId, plan.id),
    onSuccess: onUpdated,
  });
  const archiveMutation = useMutation({
    mutationFn: () => archiveMarketingPlan(projectId, plan.id),
    onSuccess: onUpdated,
  });

  const busy =
    approveMutation.isPending ||
    archiveMutation.isPending ||
    createRunMutation.isPending;
  const error =
    (approveMutation.error instanceof ApiError && approveMutation.error.message) ||
    (archiveMutation.error instanceof ApiError && archiveMutation.error.message) ||
    (createRunMutation.error instanceof ApiError && createRunMutation.error.message) ||
    null;

  return (
    <li className="rounded-md border border-border bg-muted/30 px-2 py-2 text-xs">
      <p className="font-medium text-foreground">{plan.title}</p>
      <p className="text-muted-foreground line-clamp-2">{plan.goal}</p>
      <p className="mt-1 text-muted-foreground">
        {statusLabel(plan.status)} · v{plan.current_version_number}
        {plan.approved_version_number != null
          ? ` · approved v${plan.approved_version_number}`
          : ""}
        {plan.source_scenario_name ? ` · scenario: ${plan.source_scenario_name}` : ""}
      </p>
      <div className="mt-2 flex flex-wrap gap-1">
        {plan.status === "draft" ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-6 text-[10px]"
            disabled={busy}
            onClick={() => approveMutation.mutate()}
          >
            Approve
          </Button>
        ) : null}
        {plan.status === "approved" ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-6 text-[10px]"
            disabled={busy}
            onClick={() => createRunMutation.mutate()}
          >
            Create execution run
          </Button>
        ) : null}
        {plan.status !== "archived" ? (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-6 text-[10px]"
            disabled={busy}
            onClick={() => archiveMutation.mutate()}
          >
            Archive
          </Button>
        ) : null}
      </div>
      {error ? <p className="mt-1 text-destructive">{error}</p> : null}
    </li>
  );
}

function specialistLabel(specialist: string) {
  return specialist.replace(/_/g, " ");
}

function SpecialistOutputRow({
  output,
  projectId,
  onUpdated,
}: {
  output: MarketingSpecialistOutput;
  projectId: string;
  onUpdated: () => void;
}) {
  const [linkedAssetId, setLinkedAssetId] = useState<string | null>(null);
  const approveMutation = useMutation({
    mutationFn: () => approveMarketingSpecialistOutput(projectId, output.id),
    onSuccess: onUpdated,
  });
  const createAssetMutation = useMutation({
    mutationFn: () => createContentAssetFromCopywriterOutput(projectId, output.id),
    onSuccess: (data) => {
      setLinkedAssetId(data.content_asset_id);
      onUpdated();
    },
  });
  const archiveMutation = useMutation({
    mutationFn: () => archiveMarketingSpecialistOutput(projectId, output.id),
    onSuccess: onUpdated,
  });
  const busy =
    approveMutation.isPending ||
    archiveMutation.isPending ||
    createAssetMutation.isPending;
  const err =
    (approveMutation.error instanceof ApiError && approveMutation.error.message) ||
    (createAssetMutation.error instanceof ApiError && createAssetMutation.error.message) ||
    (archiveMutation.error instanceof ApiError && archiveMutation.error.message) ||
    null;

  return (
    <li className="rounded border border-border/60 bg-background px-2 py-1.5 text-[10px]">
      <p className="font-medium">
        {specialistLabel(output.specialist)} · {output.output_type} · {output.status} · v
        {output.current_version_number}
        {output.approved_version_number != null
          ? ` (approved v${output.approved_version_number})`
          : ""}
      </p>
      <V2SpecialistOutputCard output={output} />
      <div className="mt-1 flex flex-wrap gap-1">
        {output.status === "draft" ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-5 text-[9px]"
            disabled={busy}
            onClick={() => approveMutation.mutate()}
          >
            Approve output
          </Button>
        ) : null}
        {output.specialist === "copywriter" &&
        output.status === "approved" &&
        output.output_type === "content_copy" &&
        !linkedAssetId ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-5 text-[9px]"
            disabled={busy}
            onClick={() => createAssetMutation.mutate()}
          >
            Create Content Asset
          </Button>
        ) : null}
        {output.status !== "archived" ? (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-5 text-[9px]"
            disabled={busy}
            onClick={() => archiveMutation.mutate()}
          >
            Archive output
          </Button>
        ) : null}
      </div>
      {linkedAssetId ? (
        <p className="mt-1 text-[10px] text-muted-foreground">
          Content asset created (draft) · {linkedAssetId.slice(0, 8)}…
        </p>
      ) : null}
      {err ? <p className="mt-0.5 text-destructive">{err}</p> : null}
    </li>
  );
}

function ExecutionRunRow({
  run,
  planTitle,
  projectId,
  onUpdated,
  expanded,
  onToggleExpand,
}: {
  run: MarketingPlanExecutionRun;
  planTitle: string;
  projectId: string;
  onUpdated: () => void;
  expanded: boolean;
  onToggleExpand: () => void;
}) {
  const outputsQuery = useQuery({
    queryKey: ["marketing-specialist-outputs", projectId, run.id],
    queryFn: () =>
      fetchMarketingSpecialistOutputs(projectId, { execution_run_id: run.id }),
    enabled: expanded && Boolean(projectId),
  });

  const placeholderMutation = useMutation({
    mutationFn: (taskIndex: number) =>
      createTaskPlaceholderSpecialistOutput(projectId, run.id, taskIndex),
    onSuccess: () => {
      void outputsQuery.refetch();
      onUpdated();
    },
  });
  const [pipelineCompletedNotice, setPipelineCompletedNotice] = useState(false);
  const executeStrategistMutation = useMutation({
    mutationFn: (taskIndex: number) =>
      executeStrategistTask(projectId, run.id, taskIndex),
    onSuccess: (data) => {
      void outputsQuery.refetch();
      onUpdated();
      setPipelineCompletedNotice(data.run_completed);
    },
  });

  const startMutation = useMutation({
    mutationFn: () => startMarketingPlanExecutionRun(projectId, run.id),
    onSuccess: onUpdated,
  });
  const completeMutation = useMutation({
    mutationFn: () =>
      completePlaceholderMarketingPlanExecutionRun(projectId, run.id),
    onSuccess: onUpdated,
  });
  const cancelMutation = useMutation({
    mutationFn: () => cancelMarketingPlanExecutionRun(projectId, run.id),
    onSuccess: onUpdated,
  });

  const busy =
    startMutation.isPending ||
    completeMutation.isPending ||
    cancelMutation.isPending ||
    placeholderMutation.isPending ||
    executeStrategistMutation.isPending;
  const terminal = ["succeeded", "failed", "cancelled"].includes(run.status);
  const err =
    (startMutation.error instanceof ApiError && startMutation.error.message) ||
    (completeMutation.error instanceof ApiError && completeMutation.error.message) ||
    (cancelMutation.error instanceof ApiError && cancelMutation.error.message) ||
    (placeholderMutation.error instanceof ApiError && placeholderMutation.error.message) ||
    (executeStrategistMutation.error instanceof ApiError &&
      executeStrategistMutation.error.message) ||
    null;

  const outputByTask = new Map(
    (outputsQuery.data ?? []).map((o) => [o.task_index, o]),
  );

  return (
    <li className="rounded-md border border-dashed border-border px-2 py-2 text-xs">
      <button
        type="button"
        className="w-full text-left"
        onClick={onToggleExpand}
      >
        <p className="font-medium">{planTitle}</p>
      <p className="text-muted-foreground">
        {runStatusLabel(run.status)} · v{run.marketing_plan_version_number} ·{" "}
        {run.task_snapshots.length} tasks
      </p>
      <p className="text-[10px] text-muted-foreground">
        {new Date(run.created_at).toLocaleString()} ·{" "}
        {expanded ? "Hide tasks" : "Show tasks & outputs"}
      </p>
      </button>
      {!terminal ? (
        <div className="mt-2 flex flex-wrap gap-1">
          {run.status === "queued" ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-6 text-[10px]"
              disabled={busy}
              onClick={() => startMutation.mutate()}
            >
              Start
            </Button>
          ) : null}
          {run.status === "running" ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-6 text-[10px]"
              disabled={busy}
              onClick={() => completeMutation.mutate()}
            >
              Complete placeholder
            </Button>
          ) : null}
          {run.status === "queued" || run.status === "running" ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-6 text-[10px]"
              disabled={busy}
              onClick={() => cancelMutation.mutate()}
            >
              Cancel
            </Button>
          ) : null}
        </div>
      ) : null}
      {run.result_summary?.message ? (
        <p className="mt-1 text-muted-foreground">{String(run.result_summary.message)}</p>
      ) : null}
      {run.status === "succeeded" &&
      run.result_summary &&
      typeof run.result_summary === "object" &&
      (run.result_summary as Record<string, unknown>).mode === "specialist_pipeline" ? (
        <p className="mt-1 text-[10px] font-medium text-green-700 dark:text-green-400">
          Marketing pipeline completed
        </p>
      ) : null}
      {pipelineCompletedNotice ? (
        <p className="mt-1 text-[10px] font-medium text-green-700 dark:text-green-400">
          Marketing pipeline completed
        </p>
      ) : null}
      {expanded ? (
        <div className="mt-2 space-y-2 border-t border-border/60 pt-2">
          <p className="text-[10px] text-muted-foreground">Task snapshots</p>
          <V2ExecutionRunTasks
            run={run}
            outputByTask={outputByTask}
            busy={busy}
            onExecute={(index) => executeStrategistMutation.mutate(index)}
            onPlaceholder={(index) => placeholderMutation.mutate(index)}
          />
          <p className="text-[10px] text-muted-foreground">Specialist outputs</p>
          {outputsQuery.isLoading ? (
            <p className="text-[10px] text-muted-foreground">Loading outputs…</p>
          ) : !outputsQuery.data?.length ? (
            <p className="text-[10px] text-muted-foreground">No outputs for this run yet.</p>
          ) : (
            <ul className="flex flex-col gap-1">
              {outputsQuery.data.map((output) => (
                <SpecialistOutputRow
                  key={output.id}
                  output={output}
                  projectId={projectId}
                  onUpdated={() => {
                    void outputsQuery.refetch();
                    onUpdated();
                  }}
                />
              ))}
            </ul>
          )}
        </div>
      ) : null}
      {err ? <p className="mt-1 text-destructive">{err}</p> : null}
    </li>
  );
}

export function MarketingPlansPanel({ projectId }: MarketingPlansPanelProps) {
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null);
  const [activeWizardRunId, setActiveWizardRunId] = useState<string | null>(null);
  const [focusCampaignId, setFocusCampaignId] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const plansQuery = useQuery({
    queryKey: ["marketing-plans", projectId],
    queryFn: () => fetchMarketingPlans(projectId, { limit: 50 }),
    enabled: Boolean(projectId),
  });
  const runsQuery = useQuery({
    queryKey: ["marketing-plan-execution-runs", projectId],
    queryFn: () => fetchMarketingPlanExecutionRuns(projectId, { limit: 50 }),
    enabled: Boolean(projectId),
  });

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["marketing-plans", projectId] });
    void queryClient.invalidateQueries({
      queryKey: ["marketing-plan-execution-runs", projectId],
    });
    void queryClient.invalidateQueries({
      queryKey: ["marketing-specialist-outputs", projectId],
    });
  };

  const planById = new Map((plansQuery.data ?? []).map((p) => [p.id, p]));

  return (
    <div className="rounded-lg border border-border p-3">
      <h3 className="text-sm font-semibold">Marketing plans</h3>
      <p className="mb-2 text-xs text-muted-foreground">
        Approve a plan, then create an execution run. Execute specialists manually from grouped
        pipeline panels (frozen six + v2 tracks).
      </p>
      <MarketingScenariosPicker
        projectId={projectId}
        onPlanCreated={refresh}
        onWizardStarted={setActiveWizardRunId}
      />
      <BusinessOperatorPanel
        projectId={projectId}
        onCampaignCreated={setFocusCampaignId}
      />
      <BusinessCampaignsPanel
        projectId={projectId}
        onWizardStarted={setActiveWizardRunId}
        focusCampaignId={focusCampaignId}
      />
      <div className="mb-3 mt-3">
        <h4 className="mb-1 text-xs font-semibold text-foreground">Scenario wizard</h4>
        <ScenarioWizardPanel
          projectId={projectId}
          activeRunId={activeWizardRunId}
          onRefreshPlans={refresh}
        />
      </div>
      {plansQuery.isLoading ? (
        <p className="text-xs text-muted-foreground">Loading plans…</p>
      ) : plansQuery.error ? (
        <p className="text-xs text-destructive">Failed to load plans</p>
      ) : !plansQuery.data?.length ? (
        <p className="text-xs text-muted-foreground">No saved plans yet.</p>
      ) : (
        <ul className="mb-3 flex max-h-40 flex-col gap-2 overflow-y-auto">
          {plansQuery.data.map((plan) => (
            <PlanRow key={plan.id} plan={plan} projectId={projectId} onUpdated={refresh} />
          ))}
        </ul>
      )}
      <h4 className="text-xs font-semibold text-foreground">Execution runs</h4>
      {runsQuery.isLoading ? (
        <p className="text-xs text-muted-foreground">Loading runs…</p>
      ) : !runsQuery.data?.length ? (
        <p className="text-xs text-muted-foreground">No execution runs yet.</p>
      ) : (
        <ul className="flex max-h-40 flex-col gap-2 overflow-y-auto">
          {runsQuery.data.map((run) => (
            <ExecutionRunRow
              key={run.id}
              run={run}
              projectId={projectId}
              planTitle={planById.get(run.marketing_plan_id)?.title ?? "Plan"}
              onUpdated={refresh}
              expanded={expandedRunId === run.id}
              onToggleExpand={() =>
                setExpandedRunId((current) => (current === run.id ? null : run.id))
              }
            />
          ))}
        </ul>
      )}
    </div>
  );
}
