"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { QueryStatus } from "@/components/data/query-status";
import { fetchDemoFlowStatus } from "@/lib/api/endpoints/demo-flow";
import { queryKeys } from "@/lib/api/query-keys";

type ChecklistItem = {
  key: string;
  label: string;
  done: boolean;
  detail?: string | null;
  href?: string;
};

function statusDone(value: string | null | undefined, ...accepted: string[]): boolean {
  if (!value) return false;
  return accepted.includes(value);
}

function buildItems(
  projectId: string,
  data: import("@/lib/api/types/demo-flow").DemoFlowStatus,
): ChecklistItem[] {
  const links = data.resource_links ?? {};
  const assetId = links.content_asset_id;

  return [
    {
      key: "plan",
      label: "Plan approved",
      done: statusDone(data.marketing_plan_status, "approved"),
      detail: data.marketing_plan_status,
      href: "/agents/chat",
    },
    {
      key: "run",
      label: "Execution run succeeded",
      done: statusDone(data.execution_run_status, "succeeded"),
      detail: data.execution_run_status,
      href: "/agents/chat",
    },
    {
      key: "copywriter",
      label: "Copywriter output approved",
      done: data.completed_specialists.includes("copywriter"),
      detail: data.completed_specialists.join(", ") || null,
      href: "/agents/chat",
    },
    {
      key: "asset",
      label: "Content asset approved",
      done: statusDone(data.content_asset_status, "approved"),
      detail: data.content_asset_status,
      href: assetId ? `/assets/${assetId}` : undefined,
    },
    {
      key: "brief",
      label: "Media brief approved",
      done: statusDone(data.media_brief_status, "approved"),
      detail: data.media_brief_status,
      href: assetId ? `/assets/${assetId}` : undefined,
    },
    {
      key: "media",
      label: "Media asset exists",
      done: data.media_asset_status != null,
      detail: data.media_asset_status,
      href: assetId ? `/assets/${assetId}` : undefined,
    },
    {
      key: "package",
      label: "Publication package approved",
      done: statusDone(data.publication_package_status, "approved"),
      detail: data.publication_package_status,
      href: assetId ? `/assets/${assetId}` : undefined,
    },
    {
      key: "job",
      label: "Publication job queued / scheduled / dry-run / real",
      done:
        statusDone(data.publication_job_status, "queued", "running", "dry_run_succeeded", "succeeded") ||
        statusDone(data.publication_schedule_status, "scheduled", "due", "dispatched"),
      detail: [data.publication_job_status, data.publication_schedule_status]
        .filter(Boolean)
        .join(" · "),
      href: assetId ? `/assets/${assetId}` : "/settings/channels",
    },
  ];
}

type E2eDemoFlowChecklistProps = {
  projectId: string;
};

export function E2eDemoFlowChecklist({ projectId }: E2eDemoFlowChecklistProps) {
  const query = useQuery({
    queryKey: queryKeys.demoFlowStatus(projectId),
    queryFn: () => fetchDemoFlowStatus(projectId),
    retry: false,
  });

  return (
    <section className="rounded-lg border border-border bg-card p-4">
      <div className="mb-3 flex flex-col gap-1">
        <h2 className="text-sm font-semibold">MVP demo flow</h2>
        <p className="text-xs text-muted-foreground">
          Read-only checklist across marketing → content → media → publish. Seed with{" "}
          <code className="rounded bg-muted px-1">uv run python scripts/seed_e2e_demo.py</code>
        </p>
      </div>
      <QueryStatus query={query} loadingVariant="text">
        {(data) => {
          const items = buildItems(projectId, data);
          return (
            <div className="flex flex-col gap-3">
              <ul className="flex flex-col gap-2">
                {items.map((item) => (
                  <li key={item.key} className="flex items-start gap-2 text-sm">
                    <span
                      className={
                        item.done
                          ? "mt-0.5 text-emerald-600"
                          : "mt-0.5 text-muted-foreground"
                      }
                      aria-hidden
                    >
                      {item.done ? "✓" : "○"}
                    </span>
                    <div className="flex flex-1 flex-col gap-0.5">
                      {item.href ? (
                        <Link href={item.href} className="font-medium hover:underline">
                          {item.label}
                        </Link>
                      ) : (
                        <span className="font-medium">{item.label}</span>
                      )}
                      {item.detail ? (
                        <span className="text-xs text-muted-foreground">{item.detail}</span>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ul>
              {data.failed_step ? (
                <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs">
                  <p className="font-medium text-amber-900 dark:text-amber-100">
                    Blocked at {data.failed_step}
                  </p>
                  {data.blocking_reason ? (
                    <p className="text-muted-foreground">{data.blocking_reason}</p>
                  ) : null}
                  {data.last_error_code ? (
                    <p className="font-mono text-muted-foreground">
                      code: {data.last_error_code}
                    </p>
                  ) : null}
                  {data.suggested_next_action ? (
                    <p className="mt-1 text-muted-foreground">
                      Suggested:{" "}
                      <span className="font-mono">{data.suggested_next_action}</span>
                    </p>
                  ) : null}
                </div>
              ) : null}
              {data.next_available_action ? (
                <p className="text-xs text-muted-foreground">
                  Next: <span className="font-mono">{data.next_available_action}</span>
                </p>
              ) : null}
            </div>
          );
        }}
      </QueryStatus>
    </section>
  );
}
