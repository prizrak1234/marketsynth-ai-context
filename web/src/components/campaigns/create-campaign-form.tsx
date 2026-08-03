"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/providers/toast-provider";
import { createCampaign } from "@/lib/api/endpoints/campaigns";
import { invalidateAfterCampaignChange } from "@/lib/api/invalidate-after-campaign-change";
import { ApiError } from "@/lib/api/errors";
import type { EditableCampaignStatus } from "@/lib/api/types/campaigns";
import {
  assertEndAfterStart,
  optionalLocalDatetimeToUtcIso,
  previewUtcFromLocalInput,
} from "@/lib/datetime";

type CreateCampaignFormProps = {
  projectId: string;
};

const STATUS_OPTIONS: EditableCampaignStatus[] = [
  "draft",
  "active",
  "paused",
  "completed",
];

function mutationErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Request failed";
}

export function CreateCampaignForm({ projectId }: CreateCampaignFormProps) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState<EditableCampaignStatus>("draft");
  const [startLocal, setStartLocal] = useState("");
  const [endLocal, setEndLocal] = useState("");
  const [clientError, setClientError] = useState<string | null>(null);

  const queryClient = useQueryClient();
  const toast = useToast();
  const router = useRouter();

  const createMutation = useMutation({
    mutationFn: async () => {
      const startAt = optionalLocalDatetimeToUtcIso(startLocal);
      const endAt = optionalLocalDatetimeToUtcIso(endLocal);
      assertEndAfterStart(startAt, endAt);
      return createCampaign(projectId, {
        title: title.trim(),
        description: description.trim() ? description.trim() : null,
        status,
        start_at: startAt,
        end_at: endAt,
      });
    },
    onSuccess: (campaign) => {
      toast.success("Campaign created");
      invalidateAfterCampaignChange(queryClient, projectId);
      setOpen(false);
      setClientError(null);
      router.push(`/campaigns/${campaign.id}`);
    },
    onError: (error) => {
      const message = mutationErrorMessage(error);
      setClientError(message);
      toast.error(`Create failed: ${message}`);
    },
  });

  return (
    <div className="rounded-lg border border-border p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-semibold">Create campaign</h2>
        <Button
          variant={open ? "secondary" : "default"}
          size="sm"
          onClick={() => setOpen((value) => !value)}
        >
          {open ? "Hide form" : "New campaign"}
        </Button>
      </div>

      {open ? (
        <form
          className="mt-4 grid max-w-lg gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            setClientError(null);
            if (!title.trim()) {
              setClientError("Title is required");
              return;
            }
            createMutation.mutate();
          }}
        >
          <div className="space-y-1">
            <label htmlFor="create-title" className="text-sm font-medium">
              Title
            </label>
            <input
              id="create-title"
              required
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Summer Telegram campaign"
              className="h-9 w-full rounded-lg border border-border bg-background px-3 text-sm"
              disabled={createMutation.isPending}
            />
          </div>

          <div className="space-y-1">
            <label htmlFor="create-description" className="text-sm font-medium">
              Description
            </label>
            <textarea
              id="create-description"
              rows={3}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              disabled={createMutation.isPending}
            />
          </div>

          <div className="space-y-1">
            <label htmlFor="create-status" className="text-sm font-medium">
              Status
            </label>
            <select
              id="create-status"
              value={status}
              onChange={(event) =>
                setStatus(event.target.value as EditableCampaignStatus)
              }
              className="h-9 w-full rounded-lg border border-border bg-background px-3 text-sm"
              disabled={createMutation.isPending}
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
              <label htmlFor="create-start" className="text-sm font-medium">
                start_at (local)
              </label>
              <input
                id="create-start"
                type="datetime-local"
                value={startLocal}
                onChange={(event) => setStartLocal(event.target.value)}
                className="h-9 w-full rounded-lg border border-border bg-background px-3 text-sm"
                disabled={createMutation.isPending}
              />
              {startLocal ? (
                <p className="text-xs text-muted-foreground">
                  UTC: {previewUtcFromLocalInput(startLocal) ?? "—"}
                </p>
              ) : null}
            </div>
            <div className="space-y-1">
              <label htmlFor="create-end" className="text-sm font-medium">
                end_at (local)
              </label>
              <input
                id="create-end"
                type="datetime-local"
                value={endLocal}
                onChange={(event) => setEndLocal(event.target.value)}
                className="h-9 w-full rounded-lg border border-border bg-background px-3 text-sm"
                disabled={createMutation.isPending}
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

          <Button type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending ? "Creating…" : "Create campaign"}
          </Button>
        </form>
      ) : null}
    </div>
  );
}
