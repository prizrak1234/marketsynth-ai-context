"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { ChannelStatusBadge } from "@/components/publishing/channel-status-badge";
import { useToast } from "@/components/providers/toast-provider";
import {
  archivePublishingChannel,
  updatePublishingChannel,
} from "@/lib/api/endpoints/publishing";
import { invalidateAfterPublishingChannelChange } from "@/lib/api/invalidate-after-channel-change";
import { ApiError } from "@/lib/api/errors";
import type { PublishingChannel } from "@/lib/api/types/publishing";
import { formatDateTime } from "@/lib/format";

type PublishingChannelsTableProps = {
  projectId: string;
  channels: PublishingChannel[];
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

function configSummary(channel: PublishingChannel): string {
  const preview = channel.config_preview;
  const chatId =
    typeof preview.chat_id === "string" ? preview.chat_id : "—";
  const parseMode =
    typeof preview.parse_mode === "string" ? preview.parse_mode : "—";
  return `chat_id ${chatId} · ${parseMode}`;
}

export function PublishingChannelsTable({
  projectId,
  channels,
}: PublishingChannelsTableProps) {
  const [archiveTarget, setArchiveTarget] = useState<PublishingChannel | null>(
    null,
  );
  const queryClient = useQueryClient();
  const toast = useToast();

  const statusMutation = useMutation({
    mutationFn: ({
      channelId,
      status,
    }: {
      channelId: string;
      status: "active" | "paused" | "archived";
    }) => updatePublishingChannel(projectId, channelId, { status }),
    onSuccess: (_data, variables) => {
      toast.success(`Channel ${variables.status}`);
      invalidateAfterPublishingChannelChange(queryClient, projectId);
    },
    onError: (error) => {
      toast.error(mutationErrorMessage(error));
    },
  });

  const archiveMutation = useMutation({
    mutationFn: (channelId: string) => archivePublishingChannel(projectId, channelId),
    onSuccess: async () => {
      toast.success("Channel archived");
      invalidateAfterPublishingChannelChange(queryClient, projectId);
      setArchiveTarget(null);
    },
    onError: (error) => {
      toast.error(`Archive failed: ${mutationErrorMessage(error)}`);
    },
  });

  const isPending = statusMutation.isPending || archiveMutation.isPending;

  return (
    <>
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full min-w-[900px] text-left text-sm">
          <thead className="border-b border-border bg-muted/40 text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Type</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Config</th>
              <th className="px-4 py-3 font-medium">Created</th>
              <th className="px-4 py-3 font-medium">Updated</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {channels.map((channel) => (
              <tr key={channel.id} className="border-b border-border/60">
                <td className="px-4 py-3 font-medium">{channel.name}</td>
                <td className="px-4 py-3">{channel.type}</td>
                <td className="px-4 py-3">
                  <ChannelStatusBadge status={channel.status} />
                </td>
                <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                  {configSummary(channel)}
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {formatDateTime(channel.created_at)}
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {formatDateTime(channel.updated_at)}
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap justify-end gap-2">
                    {channel.status === "paused" || channel.status === "archived" ? (
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={isPending}
                        onClick={() =>
                          statusMutation.mutate({
                            channelId: channel.id,
                            status: "active",
                          })
                        }
                      >
                        Activate
                      </Button>
                    ) : null}
                    {channel.status === "active" ? (
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={isPending}
                        onClick={() =>
                          statusMutation.mutate({
                            channelId: channel.id,
                            status: "paused",
                          })
                        }
                      >
                        Pause
                      </Button>
                    ) : null}
                    {channel.status !== "archived" ? (
                      <Button
                        variant="destructive"
                        size="sm"
                        disabled={isPending}
                        onClick={() => setArchiveTarget(channel)}
                      >
                        Archive
                      </Button>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ConfirmDialog
        open={archiveTarget !== null}
        title="Archive channel?"
        description={
          archiveTarget
            ? `"${archiveTarget.name}" will be archived. Existing scheduled jobs are not cancelled from this screen.`
            : ""
        }
        confirmLabel="Archive"
        destructive
        loading={archiveMutation.isPending}
        onCancel={() => {
          if (!archiveMutation.isPending) {
            setArchiveTarget(null);
          }
        }}
        onConfirm={() => {
          if (archiveTarget) {
            archiveMutation.mutate(archiveTarget.id);
          }
        }}
      />
    </>
  );
}
