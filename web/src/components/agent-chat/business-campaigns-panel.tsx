"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { CampaignSupervisorPanel } from "@/components/agent-chat/campaign-supervisor-panel";
import { CampaignWorkflowsPanel } from "@/components/agent-chat/campaign-workflows-panel";
import { MarketingSkillsPanel } from "@/components/agent-chat/marketing-skills-panel";
import { ApiError } from "@/lib/api/client";
import {
  createBusinessCampaign,
  executeCampaignAction,
  fetchBusinessCampaignControlCenter,
  fetchBusinessCampaignSummaries,
} from "@/lib/api/endpoints/business-campaigns";
import type {
  CampaignAction,
  CampaignControlCenter,
  CampaignHealthStatus,
} from "@/lib/api/types/business-campaigns";

type BusinessCampaignsPanelProps = {
  projectId: string;
  onWizardStarted?: (runId: string) => void;
  focusCampaignId?: string | null;
};

function healthLabel(status: CampaignHealthStatus) {
  return status.replace(/_/g, " ");
}

function resourceLinks(ids: CampaignControlCenter["resource_ids"]) {
  return Object.entries(ids).filter(([, value]) => value) as [string, string][];
}

function ControlCenterView({
  center,
  projectId,
  campaignId,
  onExecuted,
  onWizardStarted,
}: {
  center: CampaignControlCenter;
  projectId: string;
  campaignId: string;
  onExecuted: () => void;
  onWizardStarted?: (runId: string) => void;
}) {
  const [pendingAction, setPendingAction] = useState<CampaignAction | null>(null);
  const [lastMessage, setLastMessage] = useState<string | null>(null);

  const actionMutation = useMutation({
    mutationFn: (action: CampaignAction) =>
      executeCampaignAction(projectId, campaignId, action.type),
    onSuccess: (result) => {
      setLastMessage(result.message);
      setPendingAction(null);
      if (
        result.action_type === "start_wizard" &&
        result.created_resource_id &&
        onWizardStarted
      ) {
        onWizardStarted(result.created_resource_id);
      }
      onExecuted();
    },
  });

  const actionError =
    actionMutation.error instanceof ApiError ? actionMutation.error.message : null;

  const runAction = (action: CampaignAction) => {
    if (!action.enabled) return;
    if (action.confirmation_required) {
      setPendingAction(action);
      return;
    }
    actionMutation.mutate(action);
  };

  const {
    campaign,
    health,
    next_action,
    timeline,
    metrics,
    resource_ids,
    safe_warnings,
    recovery_hint,
    primary_action,
    available_actions = [],
    skill_suggestions = [],
    latest_skill_runs = [],
    skill_context,
    supervisor_health_score = 100,
    supervisor_findings_count = 0,
    critical_findings_count = 0,
    top_findings = [],
    workflow_suggestions = [],
    active_workflow = null,
  } = center;

  const secondaryActions = available_actions.filter(
    (action) => action.enabled && action.type !== primary_action?.type,
  );

  return (
    <div className="space-y-3 text-xs">
      <div>
        <div className="mb-1 flex items-center justify-between gap-2">
          <p className="font-semibold text-foreground">{campaign.name}</p>
          <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] capitalize text-muted-foreground">
            {healthLabel(health.status)}
          </span>
        </div>
        <p className="text-[10px] text-muted-foreground">{campaign.goal}</p>
      </div>

      <div>
        <div className="mb-1 flex justify-between text-[10px] text-muted-foreground">
          <span>Progress</span>
          <span>{health.progress_percent}%</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full bg-primary transition-all"
            style={{ width: `${health.progress_percent}%` }}
          />
        </div>
      </div>

      <div className="rounded-md border border-border bg-muted/20 p-2">
        <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
          Next action
        </p>
        <p className="font-medium text-foreground">{next_action.label}</p>
        <p className="mt-1 text-[10px] text-muted-foreground">{next_action.safe_description}</p>
        {primary_action ? (
          <Button
            type="button"
            size="sm"
            className="mt-2 h-7 text-[10px]"
            disabled={!primary_action.enabled || actionMutation.isPending}
            onClick={() => runAction(primary_action)}
          >
            {primary_action.label}
          </Button>
        ) : null}
        {health.blocking_reason ? (
          <p className="mt-2 text-[10px] text-amber-600 dark:text-amber-400">{health.blocking_reason}</p>
        ) : null}
        {lastMessage ? (
          <p className="mt-2 text-[10px] text-emerald-600 dark:text-emerald-400">{lastMessage}</p>
        ) : null}
        {actionError ? <p className="mt-2 text-[10px] text-destructive">{actionError}</p> : null}
      </div>

      {secondaryActions.length ? (
        <div>
          <p className="mb-1 text-[10px] font-semibold text-muted-foreground">Other actions</p>
          <div className="flex flex-wrap gap-1">
            {secondaryActions.map((action) => (
              <Button
                key={action.type}
                type="button"
                size="sm"
                variant="outline"
                className="h-7 text-[10px]"
                disabled={actionMutation.isPending}
                onClick={() => runAction(action)}
              >
                {action.label}
              </Button>
            ))}
          </div>
        </div>
      ) : null}

      {pendingAction ? (
        <div className="rounded-md border border-amber-500/40 bg-amber-500/5 p-2">
          <p className="text-[10px] font-semibold">Confirm action</p>
          <p className="text-[10px] text-muted-foreground">{pendingAction.label}</p>
          <div className="mt-2 flex gap-2">
            <Button
              type="button"
              size="sm"
              className="h-7 text-[10px]"
              disabled={actionMutation.isPending}
              onClick={() => actionMutation.mutate(pendingAction)}
            >
              Confirm
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-7 text-[10px]"
              onClick={() => setPendingAction(null)}
            >
              Cancel
            </Button>
          </div>
        </div>
      ) : null}

      <CampaignSupervisorPanel
        projectId={projectId}
        campaignId={campaignId}
        healthScore={supervisor_health_score}
        findingsCount={supervisor_findings_count}
        criticalCount={critical_findings_count}
        topFindings={top_findings}
        availableActions={available_actions}
        onRunAction={runAction}
      />

      <CampaignWorkflowsPanel
        projectId={projectId}
        campaignId={campaignId}
        workflowSuggestions={workflow_suggestions}
        activeWorkflow={active_workflow}
        availableActions={available_actions}
        onWorkflowCreated={onExecuted}
        onRunAction={runAction}
      />

      <MarketingSkillsPanel
        projectId={projectId}
        campaignId={campaignId}
        campaign={campaign}
        skillSuggestions={skill_suggestions}
        latestSkillRuns={latest_skill_runs}
        skillContext={skill_context}
        onSkillExecuted={onExecuted}
      />

      {recovery_hint ? (
        <div className="rounded-md border border-destructive/40 bg-destructive/5 p-2">
          <p className="text-[10px] font-semibold text-destructive">Recovery hint</p>
          <p className="text-[10px] text-muted-foreground">
            {recovery_hint.failed_object_type} · {recovery_hint.error_code ?? "error"}
          </p>
          <p className="mt-1 text-[10px]">{recovery_hint.suggested_recovery}</p>
        </div>
      ) : null}

      <dl className="grid grid-cols-3 gap-2 text-[10px]">
        <div>
          <dt className="text-muted-foreground">Plans</dt>
          <dd>{metrics.plans_total}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Content</dt>
          <dd>{metrics.assets_total}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Media</dt>
          <dd>{metrics.media_total}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Packages</dt>
          <dd>{metrics.packages_total}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Jobs</dt>
          <dd>{metrics.jobs_total}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Wizards</dt>
          <dd>{metrics.wizard_runs_total}</dd>
        </div>
      </dl>

      {resourceLinks(resource_ids).length ? (
        <div>
          <p className="mb-1 text-[10px] font-semibold text-muted-foreground">Artifact links</p>
          <ul className="flex flex-col gap-0.5 font-mono text-[10px]">
            {resourceLinks(resource_ids).map(([key, value]) => (
              <li key={key}>
                {key}: {value.slice(0, 8)}…
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {safe_warnings.length ? (
        <ul className="list-disc pl-4 text-[10px] text-amber-600 dark:text-amber-400">
          {safe_warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      ) : null}

      <div>
        <p className="mb-1 text-[10px] font-semibold text-muted-foreground">Timeline</p>
        {!timeline.length ? (
          <p className="text-[10px] text-muted-foreground">No events yet.</p>
        ) : (
          <ul className="max-h-36 space-y-1 overflow-y-auto">
            {timeline.map((event) => (
              <li
                key={`${event.event_type}-${event.resource_id}-${event.label}-${event.occurred_at}`}
                className="rounded border border-border/60 px-2 py-1 text-[10px]"
              >
                <span className="font-medium">{event.label}</span>
                {event.status ? (
                  <span className="text-muted-foreground"> · {event.status}</span>
                ) : null}
                {event.safe_summary ? (
                  <span className="block text-muted-foreground">{event.safe_summary}</span>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export function BusinessCampaignsPanel({
  projectId,
  onWizardStarted,
  focusCampaignId,
}: BusinessCampaignsPanelProps) {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [goal, setGoal] = useState("");
  const [scenarioId, setScenarioId] = useState("dental_clinic_lead_gen");
  const [healthFilter, setHealthFilter] = useState<CampaignHealthStatus | "">("");

  useEffect(() => {
    if (focusCampaignId) {
      setSelectedId(focusCampaignId);
    }
  }, [focusCampaignId]);

  const summariesQuery = useQuery({
    queryKey: ["business-campaign-summaries", projectId, healthFilter],
    queryFn: () =>
      fetchBusinessCampaignSummaries(projectId, {
        health: healthFilter || undefined,
      }),
    enabled: Boolean(projectId),
  });

  const activeId = selectedId ?? summariesQuery.data?.[0]?.campaign.id ?? null;

  const controlCenterQuery = useQuery({
    queryKey: ["business-campaign-control-center", projectId, activeId],
    queryFn: () => fetchBusinessCampaignControlCenter(projectId, activeId!),
    enabled: Boolean(projectId && activeId),
  });

  const refreshControlCenter = () => {
    void queryClient.invalidateQueries({
      queryKey: ["business-campaign-control-center", projectId],
    });
    void queryClient.invalidateQueries({ queryKey: ["business-campaign-summaries", projectId] });
    void queryClient.invalidateQueries({ queryKey: ["scenario-wizard-runs", projectId] });
    void queryClient.invalidateQueries({ queryKey: ["marketing-plans", projectId] });
  };

  const createMutation = useMutation({
    mutationFn: () =>
      createBusinessCampaign(projectId, {
        name: name.trim(),
        goal: goal.trim(),
        scenario_id: scenarioId.trim() || null,
      }),
    onSuccess: (created) => {
      setSelectedId(created.id);
      setName("");
      setGoal("");
      refreshControlCenter();
    },
  });

  const createError =
    createMutation.error instanceof ApiError ? createMutation.error.message : null;

  return (
    <div className="rounded-lg border border-border p-3">
      <h3 className="text-sm font-semibold">Campaign action center</h3>
      <p className="mb-2 text-xs text-muted-foreground">
        See what is next, click an explicit action button — each call uses existing services only
        (no hidden automation, no real Telegram publish).
      </p>

      <form
        className="mb-3 flex flex-col gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          if (!name.trim() || !goal.trim()) return;
          createMutation.mutate();
        }}
      >
        <input
          className="rounded border border-input bg-background px-2 py-1 text-xs"
          placeholder="Campaign name"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <textarea
          className="rounded border border-input bg-background px-2 py-1 text-xs"
          placeholder="Business goal"
          rows={2}
          value={goal}
          onChange={(event) => setGoal(event.target.value)}
        />
        <input
          className="rounded border border-input bg-background px-2 py-1 text-xs"
          placeholder="Scenario id (optional)"
          value={scenarioId}
          onChange={(event) => setScenarioId(event.target.value)}
        />
        <Button type="submit" size="sm" disabled={createMutation.isPending}>
          Create campaign
        </Button>
        {createError ? <p className="text-[10px] text-destructive">{createError}</p> : null}
      </form>

      <div className="mb-2 flex flex-wrap items-center gap-2">
        <label className="text-[10px] text-muted-foreground">
          Filter health
          <select
            className="ml-1 rounded border border-input bg-background px-1 py-0.5 text-[10px]"
            value={healthFilter}
            onChange={(event) =>
              setHealthFilter(event.target.value as CampaignHealthStatus | "")
            }
          >
            <option value="">All</option>
            <option value="healthy">Healthy</option>
            <option value="waiting_for_user">Waiting</option>
            <option value="blocked">Blocked</option>
            <option value="failed">Failed</option>
            <option value="completed">Completed</option>
          </select>
        </label>
      </div>

      {summariesQuery.isLoading ? (
        <p className="text-xs text-muted-foreground">Loading campaigns…</p>
      ) : !summariesQuery.data?.length ? (
        <p className="text-xs text-muted-foreground">No campaigns match filters.</p>
      ) : (
        <>
          <div className="mb-2 flex flex-wrap gap-1">
            {summariesQuery.data.map((summary) => (
              <button
                key={summary.campaign.id}
                type="button"
                className={`rounded px-2 py-0.5 text-[10px] ${
                  summary.campaign.id === activeId
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground"
                }`}
                onClick={() => setSelectedId(summary.campaign.id)}
                title={summary.next_action_type}
              >
                {summary.campaign.name}
              </button>
            ))}
          </div>
          {controlCenterQuery.isLoading ? (
            <p className="text-xs text-muted-foreground">Loading action center…</p>
          ) : controlCenterQuery.data && activeId ? (
            <ControlCenterView
              center={controlCenterQuery.data}
              projectId={projectId}
              campaignId={activeId}
              onExecuted={refreshControlCenter}
              onWizardStarted={onWizardStarted}
            />
          ) : null}
        </>
      )}
    </div>
  );
}
