"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import {
  createMarketingPlanFromScenario,
  fetchMarketingScenarios,
} from "@/lib/api/endpoints/marketing-scenarios";
import { createScenarioWizardRun } from "@/lib/api/endpoints/scenario-wizard-runs";
import type { ScenarioTemplate } from "@/lib/api/types/marketing-scenarios";

type MarketingScenariosPickerProps = {
  projectId: string;
  onPlanCreated: () => void;
  onWizardStarted?: (runId: string) => void;
};

function specialistLabel(specialist: string) {
  return specialist.replace(/_/g, " ");
}

function ScenarioCard({
  scenario,
  projectId,
  expanded,
  onToggle,
  onPlanCreated,
  onWizardStarted,
}: {
  scenario: ScenarioTemplate;
  projectId: string;
  expanded: boolean;
  onToggle: () => void;
  onPlanCreated: () => void;
  onWizardStarted?: (runId: string) => void;
}) {
  const createMutation = useMutation({
    mutationFn: () => createMarketingPlanFromScenario(projectId, scenario.id),
    onSuccess: () => {
      onPlanCreated();
    },
  });
  const wizardMutation = useMutation({
    mutationFn: () => createScenarioWizardRun(projectId, scenario.id),
    onSuccess: (run) => {
      onWizardStarted?.(run.id);
      onPlanCreated();
    },
  });

  const error =
    (createMutation.error instanceof ApiError && createMutation.error.message) ||
    (wizardMutation.error instanceof ApiError && wizardMutation.error.message) ||
    null;

  return (
    <li className="rounded-md border border-border bg-muted/20 px-2 py-2 text-xs">
      <button type="button" className="w-full text-left" onClick={onToggle}>
        <p className="font-medium text-foreground">{scenario.name}</p>
        <p className="text-muted-foreground">{scenario.industry}</p>
        <p className="mt-1 line-clamp-2 text-muted-foreground">{scenario.goal}</p>
        <p className="mt-1 text-[10px] text-muted-foreground">
          {scenario.required_specialists.length} specialists ·{" "}
          {expanded ? "Hide preview" : "Preview tasks"}
        </p>
      </button>
      {expanded ? (
        <div className="mt-2 space-y-2 border-t border-border/60 pt-2">
          <p className="text-[10px] font-medium text-foreground">Tasks</p>
          <ol className="list-decimal space-y-1 pl-4 text-[10px] text-muted-foreground">
            {scenario.default_plan_tasks.map((task) => (
              <li key={task.specialist}>
                <span className="font-medium text-foreground">
                  {specialistLabel(task.specialist)}
                </span>
                {" — "}
                {task.objective}
              </li>
            ))}
          </ol>
          {scenario.expected_artifacts.length ? (
            <>
              <p className="text-[10px] font-medium text-foreground">Expected artifacts</p>
              <ul className="list-disc pl-4 text-[10px] text-muted-foreground">
                {scenario.expected_artifacts.map((artifact) => (
                  <li key={artifact}>{artifact}</li>
                ))}
              </ul>
            </>
          ) : null}
        </div>
      ) : null}
      <div className="mt-2 flex flex-wrap gap-1">
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="h-6 text-[10px]"
          disabled={createMutation.isPending || wizardMutation.isPending}
          onClick={() => createMutation.mutate()}
        >
          {createMutation.isPending ? "Creating…" : "Create plan"}
        </Button>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          className="h-6 text-[10px]"
          disabled={createMutation.isPending || wizardMutation.isPending}
          onClick={() => wizardMutation.mutate()}
        >
          {wizardMutation.isPending ? "Starting…" : "Start wizard"}
        </Button>
      </div>
      {error ? <p className="mt-1 text-destructive">{error}</p> : null}
    </li>
  );
}

export function MarketingScenariosPicker({
  projectId,
  onPlanCreated,
  onWizardStarted,
}: MarketingScenariosPickerProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const scenariosQuery = useQuery({
    queryKey: ["marketing-scenarios", projectId],
    queryFn: () => fetchMarketingScenarios(projectId),
    enabled: Boolean(projectId),
  });

  return (
    <div className="mb-3 rounded-md border border-dashed border-border p-2">
      <h4 className="text-xs font-semibold text-foreground">Start from scenario</h4>
      <p className="mb-2 text-[10px] text-muted-foreground">
        Pick a business outcome — Marketsynth assembles the right specialists into a draft plan.
      </p>
      {scenariosQuery.isLoading ? (
        <p className="text-[10px] text-muted-foreground">Loading scenarios…</p>
      ) : scenariosQuery.error ? (
        <p className="text-[10px] text-destructive">Failed to load scenarios</p>
      ) : !scenariosQuery.data?.length ? (
        <p className="text-[10px] text-muted-foreground">No scenarios available.</p>
      ) : (
        <ul className="flex max-h-48 flex-col gap-2 overflow-y-auto">
          {scenariosQuery.data.map((scenario) => (
            <ScenarioCard
              key={scenario.id}
              scenario={scenario}
              projectId={projectId}
              expanded={expandedId === scenario.id}
              onToggle={() =>
                setExpandedId((current) => (current === scenario.id ? null : scenario.id))
              }
              onPlanCreated={onPlanCreated}
              onWizardStarted={onWizardStarted}
            />
          ))}
        </ul>
      )}
    </div>
  );
}
