"use client";

import Link from "next/link";
import { JobStatusBadge } from "@/components/publishing/job-status-badge";
import { ScheduledPublicationJobRow } from "@/components/publishing/scheduled-publication-job-row";
import type { PublicationJob } from "@/lib/api/types/publishing";
import { formatDateTime } from "@/lib/format";

const DISPLAY_STATUSES = [
  "scheduled",
  "queued",
  "running",
  "succeeded",
  "failed",
  "cancelled",
] as const;

function jobTitle(job: PublicationJob): string {
  const preview = job.payload_preview;
  if (
    typeof preview === "object" &&
    preview !== null &&
    "asset_title" in preview &&
    typeof preview.asset_title === "string"
  ) {
    return preview.asset_title;
  }
  return job.asset_id.slice(0, 8);
}

function jobWhen(job: PublicationJob): string {
  return formatDateTime(
    job.scheduled_at ?? job.queued_at ?? job.started_at ?? job.created_at,
  );
}

type PublicationJobsListProps = {
  projectId: string;
  campaignId: string;
  jobs: PublicationJob[];
};

export function PublicationJobsList({
  projectId,
  campaignId,
  jobs,
}: PublicationJobsListProps) {
  const byStatus = DISPLAY_STATUSES.map((status) => ({
    status,
    items: jobs.filter((job) => job.status === status),
  })).filter((group) => group.items.length > 0);

  if (jobs.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      {byStatus.map((group) => (
        <div key={group.status}>
          <div className="mb-2 flex items-center gap-2">
            <JobStatusBadge status={group.status} />
            <span className="text-xs text-muted-foreground">
              {group.items.length} job{group.items.length === 1 ? "" : "s"}
            </span>
          </div>
          <ul className="space-y-2 text-sm">
            {group.items.map((job) => {
              const title = jobTitle(job);
              if (job.status === "scheduled") {
                return (
                  <ScheduledPublicationJobRow
                    key={job.id}
                    projectId={projectId}
                    campaignId={campaignId}
                    job={job}
                    title={title}
                  />
                );
              }
              return (
                <li
                  key={job.id}
                  className="flex flex-wrap items-baseline justify-between gap-2 border-b border-border/50 pb-2 last:border-0"
                >
                  <span>
                    <Link
                      href={`/assets/${job.asset_id}`}
                      className="font-medium hover:underline"
                    >
                      {title}
                    </Link>
                    <span className="ml-2 text-muted-foreground">
                      v{job.asset_version_number}
                    </span>
                    {job.error ? (
                      <span className="ml-2 text-destructive">· {job.error}</span>
                    ) : null}
                  </span>
                  <span className="text-muted-foreground">{jobWhen(job)}</span>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </div>
  );
}
