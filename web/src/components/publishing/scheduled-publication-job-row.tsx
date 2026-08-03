"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { JobStatusBadge } from "@/components/publishing/job-status-badge";
import { useToast } from "@/components/providers/toast-provider";
import {
  cancelPublicationJob,
  reschedulePublicationJob,
} from "@/lib/api/endpoints/publishing";
import { invalidateAfterPublicationJobChange } from "@/lib/api/invalidate-after-publication-schedule";
import { ApiError } from "@/lib/api/errors";
import type { PublicationJob } from "@/lib/api/types/publishing";
import { formatDateTime } from "@/lib/format";
import {
  localDatetimeInputToUtcIso,
  previewUtcFromLocalInput,
  utcIsoToDatetimeLocal,
} from "@/lib/datetime";

type ScheduledPublicationJobRowProps = {
  projectId: string;
  campaignId: string;
  job: PublicationJob;
  title: string;
};

function mutationErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Request failed";
}

export function ScheduledPublicationJobRow({
  projectId,
  campaignId,
  job,
  title,
}: ScheduledPublicationJobRowProps) {
  const [rescheduleOpen, setRescheduleOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [scheduledLocal, setScheduledLocal] = useState(() =>
    utcIsoToDatetimeLocal(job.scheduled_at),
  );
  const [clientError, setClientError] = useState<string | null>(null);

  const queryClient = useQueryClient();
  const toast = useToast();

  const onSettled = () => {
    invalidateAfterPublicationJobChange(queryClient, projectId, {
      campaignId,
      assetId: job.asset_id,
    });
  };

  const cancelMutation = useMutation({
    mutationFn: () => cancelPublicationJob(projectId, job.id),
    onSuccess: () => {
      toast.success("Publication job cancelled");
      onSettled();
      setCancelOpen(false);
    },
    onError: (error) => {
      toast.error(`Cancel failed: ${mutationErrorMessage(error)}`);
    },
  });

  const rescheduleMutation = useMutation({
    mutationFn: () =>
      reschedulePublicationJob(projectId, job.id, {
        scheduled_at: localDatetimeInputToUtcIso(scheduledLocal),
      }),
    onSuccess: () => {
      toast.success("Publication rescheduled");
      onSettled();
      setRescheduleOpen(false);
      setClientError(null);
    },
    onError: (error) => {
      const message = mutationErrorMessage(error);
      setClientError(message);
      toast.error(`Reschedule failed: ${message}`);
    },
  });

  const utcPreview = previewUtcFromLocalInput(scheduledLocal);
  const isPending = cancelMutation.isPending || rescheduleMutation.isPending;

  return (
    <li className="space-y-2 border-b border-border/50 pb-3 last:border-0">
      <div className="flex flex-wrap items-start justify-between gap-2 text-sm">
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
          <span className="ml-2">
            <JobStatusBadge status={job.status} />
          </span>
        </span>
        <span className="text-muted-foreground">
          {formatDateTime(job.scheduled_at)}
        </span>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={isPending}
          onClick={() => {
            setRescheduleOpen((open) => !open);
            setClientError(null);
            if (!rescheduleOpen) {
              setScheduledLocal(utcIsoToDatetimeLocal(job.scheduled_at));
            }
          }}
        >
          {rescheduleOpen ? "Hide reschedule" : "Reschedule"}
        </Button>
        <Button
          variant="destructive"
          size="sm"
          disabled={isPending}
          onClick={() => setCancelOpen(true)}
        >
          Cancel
        </Button>
      </div>

      {rescheduleOpen ? (
        <form
          className="rounded-md border border-border bg-muted/20 p-3 space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            setClientError(null);
            rescheduleMutation.mutate();
          }}
        >
          <div className="space-y-1">
            <label
              htmlFor={`reschedule-${job.id}`}
              className="text-xs font-medium"
            >
              New scheduled time (local)
            </label>
            <input
              id={`reschedule-${job.id}`}
              type="datetime-local"
              required
              value={scheduledLocal}
              onChange={(event) => setScheduledLocal(event.target.value)}
              className="h-9 w-full max-w-md rounded-lg border border-border bg-background px-3 text-sm"
              disabled={isPending}
            />
            {utcPreview ? (
              <p className="text-xs text-muted-foreground">
                Sent to API as UTC: <code>{utcPreview}</code>
              </p>
            ) : null}
          </div>
          {clientError ? (
            <p className="text-sm text-destructive" role="alert">
              {clientError}
            </p>
          ) : null}
          <Button type="submit" size="sm" disabled={isPending}>
            {rescheduleMutation.isPending ? "Saving…" : "Save new time"}
          </Button>
        </form>
      ) : null}

      <ConfirmDialog
        open={cancelOpen}
        title="Cancel scheduled publication?"
        description={`Cancel scheduled job for "${title}"? This does not publish or delete the asset.`}
        confirmLabel="Cancel job"
        destructive
        loading={cancelMutation.isPending}
        onCancel={() => {
          if (!cancelMutation.isPending) {
            setCancelOpen(false);
          }
        }}
        onConfirm={() => {
          cancelMutation.mutate();
        }}
      />
    </li>
  );
}
