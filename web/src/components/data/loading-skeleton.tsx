import { cn } from "@/lib/utils";

type LoadingSkeletonProps = {
  variant?: "text" | "card" | "table";
  lines?: number;
  className?: string;
};

export function LoadingSkeleton({
  variant = "text",
  lines = 3,
  className,
}: LoadingSkeletonProps) {
  if (variant === "card") {
    return (
      <div
        className={cn("animate-pulse rounded-lg border border-border p-4", className)}
        role="status"
        aria-label="Loading"
      >
        <div className="h-4 w-1/3 rounded bg-muted" />
        <div className="mt-3 h-3 w-full rounded bg-muted/80" />
        <div className="mt-2 h-3 w-5/6 rounded bg-muted/80" />
      </div>
    );
  }

  if (variant === "table") {
    return (
      <div
        className={cn(
          "animate-pulse overflow-hidden rounded-lg border border-border",
          className,
        )}
        role="status"
        aria-label="Loading"
      >
        <div className="h-10 border-b border-border bg-muted/50" />
        {Array.from({ length: lines }).map((_, index) => (
          <div
            key={index}
            className="flex gap-4 border-b border-border/60 px-4 py-3 last:border-0"
          >
            <div className="h-3 flex-1 rounded bg-muted/80" />
            <div className="h-3 w-20 rounded bg-muted/60" />
            <div className="h-3 w-24 rounded bg-muted/60" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div
      className={cn("animate-pulse space-y-2", className)}
      role="status"
      aria-label="Loading"
    >
      {Array.from({ length: lines }).map((_, index) => (
        <div
          key={index}
          className={cn(
            "h-3 rounded bg-muted/80",
            index === lines - 1 ? "w-4/5" : "w-full",
          )}
        />
      ))}
    </div>
  );
}
