"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ApiKeyMissing,
  ProjectIdMissing,
} from "@/components/data/config-missing";
import { QueryStatus } from "@/components/data/query-status";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/layout/page-header";
import { CreateTelegramChannelForm } from "@/components/settings/create-telegram-channel-form";
import { PublishingChannelsTable } from "@/components/settings/publishing-channels-table";
import { fetchPublishingChannels } from "@/lib/api/endpoints/publishing";
import { queryKeys } from "@/lib/api/query-keys";
import { useEnvConfig } from "@/lib/hooks/use-env-config";

export function ChannelsSettingsView() {
  const { hasApiKey, hasProjectId, projectId, isProjectScopeReady } =
    useEnvConfig();

  const channelsQuery = useQuery({
    queryKey: [...queryKeys.publishingChannels(projectId ?? ""), "all"],
    queryFn: () =>
      fetchPublishingChannels(projectId!, { includeArchived: true }),
    enabled: isProjectScopeReady,
  });

  if (!hasApiKey) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader title="Publishing channels" />
        <ApiKeyMissing />
      </div>
    );
  }

  if (!hasProjectId) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader title="Publishing channels" />
        <ProjectIdMissing />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Publishing channels"
        description="Manage Telegram destinations for scheduled publication. No test-send or publish from this screen."
      />

      <div id="create-telegram-channel">
        <CreateTelegramChannelForm projectId={projectId!} />
      </div>

      <QueryStatus
        query={channelsQuery}
        loadingVariant="table"
        loadingLines={3}
        empty={
          channelsQuery.isSuccess && (channelsQuery.data?.length ?? 0) === 0
        }
        emptyTitle="No channels yet"
        emptyDescription="Create a Telegram channel to use when scheduling approved assets."
        emptyAction={
          <Button
            type="button"
            onClick={() => {
              document
                .getElementById("create-telegram-channel")
                ?.scrollIntoView({ behavior: "smooth" });
            }}
          >
            Create Telegram channel
          </Button>
        }
      >
        {(channels) => (
          <PublishingChannelsTable projectId={projectId!} channels={channels} />
        )}
      </QueryStatus>
    </div>
  );
}
