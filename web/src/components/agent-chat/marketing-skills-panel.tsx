"use client";



import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useMemo, useState } from "react";



import { Button } from "@/components/ui/button";

import { ApiError } from "@/lib/api/client";

import {

  createMarketingSkillRun,

  fetchMarketingSkillRuns,

} from "@/lib/api/endpoints/marketing-skills";

import type {

  CampaignSkillContext,

  CampaignSkillSuggestion,

} from "@/lib/api/types/business-campaigns";

import type {

  MarketingSkillRun,

  MarketingSkillType,

} from "@/lib/api/types/marketing-skills";

import type { BusinessCampaign } from "@/lib/api/types/business-campaigns";



type MarketingSkillsPanelProps = {

  projectId: string;

  campaignId: string;

  campaign: BusinessCampaign;

  skillSuggestions: CampaignSkillSuggestion[];

  latestSkillRuns?: MarketingSkillRun[];

  skillContext?: CampaignSkillContext | null;

  onSkillExecuted?: () => void;

};



function buildSkillInput(

  campaign: BusinessCampaign,

  skillType: MarketingSkillType,

): Record<string, unknown> {

  const intent = (campaign.metadata?.source_business_intent ?? {}) as Record<string, unknown>;

  const base: Record<string, unknown> = {

    campaign_id: campaign.id,

    industry: intent.industry,

    goal: intent.goal ?? campaign.goal,

    geography: intent.geography,

    target_audience: intent.target_audience || campaign.name,

    offer: intent.offer || campaign.goal,

    segment_name: intent.target_audience || campaign.name,

  };



  if (skillType === "wordstat_research") {

    return {

      ...base,

      query: (intent.offer as string) || (intent.industry as string) || campaign.goal,

      create_tool_call: false,

    };

  }

  if (skillType === "metrica_analysis") {

    return { ...base, create_tool_call: false, natural_language: "traffic and device breakdown" };

  }

  if (skillType === "visual_report") {

    return {

      ...base,

      offer: (intent.offer as string) || campaign.goal,

      create_tool_call: false,

    };

  }

  return base;

}



function OutputPreview({ run }: { run: MarketingSkillRun }) {

  const output = run.output_payload ?? {};

  const conclusion =

    typeof output.business_conclusion === "string" ? output.business_conclusion : null;

  const provenance = output.provenance as Record<string, unknown> | undefined;

  const keys = Object.keys(output).filter((key) => key !== "provenance").slice(0, 6);



  return (

    <div className="mt-2 rounded border border-border/60 bg-muted/10 p-2 text-[10px]">

      <p className="font-semibold text-foreground">{run.skill_type.replace(/_/g, " ")}</p>

      {conclusion ? <p className="mt-1 text-muted-foreground">{conclusion}</p> : null}

      <ul className="mt-1 list-disc pl-4 text-muted-foreground">

        {keys.map((key) => (

          <li key={key}>{key}</li>

        ))}

      </ul>

      {provenance?.skill_run_id ? (

        <p className="mt-1 font-mono text-[9px] text-muted-foreground">

          run {String(provenance.skill_run_id).slice(0, 8)}

        </p>

      ) : null}

      {run.used_tool_call_ids.length ? (

        <p className="mt-1 font-mono text-[9px]">

          tools: {run.used_tool_call_ids.map((id) => id.slice(0, 8)).join(", ")}

        </p>

      ) : null}

    </div>

  );

}



function SkillContextCards({ context }: { context: CampaignSkillContext }) {

  const cards = (
    [
      ["Segment", context.segment_summary],
      ["Offer", context.offer_summary],
      ["Demand", context.demand_summary],
      ["Analytics", context.analytics_summary],
    ] as Array<[string, unknown]>
  ).filter(([, value]) => Boolean(value));



  if (!cards.length) return null;



  return (

    <div className="mt-2 space-y-1">

      <p className="text-[10px] font-semibold text-muted-foreground">Campaign skill context</p>

      {cards.map(([label, summary]) => (

        <div key={String(label)} className="rounded border border-border/60 bg-background/50 p-2 text-[10px]">

          <p className="font-medium">{label}</p>

          <pre className="mt-1 max-h-20 overflow-auto whitespace-pre-wrap text-muted-foreground">

            {JSON.stringify(summary, null, 0).slice(0, 280)}

          </pre>

        </div>

      ))}

    </div>

  );

}



export function MarketingSkillsPanel({

  projectId,

  campaignId,

  campaign,

  skillSuggestions,

  latestSkillRuns = [],

  skillContext,

  onSkillExecuted,

}: MarketingSkillsPanelProps) {

  const queryClient = useQueryClient();

  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const [pendingSkill, setPendingSkill] = useState<MarketingSkillType | null>(null);



  const runsQuery = useQuery({

    queryKey: ["marketing-skill-runs", projectId, campaignId],

    queryFn: () => fetchMarketingSkillRuns(projectId, { campaign_id: campaignId, limit: 20 }),

    enabled: Boolean(projectId && campaignId),

  });



  const runMutation = useMutation({

    mutationFn: (skillType: MarketingSkillType) =>

      createMarketingSkillRun(projectId, skillType, {

        campaign_id: campaignId,

        input_payload: buildSkillInput(campaign, skillType),

      }),

    onSuccess: (run) => {

      setSelectedRunId(run.id);

      setPendingSkill(null);

      void queryClient.invalidateQueries({ queryKey: ["marketing-skill-runs", projectId] });

      onSkillExecuted?.();

    },

  });



  const runError = runMutation.error instanceof ApiError ? runMutation.error.message : null;

  const runs = runsQuery.data ?? latestSkillRuns;

  const selectedRun = useMemo(

    () => runs.find((run) => run.id === selectedRunId) ?? runs[0] ?? null,

    [runs, selectedRunId],

  );



  if (!skillSuggestions.length && !runs.length && !skillContext) {

    return null;

  }



  return (

    <div className="rounded-md border border-border bg-muted/20 p-2">

      <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">

        Marketing skills

      </p>

      <p className="mb-2 text-[10px] text-muted-foreground">

        Recommended skills for this campaign — explicit run only, no auto-call.

      </p>



      {skillSuggestions.length ? (

        <div className="space-y-2">

          {skillSuggestions.slice(0, 5).map((suggestion) => (

            <div

              key={suggestion.skill_type}

              className="rounded border border-border/60 bg-background/40 p-2 text-[10px]"

            >

              <div className="flex flex-wrap items-start justify-between gap-2">

                <div>

                  <p className="font-medium text-foreground">{suggestion.label}</p>

                  <p className="mt-0.5 text-muted-foreground">{suggestion.reason}</p>

                </div>

                <Button

                  type="button"

                  size="sm"

                  variant="outline"

                  className="h-7 shrink-0 text-[10px]"

                  disabled={runMutation.isPending}

                  onClick={() => {

                    setPendingSkill(suggestion.skill_type);

                    runMutation.mutate(suggestion.skill_type);

                  }}

                >

                  {pendingSkill === suggestion.skill_type && runMutation.isPending

                    ? "Running…"

                    : "Run"}

                </Button>

              </div>

            </div>

          ))}

        </div>

      ) : null}



      {runError ? <p className="mt-2 text-[10px] text-destructive">{runError}</p> : null}



      {skillContext ? <SkillContextCards context={skillContext} /> : null}



      {runs.length ? (

        <div className="mt-2">

          <p className="mb-1 text-[10px] font-semibold text-muted-foreground">Latest runs</p>

          <div className="flex flex-wrap gap-1">

            {runs.slice(0, 5).map((run) => (

              <Button

                key={run.id}

                type="button"

                size="sm"

                variant={selectedRun?.id === run.id ? "default" : "ghost"}

                className="h-6 px-2 text-[9px]"

                onClick={() => setSelectedRunId(run.id)}

              >

                {run.skill_type.replace(/_/g, " ")}

              </Button>

            ))}

          </div>

          {selectedRun ? <OutputPreview run={selectedRun} /> : null}

        </div>

      ) : null}

    </div>

  );

}


