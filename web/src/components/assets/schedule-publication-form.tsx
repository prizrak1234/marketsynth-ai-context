"use client";

/**
 * Legacy publication scheduling — uses PublicationJob worker path.
 * Not wired to Content Factory foundation flow (PublicationPackageJob).
 */

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/providers/toast-provider";
import {
  createPublicationJob,
  fetchPublishingChannels,
} from "@/lib/api/endpoints/publishing";
import { invalidateAfterPublicationJobChange } from "@/lib/api/invalidate-after-publication-schedule";
import { queryKeys } from "@/lib/api/query-keys";
import { ApiError } from "@/lib/api/errors";
import {
  defaultFutureDatetimeLocal,
  localDatetimeInputToUtcIso,
  previewUtcFromLocalInput,
} from "@/lib/datetime";

type SchedulePublicationFormProps = {
  projectId: string;
  assetId: string;
  campaignId?: string | null;
  approvedVersionNumber: number;
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

export function SchedulePublicationForm({
  projectId,
  assetId,
  campaignId,
  approvedVersionNumber,
}: SchedulePublicationFormProps) {
  const [open, setOpen] = useState(false);
  const [channelId, setChannelId] = useState("");
  const [scheduledLocal, setScheduledLocal] = useState(defaultFutureDatetimeLocal);
  const [clientError, setClientError] = useState<string | null>(null);

  const queryClient = useQueryClient();
  const toast = useToast();

  const channelsQuery = useQuery({
    queryKey: [...queryKeys.publishingChannels(projectId), "active"],
    queryFn: () => fetchPublishingChannels(projectId, { includeArchived: false }),
    enabled: open,
  });

  const activeChannels =
    channelsQuery.data?.filter((channel) => channel.status === "active") ?? [];

  const scheduleMutation = useMutation({
    mutationFn: async () => {
      const scheduledAt = localDatetimeInputToUtcIso(scheduledLocal);
      if (!channelId) {
        throw new Error("Select a publishing channel");
      }
      return createPublicationJob(projectId, {
        asset_id: assetId,
        channel_id: channelId,
        scheduled_at: scheduledAt,
        ...(campaignId ? { campaign_id: campaignId } : {}),
      });
    },
    onSuccess: (job) => {
      toast.success(`Publication scheduled (${job.status})`);
      invalidateAfterPublicationJobChange(queryClient, projectId, {
        assetId,
        campaignId,
      });
      setOpen(false);
      setClientError(null);
    },
    onError: (error) => {
      const message = mutationErrorMessage(error);
      setClientError(message);
      toast.error(`Schedule failed: ${message}`);
    },
  });

  const utcPreview = previewUtcFromLocalInput(scheduledLocal);

  return (
    <div className="rounded-lg border border-border p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">Schedule publication</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Approved v{approvedVersionNumber} · future UTC time only · no
            immediate publish
          </p>
        </div>
        <Button
          variant={open ? "secondary" : "default"}
          size="sm"
          onClick={() => setOpen((value) => !value)}
        >
          {open ? "Hide form" : "Schedule publication"}
        </Button>
      </div>

      {open ? (
        <form
          className="mt-4 space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            setClientError(null);
            scheduleMutation.mutate();
          }}
        >
          {channelsQuery.isPending ? (
            <p className="text-sm text-muted-foreground">Loading channels…</p>
          ) : null}

          {channelsQuery.isError ? (
            <p className="text-sm text-destructive" role="alert">
              Failed to load channels: {mutationErrorMessage(channelsQuery.error)}
            </p>
          ) : null}

          {channelsQuery.isSuccess && activeChannels.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No active publishing channels.{" "}
              <Link href="/settings/channels" className="font-medium underline">
                Create a Telegram channel
              </Link>{" "}
              first.
            </p>
          ) : null}

          {activeChannels.length > 0 ? (
            <>
              <div className="space-y-1">
                <label htmlFor="schedule-channel" className="text-sm font-medium">
                  Channel
                </label>
                <select
                  id="schedule-channel"
                  required
                  value={channelId}
                  onChange={(event) => setChannelId(event.target.value)}
                  className="h-9 w-full max-w-md rounded-lg border border-border bg-background px-3 text-sm"
                  disabled={scheduleMutation.isPending}
                >
                  <option value="">Select channel…</option>
                  {activeChannels.map((channel) => (
                    <option key={channel.id} value={channel.id}>
                      {channel.name} ({channel.type})
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1">
                <label htmlFor="schedule-at" className="text-sm font-medium">
                  Scheduled at (your local time)
                </label>
                <input
                  id="schedule-at"
                  type="datetime-local"
                  required
                  value={scheduledLocal}
                  onChange={(event) => setScheduledLocal(event.target.value)}
                  className="h-9 w-full max-w-md rounded-lg border border-border bg-background px-3 text-sm"
                  disabled={scheduleMutation.isPending}
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

              <Button type="submit" disabled={scheduleMutation.isPending}>
                {scheduleMutation.isPending ? "Scheduling…" : "Submit schedule"}
              </Button>
            </>
          ) : null}
        </form>
      ) : null}
    </div>
  );
}
