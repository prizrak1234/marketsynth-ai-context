"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/providers/toast-provider";
import { createCampaignPlanDraft } from "@/lib/api/endpoints/plan-drafts";
import { invalidateAfterPlanDraftChange } from "@/lib/api/invalidate-after-plan-draft-generate";
import { ApiError } from "@/lib/api/errors";
import {
  buildPlanPayloadFromForm,
  emptyContentItem,
  type ContentItemFormState,
} from "@/lib/plan-drafts/build-payload";
import { previewUtcFromLocalInput } from "@/lib/datetime";

type CreatePlanDraftFormProps = {
  projectId: string;
  campaignId: string;
  onCreated: (draftId: string) => void;
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

export function CreatePlanDraftForm({
  projectId,
  campaignId,
  onCreated,
}: CreatePlanDraftFormProps) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("Telegram launch plan");
  const [goal, setGoal] = useState("");
  const [targetAudience, setTargetAudience] = useState("");
  const [keyMessage, setKeyMessage] = useState("");
  const [contentItems, setContentItems] = useState<ContentItemFormState[]>([
    emptyContentItem(),
  ]);
  const [clientError, setClientError] = useState<string | null>(null);

  const queryClient = useQueryClient();
  const toast = useToast();

  const createMutation = useMutation({
    mutationFn: async () => {
      const plan_payload = buildPlanPayloadFromForm({
        goal,
        targetAudience,
        keyMessage,
        contentItems,
      });
      return createCampaignPlanDraft(projectId, campaignId, {
        title: title.trim(),
        plan_payload,
      });
    },
    onSuccess: (draft) => {
      toast.success("Plan draft created");
      invalidateAfterPlanDraftChange(queryClient, projectId, campaignId, draft.id);
      onCreated(draft.id);
      setOpen(false);
      setClientError(null);
    },
    onError: (error) => {
      const message = mutationErrorMessage(error);
      setClientError(message);
      toast.error(`Create failed: ${message}`);
    },
  });

  const updateItem = (
    index: number,
    patch: Partial<ContentItemFormState>,
  ) => {
    setContentItems((items) =>
      items.map((item, i) => (i === index ? { ...item, ...patch } : item)),
    );
  };

  return (
    <div className="rounded-lg border border-dashed border-border p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm font-medium">Create plan draft</p>
        <Button
          variant={open ? "secondary" : "outline"}
          size="sm"
          onClick={() => setOpen((value) => !value)}
        >
          {open ? "Hide form" : "New plan draft"}
        </Button>
      </div>

      {open ? (
        <form
          className="mt-4 space-y-4"
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
            <label htmlFor="plan-title" className="text-sm font-medium">
              Title
            </label>
            <input
              id="plan-title"
              required
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              className="h-9 w-full max-w-md rounded-lg border border-border bg-background px-3 text-sm"
              disabled={createMutation.isPending}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-1">
              <label htmlFor="plan-goal" className="text-sm font-medium">
                goal
              </label>
              <input
                id="plan-goal"
                value={goal}
                onChange={(event) => setGoal(event.target.value)}
                className="h-9 w-full rounded-lg border border-border bg-background px-3 text-sm"
                disabled={createMutation.isPending}
              />
            </div>
            <div className="space-y-1">
              <label htmlFor="plan-audience" className="text-sm font-medium">
                target_audience
              </label>
              <input
                id="plan-audience"
                value={targetAudience}
                onChange={(event) => setTargetAudience(event.target.value)}
                className="h-9 w-full rounded-lg border border-border bg-background px-3 text-sm"
                disabled={createMutation.isPending}
              />
            </div>
            <div className="space-y-1">
              <label htmlFor="plan-message" className="text-sm font-medium">
                key_message
              </label>
              <input
                id="plan-message"
                value={keyMessage}
                onChange={(event) => setKeyMessage(event.target.value)}
                className="h-9 w-full rounded-lg border border-border bg-background px-3 text-sm"
                disabled={createMutation.isPending}
              />
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium">content_items</p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={createMutation.isPending}
                onClick={() =>
                  setContentItems((items) => [...items, emptyContentItem()])
                }
              >
                Add item
              </Button>
            </div>

            {contentItems.map((item, index) => (
              <div
                key={index}
                className="space-y-2 rounded-md border border-border bg-muted/20 p-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-muted-foreground">
                    Item {index + 1}
                  </span>
                  {contentItems.length > 1 ? (
                    <Button
                      type="button"
                      variant="ghost"
                      size="xs"
                      disabled={createMutation.isPending}
                      onClick={() =>
                        setContentItems((items) =>
                          items.filter((_, i) => i !== index),
                        )
                      }
                    >
                      Remove
                    </Button>
                  ) : null}
                </div>
                <input
                  placeholder="Title"
                  required
                  value={item.title}
                  onChange={(event) =>
                    updateItem(index, { title: event.target.value })
                  }
                  className="h-9 w-full rounded-lg border border-border bg-background px-3 text-sm"
                  disabled={createMutation.isPending}
                />
                <div className="grid gap-2 sm:grid-cols-3">
                  <input
                    placeholder="channel"
                    value={item.channel}
                    onChange={(event) =>
                      updateItem(index, { channel: event.target.value })
                    }
                    className="h-9 rounded-lg border border-border bg-background px-3 text-sm"
                    disabled={createMutation.isPending}
                  />
                  <select
                    value={item.format}
                    onChange={(event) =>
                      updateItem(index, {
                        format: event.target.value as "text" | "photo",
                      })
                    }
                    className="h-9 rounded-lg border border-border bg-background px-3 text-sm"
                    disabled={createMutation.isPending}
                  >
                    <option value="text">text</option>
                    <option value="photo">photo</option>
                  </select>
                  <input
                    type="datetime-local"
                    placeholder="scheduled_at (local)"
                    value={item.scheduledAtLocal}
                    onChange={(event) =>
                      updateItem(index, {
                        scheduledAtLocal: event.target.value,
                      })
                    }
                    className="h-9 rounded-lg border border-border bg-background px-3 text-sm"
                    disabled={createMutation.isPending}
                  />
                </div>
                {item.scheduledAtLocal ? (
                  <p className="text-xs text-muted-foreground">
                    Metadata UTC:{" "}
                    {previewUtcFromLocalInput(item.scheduledAtLocal) ?? "—"}
                  </p>
                ) : null}
                <input
                  placeholder="notes"
                  value={item.notes}
                  onChange={(event) =>
                    updateItem(index, { notes: event.target.value })
                  }
                  className="h-9 w-full rounded-lg border border-border bg-background px-3 text-sm"
                  disabled={createMutation.isPending}
                />
              </div>
            ))}
          </div>

          {clientError ? (
            <p className="text-sm text-destructive" role="alert">
              {clientError}
            </p>
          ) : null}

          <Button type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending ? "Creating…" : "Create plan draft"}
          </Button>
        </form>
      ) : null}
    </div>
  );
}
