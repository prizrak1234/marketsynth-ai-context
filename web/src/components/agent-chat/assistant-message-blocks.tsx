"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { executeChatBlockAction } from "@/lib/api/endpoints/agent-chat";
import { ApiError } from "@/lib/api/errors";
import { cn } from "@/lib/utils";
import type {
  ChatAssistantMessageBlock,
  ChatBlockAction,
  ChatBlockActionType,
} from "@/lib/api/types/agent-chat";

type AssistantMessageBlocksProps = {
  blocks: ChatAssistantMessageBlock[];
  className?: string;
  projectId?: string;
  sessionId?: string;
  assistantMessageId?: string;
};

type BlockCardProps = {
  children: ReactNode;
  variant: "default" | "guidance" | "draft" | "brief" | "plan" | "error";
};

function BlockCard({ children, variant }: BlockCardProps) {
  const styles = {
    default: "border-border bg-muted/50",
    guidance: "border-dashed border-border bg-muted/20",
    draft: "border-primary/30 bg-primary/5",
    brief: "border-sky-500/30 bg-sky-500/5",
    plan: "border-emerald-500/30 bg-emerald-500/5",
    error: "border-destructive/40 bg-destructive/10",
  };
  return (
    <div
      className={cn(
        "max-w-[85%] rounded-lg border px-3 py-2 text-sm whitespace-pre-wrap",
        styles[variant],
      )}
    >
      {children}
    </div>
  );
}

function BlockActionsBar({
  actions,
  blockIndex,
  projectId,
  sessionId,
  assistantMessageId,
}: {
  actions: ChatBlockAction[];
  blockIndex: number;
  projectId: string;
  sessionId: string;
  assistantMessageId: string;
}) {
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (actionType: ChatBlockActionType) =>
      executeChatBlockAction(projectId, {
        session_id: sessionId,
        assistant_message_id: assistantMessageId,
        block_index: blockIndex,
        action_type: actionType,
      }),
    onSuccess: async (data, actionType) => {
      setError(null);
      if (actionType === "copy_text" && data.text) {
        try {
          await navigator.clipboard.writeText(data.text);
          setFeedback("Copied to clipboard");
        } catch {
          setFeedback(data.text.slice(0, 120) + (data.text.length > 120 ? "…" : ""));
        }
      } else if (actionType === "export_markdown" && data.markdown) {
        try {
          await navigator.clipboard.writeText(data.markdown);
          setFeedback("Markdown copied");
        } catch {
          setFeedback("Markdown ready");
        }
      } else if (
        actionType === "save_marketing_plan" &&
        data.created_resource_id
      ) {
        setFeedback(`Saved plan ${data.created_resource_id}`);
        if (projectId) {
          void queryClient.invalidateQueries({
            queryKey: ["marketing-plans", projectId],
          });
        }
      } else if (data.created_resource_id) {
        setFeedback(data.message || "Created");
      } else {
        setFeedback(data.message);
      }
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Action failed");
      }
      setFeedback(null);
    },
  });

  const runAction = useCallback(
    (action: ChatBlockAction) => {
      if (!action.enabled) {
        return;
      }
      setFeedback(null);
      setError(null);
      mutation.mutate(action.type);
    },
    [mutation],
  );

  if (!actions.length) {
    return null;
  }

  return (
    <div className="mt-2 flex flex-col gap-1">
      <div className="flex flex-wrap gap-1.5">
        {actions.map((action) => (
          <Button
            key={`${action.type}-${action.label}`}
            type="button"
            variant={action.enabled ? "outline" : "ghost"}
            size="sm"
            className="h-7 text-xs"
            disabled={!action.enabled || mutation.isPending}
            title={action.reason ?? undefined}
            onClick={() => runAction(action)}
          >
            {action.label}
          </Button>
        ))}
      </div>
      {actions.some((a) => !a.enabled && a.reason) ? (
        <p className="text-xs text-muted-foreground">
          {actions.find((a) => !a.enabled && a.reason)?.reason}
        </p>
      ) : null}
      {feedback ? <p className="text-xs text-muted-foreground">{feedback}</p> : null}
      {error ? <p className="text-xs text-destructive">{error}</p> : null}
    </div>
  );
}

function renderBlockContent(block: ChatAssistantMessageBlock) {
  const title = block.title ? (
    <p className="mb-1 font-medium text-foreground">{block.title}</p>
  ) : null;

  switch (block.type) {
    case "clarification":
      return (
        <>
          {title}
          <p className="text-muted-foreground">{block.content}</p>
        </>
      );
    case "draft":
      return (
        <>
          {title}
          <p>{block.content}</p>
          {block.persisted === false ? (
            <p className="mt-2 text-xs text-muted-foreground">Not persisted — review only.</p>
          ) : null}
        </>
      );
    case "brief":
      return (
        <>
          {title}
          <p>{block.content}</p>
          {block.persisted === false ? (
            <p className="mt-2 text-xs text-muted-foreground">Not persisted — review only.</p>
          ) : null}
        </>
      );
    case "marketing_plan": {
      const plan = block.data?.marketing_execution_plan as
        | {
            goal?: string;
            specialist_tasks?: Array<{
              specialist?: string;
              objective?: string;
              expected_output?: string;
            }>;
            execution_mode?: string;
          }
        | undefined;
      const tasks = plan?.specialist_tasks ?? [];
      return (
        <>
          {title}
          {plan?.goal ? (
            <p className="mb-2 font-medium text-foreground">{plan.goal}</p>
          ) : null}
          {tasks.length > 0 ? (
            <ul className="list-disc space-y-1 pl-4 text-sm">
              {tasks.map((task, idx) => (
                <li key={`${task.specialist ?? "task"}-${idx}`}>
                  <span className="font-medium capitalize">
                    {(task.specialist ?? "specialist").replace(/_/g, " ")}
                  </span>
                  {task.objective ? `: ${task.objective}` : null}
                  {task.expected_output ? (
                    <span className="text-muted-foreground">
                      {" "}
                      → {task.expected_output}
                    </span>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p>{block.content}</p>
          )}
          <p className="mt-2 text-xs text-muted-foreground">
            Planning mode only — no execute action in this phase.
          </p>
        </>
      );
    }
    case "error":
      return <p className="text-destructive">{block.content}</p>;
    case "text":
    default:
      return (
        <>
          {title}
          <p>{block.content}</p>
        </>
      );
  }
}

function blockVariant(block: ChatAssistantMessageBlock): BlockCardProps["variant"] {
  switch (block.type) {
    case "clarification":
      return "guidance";
    case "draft":
      return "draft";
    case "brief":
      return "brief";
    case "marketing_plan":
      return "plan";
    case "error":
      return "error";
    default:
      return "default";
  }
}

export function AssistantMessageBlocks({
  blocks,
  className,
  projectId,
  sessionId,
  assistantMessageId,
}: AssistantMessageBlocksProps) {
  const canExecuteActions =
    Boolean(projectId) && Boolean(sessionId) && Boolean(assistantMessageId);

  if (!blocks.length) {
    return null;
  }

  return (
    <div className={cn("flex flex-col items-start gap-2", className)}>
      {blocks.map((block, index) => {
        const actions = block.actions ?? [];
        const showActions = canExecuteActions && actions.length > 0;
        return (
          <BlockCard
            key={`block-${index}-${block.type}`}
            variant={blockVariant(block)}
          >
            {renderBlockContent(block)}
            {showActions ? (
              <BlockActionsBar
                actions={actions}
                blockIndex={index}
                projectId={projectId!}
                sessionId={sessionId!}
                assistantMessageId={assistantMessageId!}
              />
            ) : null}
            {!showActions && actions.some((a) => !a.enabled && a.reason) ? (
              <p className="mt-2 text-xs text-muted-foreground">
                {actions.find((a) => a.reason)?.reason}
              </p>
            ) : null}
          </BlockCard>
        );
      })}
    </div>
  );
}
