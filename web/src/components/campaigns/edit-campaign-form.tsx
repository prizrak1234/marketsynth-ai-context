"use client";

import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/providers/toast-provider";
import { updateCampaign } from "@/lib/api/endpoints/campaigns";
import { invalidateAfterCampaignChange } from "@/lib/api/invalidate-after-campaign-change";
import { ApiError } from "@/lib/api/errors";
import type {
  EditableCampaignStatus,
  MarketingCampaign,
} from "@/lib/api/types/campaigns";
import {
  assertEndAfterStart,
  optionalLocalDatetimeToUtcIso,
  previewUtcFromLocalInput,
  utcIsoToDatetimeLocal,
} from "@/lib/datetime";

const STATUS_OPTIONS: EditableCampaignStatus[] = [
  "draft",
  "active",
  "paused",
  "completed",
];

type EditCampaignFormProps = {
  projectId: string;
  campaign: MarketingCampaign;
  onClose: () => void;
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

export function EditCampaignForm({
  projectId,
  campaign,
  onClose,
}: EditCampaignFormProps) {
  const [title, setTitle] = useState(campaign.title);
  const [description, setDescription] = useState(campaign.description ?? "");
  const [status, setStatus] = useState<EditableCampaignStatus>(
    campaign.status as EditableCampaignStatus,
  );
  const [startLocal, setStartLocal] = useState(
    campaign.start_at ? utcIsoToDatetimeLocal(campaign.start_at) : "",
  );
  const [endLocal, setEndLocal] = useState(
    campaign.end_at ? utcIsoToDatetimeLocal(campaign.end_at) : "",
  );
  const [clientError, setClientError] = useState<string | null>(null);

  const queryClient = useQueryClient();
  const toast = useToast();

  useEffect(() => {
    setTitle(campaign.title);
    setDescription(campaign.description ?? "");
    setStatus(campaign.status as EditableCampaignStatus);
    setStartLocal(
      campaign.start_at ? utcIsoToDatetimeLocal(campaign.start_at) : "",
    );
    setEndLocal(campaign.end_at ? utcIsoToDatetimeLocal(campaign.end_at) : "");
  }, [campaign]);

  const updateMutation = useMutation({
    mutationFn: async () => {
      const startAt = optionalLocalDatetimeToUtcIso(startLocal);
      const endAt = optionalLocalDatetimeToUtcIso(endLocal);
      assertEndAfterStart(startAt, endAt);
      return updateCampaign(projectId, campaign.id, {
        title: title.trim(),
        description: description.trim() ? description.trim() : null,
        status,
        start_at: startAt,
        end_at: endAt,
      });
    },
    onSuccess: () => {
      toast.success("Campaign updated");
      invalidateAfterCampaignChange(queryClient, projectId, campaign.id);
      onClose();
    },
    onError: (error) => {
      const message = mutationErrorMessage(error);
      setClientError(message);
      toast.error(`Update failed: ${message}`);
    },
  });

  if (campaign.status === "archived") {
    return (
      <p className="text-sm text-muted-foreground">
        Archived campaigns cannot be edited.
      </p>
    );
  }

  return (
    <form
      className="grid max-w-lg gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        setClientError(null);
        if (!title.trim()) {
          setClientError("Title is required");
          return;
        }
        updateMutation.mutate();
      }}
    >
      <div className="space-y-1">
        <label htmlFor="edit-title" className="text-sm font-medium">
          Title
        </label>
        <input
          id="edit-title"
          required
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          className="h-9 w-full rounded-lg border border-border bg-background px-3 text-sm"
          disabled={updateMutation.isPending}
        />
      </div>

      <div className="space-y-1">
        <label htmlFor="edit-description" className="text-sm font-medium">
          Description
        </label>
        <textarea
          id="edit-description"
          rows={3}
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
          disabled={updateMutation.isPending}
        />
      </div>

      <div className="space-y-1">
        <label htmlFor="edit-status" className="text-sm font-medium">
          Status
        </label>
        <select
          id="edit-status"
          value={status}
          onChange={(event) =>
            setStatus(event.target.value as EditableCampaignStatus)
          }
          className="h-9 w-full rounded-lg border border-border bg-background px-3 text-sm"
          disabled={updateMutation.isPending}
        >
          {STATUS_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1">
          <label htmlFor="edit-start" className="text-sm font-medium">
            start_at (local)
          </label>
          <input
            id="edit-start"
            type="datetime-local"
            value={startLocal}
            onChange={(event) => setStartLocal(event.target.value)}
            className="h-9 w-full rounded-lg border border-border bg-background px-3 text-sm"
            disabled={updateMutation.isPending}
          />
          {startLocal ? (
            <p className="text-xs text-muted-foreground">
              UTC: {previewUtcFromLocalInput(startLocal) ?? "—"}
            </p>
          ) : null}
        </div>
        <div className="space-y-1">
          <label htmlFor="edit-end" className="text-sm font-medium">
            end_at (local)
          </label>
          <input
            id="edit-end"
            type="datetime-local"
            value={endLocal}
            onChange={(event) => setEndLocal(event.target.value)}
            className="h-9 w-full rounded-lg border border-border bg-background px-3 text-sm"
            disabled={updateMutation.isPending}
          />
          {endLocal ? (
            <p className="text-xs text-muted-foreground">
              UTC: {previewUtcFromLocalInput(endLocal) ?? "—"}
            </p>
          ) : null}
        </div>
      </div>

      {clientError ? (
        <p className="text-sm text-destructive" role="alert">
          {clientError}
        </p>
      ) : null}

      <div className="flex gap-2">
        <Button type="submit" disabled={updateMutation.isPending}>
          {updateMutation.isPending ? "Saving…" : "Save changes"}
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={updateMutation.isPending}
          onClick={onClose}
        >
          Cancel
        </Button>
      </div>
    </form>
  );
}
