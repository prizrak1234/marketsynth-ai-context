import { cn } from "@/lib/utils";

/** Shared status chip styles for ops UI (Phase UI.10). */
export const STATUS_BADGE_STYLES: Record<string, string> = {
  draft: "bg-sky-500/15 text-sky-900 dark:text-sky-100",
  active: "bg-emerald-500/15 text-emerald-900 dark:text-emerald-100",
  paused: "bg-amber-500/15 text-amber-900 dark:text-amber-100",
  completed: "bg-sky-500/15 text-sky-900 dark:text-sky-100",
  approved: "bg-emerald-500/15 text-emerald-900 dark:text-emerald-100",
  archived: "bg-muted text-muted-foreground",
  scheduled: "bg-sky-500/15 text-sky-800 dark:text-sky-200",
  queued: "bg-amber-500/15 text-amber-900 dark:text-amber-100",
  running: "bg-violet-500/15 text-violet-900 dark:text-violet-100",
  succeeded: "bg-emerald-500/15 text-emerald-900 dark:text-emerald-100",
  failed: "bg-destructive/15 text-destructive",
  cancelled: "bg-muted text-muted-foreground",
  planning: "bg-violet-500/15 text-violet-900 dark:text-violet-100",
  ready_for_review: "bg-amber-500/15 text-amber-900 dark:text-amber-100",
  publishing: "bg-sky-500/15 text-sky-900 dark:text-sky-100",
  done: "bg-emerald-500/15 text-emerald-900 dark:text-emerald-100",
};

export type StatusBadgeProps = {
  status: string;
  className?: string;
  strikethroughWhenArchived?: boolean;
};

export function StatusBadge({
  status,
  className,
  strikethroughWhenArchived = false,
}: StatusBadgeProps) {
  const normalized = status.trim().toLowerCase().replace(/\s+/g, "_");
  return (
    <span
      className={cn(
        "inline-flex rounded-md px-2 py-0.5 text-xs font-medium capitalize",
        STATUS_BADGE_STYLES[normalized] ?? "bg-muted text-muted-foreground",
        strikethroughWhenArchived && normalized === "archived" && "line-through",
        className,
      )}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}

export function WorkflowStateBadge({ state }: { state: string }) {
  return <StatusBadge status={state} />;
}

export function ContentAssetStatusBadge({ status }: { status: string }) {
  return <StatusBadge status={status} />;
}
