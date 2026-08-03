"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiKeyMissing } from "@/components/data/config-missing";
import { QueryStatus } from "@/components/data/query-status";
import { PageHeader } from "@/components/layout/page-header";
import {
  fetchBetaAdminFeedback,
  fetchBetaQaExport,
  resolveBetaAdminFeedback,
  triageBetaAdminFeedback,
} from "@/lib/api/endpoints/beta-feedback";
import { queryKeys } from "@/lib/api/query-keys";
import { useEnvConfig } from "@/lib/hooks/use-env-config";
import { formatDateTime } from "@/lib/format";

export function BetaQaView() {
  const { hasApiKey } = useEnvConfig();
  const queryClient = useQueryClient();

  const feedbackQuery = useQuery({
    queryKey: queryKeys.betaAdminFeedback,
    queryFn: fetchBetaAdminFeedback,
    enabled: hasApiKey,
    retry: false,
  });

  const exportQuery = useQuery({
    queryKey: queryKeys.betaQaExport,
    queryFn: fetchBetaQaExport,
    enabled: hasApiKey,
    retry: false,
  });

  const triageMutation = useMutation({
    mutationFn: triageBetaAdminFeedback,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.betaAdminFeedback });
      void queryClient.invalidateQueries({ queryKey: queryKeys.betaQaExport });
    },
  });

  const resolveMutation = useMutation({
    mutationFn: resolveBetaAdminFeedback,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.betaAdminFeedback });
      void queryClient.invalidateQueries({ queryKey: queryKeys.betaQaExport });
    },
  });

  if (!hasApiKey) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader title="Beta QA" description="Feedback triage and safe export" />
        <ApiKeyMissing />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Beta QA"
        description="Closed-beta diagnostics — no support ticketing"
      />

      <QueryStatus query={exportQuery} loadingVariant="card">
        {(data) => (
          <div className="grid gap-3 rounded-lg border border-border bg-card p-4 text-sm sm:grid-cols-3">
            <div>
              <p className="text-xs text-muted-foreground">Demo projects</p>
              <p className="font-medium">{data.demo_completion.demo_projects_total}</p>
              <p className="text-xs text-muted-foreground">
                Queued: {data.demo_completion.publication_queued_count} · Blocked:{" "}
                {data.demo_completion.with_failed_step_count}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Feedback open / blocker</p>
              <p className="font-medium">
                {data.feedback_counts.open} open · {data.feedback_counts.blocker} blocker
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Failed jobs (24h)</p>
              <p className="font-medium">
                pkg {data.failed_jobs.failed_package_jobs} · gen{" "}
                {data.failed_jobs.failed_generation_jobs}
              </p>
            </div>
            <p className="text-xs text-muted-foreground sm:col-span-3">
              Export at {formatDateTime(data.generated_at)} — no content bodies or secrets
            </p>
          </div>
        )}
      </QueryStatus>

      <section className="rounded-lg border border-border bg-card">
        <div className="border-b border-border px-4 py-3">
          <h2 className="text-sm font-semibold">Feedback reports</h2>
        </div>
        <QueryStatus query={feedbackQuery} loadingVariant="text">
          {(rows) =>
            rows.length === 0 ? (
              <p className="px-4 py-6 text-sm text-muted-foreground">No feedback yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-border text-xs text-muted-foreground">
                    <tr>
                      <th className="px-4 py-2">Title</th>
                      <th className="px-4 py-2">Source</th>
                      <th className="px-4 py-2">Severity</th>
                      <th className="px-4 py-2">Status</th>
                      <th className="px-4 py-2">Created</th>
                      <th className="px-4 py-2">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row) => (
                      <tr key={row.id} className="border-b border-border/60">
                        <td className="px-4 py-2 font-medium">{row.title}</td>
                        <td className="px-4 py-2">{row.source}</td>
                        <td className="px-4 py-2">{row.severity}</td>
                        <td className="px-4 py-2">{row.status}</td>
                        <td className="px-4 py-2 text-xs text-muted-foreground">
                          {formatDateTime(row.created_at)}
                        </td>
                        <td className="px-4 py-2">
                          <div className="flex gap-2">
                            {row.status === "open" ? (
                              <button
                                type="button"
                                className="text-xs underline"
                                disabled={triageMutation.isPending}
                                onClick={() => triageMutation.mutate(row.id)}
                              >
                                Triage
                              </button>
                            ) : null}
                            {row.status !== "resolved" && row.status !== "archived" ? (
                              <button
                                type="button"
                                className="text-xs underline"
                                disabled={resolveMutation.isPending}
                                onClick={() => resolveMutation.mutate(row.id)}
                              >
                                Resolve
                              </button>
                            ) : null}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          }
        </QueryStatus>
      </section>
    </div>
  );
}
