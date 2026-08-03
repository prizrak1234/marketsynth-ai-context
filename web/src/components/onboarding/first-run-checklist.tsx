"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { QueryStatus } from "@/components/data/query-status";
import {
  completeOnboardingStep,
  fetchOnboardingStatus,
} from "@/lib/api/endpoints/onboarding";
import { queryKeys } from "@/lib/api/query-keys";

const STEP_LABELS: Record<string, string> = {
  project_created: "Project created",
  agents_seeded: "Agents seeded",
  demo_seeded: "E2E demo seeded",
  first_chat_done: "First chat message sent",
  first_asset_created: "First content asset created",
  first_publication_job_created: "First publication job created",
};

type FirstRunChecklistProps = {
  projectId: string;
};

export function FirstRunChecklist({ projectId }: FirstRunChecklistProps) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: queryKeys.onboarding(projectId),
    queryFn: () => fetchOnboardingStatus(projectId),
  });

  const completeMutation = useMutation({
    mutationFn: () => completeOnboardingStep("demo_seeded"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.onboarding(projectId) });
    },
  });

  return (
    <section className="rounded-lg border border-border bg-card p-4">
      <div className="mb-3 flex flex-col gap-1">
        <h2 className="text-sm font-semibold">First-run onboarding</h2>
        <p className="text-xs text-muted-foreground">
          Progress is derived from your workspace. Mark demo seeded after running the seed script.
        </p>
      </div>
      <QueryStatus query={query} loadingVariant="text">
        {(data) => (
          <div className="flex flex-col gap-3">
            <p className="text-xs text-muted-foreground">
              {data.completed_count} / {data.total_count} complete
            </p>
            <ul className="flex flex-col gap-2">
              {data.steps.map((item) => (
                <li key={item.step} className="flex items-start gap-2 text-sm">
                  <span
                    className={
                      item.completed ? "text-emerald-600" : "text-muted-foreground"
                    }
                    aria-hidden
                  >
                    {item.completed ? "✓" : "○"}
                  </span>
                  <div className="flex flex-1 flex-col gap-1">
                    <span className="font-medium">
                      {STEP_LABELS[item.step] ?? item.step}
                    </span>
                    {item.step === "demo_seeded" && item.manual_allowed && !item.completed ? (
                      <button
                        type="button"
                        className="w-fit text-xs text-primary underline"
                        disabled={completeMutation.isPending}
                        onClick={() => completeMutation.mutate()}
                      >
                        Mark demo seeded
                      </button>
                    ) : null}
                    {item.step === "first_chat_done" ? (
                      <Link href="/agents/chat" className="text-xs text-primary underline">
                        Open agent chat
                      </Link>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </QueryStatus>
    </section>
  );
}
