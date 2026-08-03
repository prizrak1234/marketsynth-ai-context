"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { createBetaFeedback } from "@/lib/api/endpoints/beta-feedback";
import { queryKeys } from "@/lib/api/query-keys";

type Props = {
  projectId: string;
};

export function BetaFeedbackForm({ projectId }: Props) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [open, setOpen] = useState(false);

  const mutation = useMutation({
    mutationFn: () =>
      createBetaFeedback({
        title,
        description,
        project_id: projectId,
        source: "other",
        severity: "medium",
        safe_context: { project_id: projectId, screen: "dashboard" },
      }),
    onSuccess: () => {
      setTitle("");
      setDescription("");
      setOpen(false);
      void queryClient.invalidateQueries({ queryKey: queryKeys.myBetaFeedback });
      void queryClient.invalidateQueries({ queryKey: queryKeys.betaAdminFeedback });
    },
  });

  if (!open) {
    return (
      <button
        type="button"
        className="text-xs text-muted-foreground underline hover:text-foreground"
        onClick={() => setOpen(true)}
      >
        Report a beta issue
      </button>
    );
  }

  return (
    <form
      className="flex flex-col gap-2 rounded-md border border-border bg-muted/30 p-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (!title.trim() || !description.trim()) return;
        mutation.mutate();
      }}
    >
      <p className="text-xs font-medium">Beta feedback (diagnostic only)</p>
      <input
        className="rounded border border-input bg-background px-2 py-1 text-sm"
        placeholder="Short title"
        value={title}
        onChange={(event) => setTitle(event.target.value)}
        maxLength={256}
        required
      />
      <textarea
        className="min-h-[72px] rounded border border-input bg-background px-2 py-1 text-sm"
        placeholder="What broke? Which step?"
        value={description}
        onChange={(event) => setDescription(event.target.value)}
        maxLength={4096}
        required
      />
      <div className="flex gap-2">
        <button
          type="submit"
          className="rounded bg-primary px-3 py-1 text-xs font-medium text-primary-foreground disabled:opacity-50"
          disabled={mutation.isPending}
        >
          {mutation.isPending ? "Sending…" : "Submit"}
        </button>
        <button
          type="button"
          className="rounded px-3 py-1 text-xs text-muted-foreground"
          onClick={() => setOpen(false)}
        >
          Cancel
        </button>
      </div>
      {mutation.isError ? (
        <p className="text-xs text-destructive">Could not submit feedback.</p>
      ) : null}
    </form>
  );
}
