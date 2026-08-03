"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/providers/toast-provider";
import { createPublishingChannel } from "@/lib/api/endpoints/publishing";
import { invalidateAfterPublishingChannelChange } from "@/lib/api/invalidate-after-channel-change";
import { ApiError } from "@/lib/api/errors";
import { buildTelegramChannelConfig } from "@/lib/publishing/channel-config";

type CreateTelegramChannelFormProps = {
  projectId: string;
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

export function CreateTelegramChannelForm({
  projectId,
}: CreateTelegramChannelFormProps) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("Telegram main");
  const [chatId, setChatId] = useState("");
  const [parseMode, setParseMode] = useState<"" | "HTML" | "MarkdownV2">("HTML");
  const [disableWebPagePreview, setDisableWebPagePreview] = useState(true);
  const [clientError, setClientError] = useState<string | null>(null);

  const queryClient = useQueryClient();
  const toast = useToast();

  const createMutation = useMutation({
    mutationFn: async () => {
      const config = buildTelegramChannelConfig({
        chatId,
        parseMode,
        disableWebPagePreview,
      });
      return createPublishingChannel(projectId, {
        name: name.trim(),
        type: "telegram",
        config,
      });
    },
    onSuccess: () => {
      toast.success("Telegram channel created");
      invalidateAfterPublishingChannelChange(queryClient, projectId);
      setOpen(false);
      setClientError(null);
      setChatId("");
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
        <div>
          <h2 className="text-sm font-semibold">Create Telegram channel</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Bot token is not stored here. Set{" "}
            <code className="text-xs">TELEGRAM_PUBLICATION_BOT_TOKEN</code> on the
            API server.
          </p>
        </div>
        <Button
          variant={open ? "secondary" : "default"}
          size="sm"
          onClick={() => setOpen((value) => !value)}
        >
          {open ? "Hide form" : "New channel"}
        </Button>
      </div>

      {open ? (
        <form
          className="mt-4 grid max-w-lg gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            setClientError(null);
            if (!name.trim()) {
              setClientError("Name is required");
              return;
            }
            if (!chatId.trim()) {
              setClientError("chat_id is required");
              return;
            }
            createMutation.mutate();
          }}
        >
          <div className="space-y-1">
            <label htmlFor="channel-name" className="text-sm font-medium">
              Name
            </label>
            <input
              id="channel-name"
              type="text"
              required
              value={name}
              onChange={(event) => setName(event.target.value)}
              className="h-9 w-full rounded-lg border border-border bg-background px-3 text-sm"
              disabled={createMutation.isPending}
            />
          </div>

          <div className="space-y-1">
            <label htmlFor="channel-chat-id" className="text-sm font-medium">
              Telegram chat_id
            </label>
            <input
              id="channel-chat-id"
              type="text"
              required
              placeholder="-100..."
              value={chatId}
              onChange={(event) => setChatId(event.target.value)}
              className="h-9 w-full rounded-lg border border-border bg-background px-3 text-sm font-mono"
              disabled={createMutation.isPending}
            />
          </div>

          <div className="space-y-1">
            <label htmlFor="channel-parse-mode" className="text-sm font-medium">
              parse_mode
            </label>
            <select
              id="channel-parse-mode"
              value={parseMode}
              onChange={(event) =>
                setParseMode(event.target.value as "" | "HTML" | "MarkdownV2")
              }
              className="h-9 w-full rounded-lg border border-border bg-background px-3 text-sm"
              disabled={createMutation.isPending}
            >
              <option value="HTML">HTML</option>
              <option value="MarkdownV2">MarkdownV2</option>
              <option value="">(none)</option>
            </select>
          </div>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={disableWebPagePreview}
              onChange={(event) => setDisableWebPagePreview(event.target.checked)}
              disabled={createMutation.isPending}
            />
            disable_web_page_preview
          </label>

          <p className="text-xs text-muted-foreground">
            Do not enter bot_token, api_key, or secret — they are rejected by the
            API and must live in server environment only.
          </p>

          {clientError ? (
            <p className="text-sm text-destructive" role="alert">
              {clientError}
            </p>
          ) : null}

          <Button type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending ? "Creating…" : "Create channel"}
          </Button>
        </form>
      ) : null}
    </div>
  );
}
