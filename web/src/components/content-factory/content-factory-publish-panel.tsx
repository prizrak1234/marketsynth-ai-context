"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import {
  createPublicationPackageJob,
  executePublicationPackageJobDryRun,
  fetchPublicationPackageJobs,
  schedulePublicationPackageJob,
} from "@/lib/api/endpoints/publication-package-jobs";
import { fetchPublishingFoundationChannels } from "@/lib/api/endpoints/publishing-foundation-channels";
import { fetchPublicationPackage } from "@/lib/api/endpoints/publication-packages";
import { ApiError } from "@/lib/api/errors";
import {
  backendChannelForProduct,
  labelJobStatus,
  labelScheduleStatus,
  type ContentFactoryProductChannelId,
} from "@/lib/content-factory/labels";
import {
  defaultFutureDatetimeLocal,
  localDatetimeInputToUtcIso,
} from "@/lib/datetime";
import { useLocale } from "@/lib/i18n";

type ContentFactoryPublishPanelProps = {
  projectId: string;
  packageId: string | null;
  channelProductId: ContentFactoryProductChannelId;
};

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Request failed";
}

function previewTextFromJob(resultMetadata: Record<string, unknown> | undefined): string {
  if (!resultMetadata) return "";
  const preview = resultMetadata.preview;
  if (typeof preview === "string") return preview;
  const message = resultMetadata.message;
  if (typeof message === "string") return message;
  const dryRun = resultMetadata.dry_run;
  if (dryRun && typeof dryRun === "object") {
    const nested = (dryRun as Record<string, unknown>).preview;
    if (typeof nested === "string") return nested;
  }
  return JSON.stringify(resultMetadata, null, 2);
}

export function ContentFactoryPublishPanel({
  projectId,
  packageId,
  channelProductId,
}: ContentFactoryPublishPanelProps) {
  const { t, locale } = useLocale();
  const queryClient = useQueryClient();
  const backendChannel = backendChannelForProduct(channelProductId);
  const [scheduledLocal, setScheduledLocal] = useState(defaultFutureDatetimeLocal);
  const [selectedChannelId, setSelectedChannelId] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  const packageQuery = useQuery({
    queryKey: ["projects", projectId, "publication-package", packageId],
    queryFn: () => fetchPublicationPackage(projectId, packageId!),
    enabled: Boolean(packageId),
  });

  const channelsQuery = useQuery({
    queryKey: ["projects", projectId, "publishing-foundation-channels", backendChannel],
    queryFn: () =>
      fetchPublishingFoundationChannels(projectId, {
        channel_type: backendChannel,
        include_archived: false,
      }),
    enabled: Boolean(packageId),
  });

  const jobsQuery = useQuery({
    queryKey: ["projects", projectId, "publication-package-jobs", packageId],
    queryFn: () =>
      fetchPublicationPackageJobs(projectId, {
        publication_package_id: packageId ?? undefined,
      }),
    enabled: Boolean(packageId),
  });

  const activeJob = jobsQuery.data?.[0] ?? null;
  const activeFoundationChannels = useMemo(
    () => (channelsQuery.data ?? []).filter((row) => row.status === "active"),
    [channelsQuery.data],
  );
  const selectedChannel =
    activeFoundationChannels.find((row) => row.id === selectedChannelId) ??
    activeFoundationChannels[0] ??
    null;

  const invalidate = () => {
    void queryClient.invalidateQueries({
      queryKey: ["projects", projectId, "publication-package-jobs"],
    });
  };

  const createJobMutation = useMutation({
    mutationFn: () => {
      if (!packageId) throw new Error("package required");
      if (!selectedChannel) throw new Error("channel required");
      return createPublicationPackageJob(projectId, packageId, selectedChannel.id);
    },
    onSuccess: () => {
      invalidate();
      setActionError(null);
    },
    onError: (err) => setActionError(errorMessage(err)),
  });

  const dryRunMutation = useMutation({
    mutationFn: () => {
      if (!activeJob) throw new Error("job required");
      return executePublicationPackageJobDryRun(projectId, activeJob.id);
    },
    onSuccess: () => {
      invalidate();
      setActionError(null);
    },
    onError: (err) => setActionError(errorMessage(err)),
  });

  const scheduleMutation = useMutation({
    mutationFn: () => {
      if (!activeJob) throw new Error("job required");
      return schedulePublicationPackageJob(projectId, activeJob.id, {
        scheduled_for: localDatetimeInputToUtcIso(scheduledLocal),
      });
    },
    onSuccess: () => {
      invalidate();
      setActionError(null);
    },
    onError: (err) => setActionError(errorMessage(err)),
  });

  if (!packageId) {
    return (
      <section
        className="rounded-xl border p-4 text-sm text-muted-foreground"
        data-testid="content-factory-publish-empty"
      >
        {t("contentFactory.publish.createPackageFirst")}
      </section>
    );
  }

  if (packageQuery.isLoading) {
    return (
      <section className="rounded-xl border p-4 text-sm text-muted-foreground">
        {t("common.loading")}
      </section>
    );
  }

  if (packageQuery.data?.status !== "approved") {
    return (
      <section
        className="rounded-xl border p-4 text-sm text-muted-foreground"
        data-testid="content-factory-publish-not-approved"
      >
        {t("contentFactory.publish.packageMustBeApproved")}
      </section>
    );
  }

  const previewText = previewTextFromJob(activeJob?.result_metadata);
  const dryRunDone =
    activeJob?.status === "dry_run_succeeded" ||
    activeJob?.status === "succeeded" ||
    Boolean(activeJob?.result_metadata?.dry_run);
  const canSchedule =
    activeJob?.status === "queued" &&
    activeJob.schedule_status !== "scheduled" &&
    activeJob.schedule_status !== "due";
  const isScheduled =
    activeJob?.schedule_status === "scheduled" ||
    activeJob?.schedule_status === "due";

  return (
    <section
      className="rounded-xl border p-4"
      style={{
        borderColor: "var(--ms-border-default)",
        background: "var(--ms-bg-surface)",
      }}
      data-testid="content-factory-publish-panel"
    >
      <h2 className="text-sm font-semibold">{t("contentFactory.publishLabel")}</h2>
      <p className="mt-1 text-xs text-muted-foreground">{t("contentFactory.publish.hint")}</p>

      <div className="mt-4 space-y-3">
        {!activeJob ? (
          <>
            {activeFoundationChannels.length === 0 ? (
              <p
                className="rounded-md border px-3 py-2 text-xs text-muted-foreground"
                data-testid="content-factory-channel-missing"
              >
                {t("contentFactory.publish.noActiveChannel")}
              </p>
            ) : (
              <label className="block text-xs font-medium">
                {t("contentFactory.field.foundationChannel")}
                <select
                  className="mt-1 block w-full rounded-md border px-3 py-2 text-sm"
                  style={{ borderColor: "var(--ms-border-default)" }}
                  value={selectedChannel?.id ?? ""}
                  onChange={(e) => setSelectedChannelId(e.target.value)}
                  data-testid="content-factory-channel-select"
                >
                  {activeFoundationChannels.map((channel) => (
                    <option key={channel.id} value={channel.id}>
                      {channel.name}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <Button
              type="button"
              size="sm"
              disabled={createJobMutation.isPending || !selectedChannel}
              onClick={() => createJobMutation.mutate()}
              data-testid="content-factory-create-job"
            >
              {t("contentFactory.action.createPublishTask")}
            </Button>
          </>
        ) : (
          <>
            <div className="text-xs text-muted-foreground">
              <p>{t("contentFactory.publishTaskLabel")}</p>
              <p className="mt-1 font-medium text-foreground">
                {labelJobStatus(locale, activeJob.status)}
              </p>
              <p className="mt-1">
                {t("contentFactory.scheduleLabel")}:{" "}
                {labelScheduleStatus(locale, activeJob.schedule_status)}
              </p>
            </div>

            {canSchedule ? (
              <div className="space-y-2">
                <label className="block text-xs font-medium">
                  {t("contentFactory.field.scheduleAt")}
                  <input
                    type="datetime-local"
                    className="mt-1 block rounded-md border px-3 py-2 text-sm"
                    style={{ borderColor: "var(--ms-border-default)" }}
                    value={scheduledLocal}
                    onChange={(e) => setScheduledLocal(e.target.value)}
                    data-testid="content-factory-schedule-input"
                  />
                </label>
                <Button
                  type="button"
                  size="sm"
                  disabled={scheduleMutation.isPending}
                  onClick={() => scheduleMutation.mutate()}
                  data-testid="content-factory-schedule"
                >
                  {t("contentFactory.action.schedulePublish")}
                </Button>
              </div>
            ) : null}

            {!dryRunDone ? (
              <Button
                type="button"
                size="sm"
                disabled={dryRunMutation.isPending}
                onClick={() => dryRunMutation.mutate()}
                data-testid="content-factory-execute-dry-run"
              >
                {t("contentFactory.action.createPreview")}
              </Button>
            ) : (
              <div
                className="rounded-lg border p-3 text-sm"
                style={{ borderColor: "var(--ms-border-default)" }}
                data-testid="content-factory-dry-run-preview"
              >
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  {t("contentFactory.previewLabel")}
                </p>
                <pre className="mt-2 whitespace-pre-wrap text-xs">{previewText || t("contentFactory.publish.previewReady")}</pre>
              </div>
            )}

            {isScheduled ? (
              <p
                className="text-xs text-muted-foreground"
                data-testid="content-factory-scheduled-status"
              >
                {t("contentFactory.publish.scheduledReadiness", {
                  at: activeJob.scheduled_for ?? "—",
                })}
              </p>
            ) : null}
          </>
        )}

        <p
          className="rounded-md border px-3 py-2 text-xs"
          style={{
            borderColor: "var(--ms-border-default)",
            color: "var(--ms-text-secondary)",
          }}
          data-testid="content-factory-real-publish-blocked"
        >
          {t("contentFactory.publish.realPublishUnavailable")}
        </p>
      </div>

      {actionError ? (
        <p className="mt-2 text-xs text-destructive">{actionError}</p>
      ) : null}
      {(createJobMutation.error || dryRunMutation.error || scheduleMutation.error) &&
      !actionError ? (
        <p className="mt-2 text-xs text-destructive">
          {errorMessage(
            createJobMutation.error ?? dryRunMutation.error ?? scheduleMutation.error,
          )}
        </p>
      ) : null}
    </section>
  );
}
