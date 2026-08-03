"use client";

import { useQuery } from "@tanstack/react-query";
import { QueryStatus } from "@/components/data/query-status";
import { fetchBetaAccess, fetchBetaGuide } from "@/lib/api/endpoints/beta-launch";
import { queryKeys } from "@/lib/api/query-keys";

export function BetaGuideCard() {
  const guideQuery = useQuery({
    queryKey: queryKeys.betaGuide,
    queryFn: fetchBetaGuide,
  });
  const accessQuery = useQuery({
    queryKey: queryKeys.betaAccess,
    queryFn: fetchBetaAccess,
  });

  return (
    <section className="rounded-lg border border-border bg-card p-4">
      <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-sm font-semibold">Beta guide</h2>
          <p className="text-xs text-muted-foreground">
            What to test in the closed MVP beta
          </p>
        </div>
        <QueryStatus query={accessQuery} loadingVariant="text">
          {(access) => (
            <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Access: {access.status}
              {access.gate_enabled && !access.can_use_mvp ? " (MVP locked)" : ""}
            </span>
          )}
        </QueryStatus>
      </div>
      <QueryStatus query={guideQuery} loadingVariant="text">
        {(guide) => (
          <div className="flex flex-col gap-3 text-sm">
            <p className="text-xs text-muted-foreground">
              Phase: <span className="font-mono">{guide.current_phase}</span>
            </p>
            <div>
              <p className="mb-1 text-xs font-medium text-muted-foreground">Expected path</p>
              <ol className="list-decimal space-y-1 pl-4 text-xs">
                {guide.expected_path.map((step) => (
                  <li key={step.key}>
                    <span className="font-medium">{step.label}</span>
                    {step.hint ? (
                      <span className="text-muted-foreground"> — {step.hint}</span>
                    ) : null}
                  </li>
                ))}
              </ol>
            </div>
            <div>
              <p className="mb-1 text-xs font-medium text-muted-foreground">Limitations</p>
              <ul className="list-disc space-y-0.5 pl-4 text-xs text-muted-foreground">
                {guide.known_limitations.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
            <p className="text-xs text-muted-foreground">{guide.feedback_instructions}</p>
          </div>
        )}
      </QueryStatus>
    </section>
  );
}
