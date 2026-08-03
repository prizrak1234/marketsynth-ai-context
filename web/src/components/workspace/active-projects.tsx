"use client";

import Link from "next/link";
import type { WorkspaceProjectViewModel } from "@/lib/integration/contracts";
import { unavailableLabel } from "@/lib/integration/errors";

type Props = {
  projects: WorkspaceProjectViewModel[];
};

export function ActiveProjects({ projects }: Props) {
  if (projects.length === 0) {
    return null;
  }

  return (
    <section>
      <h2
        className="text-sm font-semibold uppercase tracking-[0.14em]"
        style={{ color: "var(--ms-brand-secondary)" }}
      >
        Active Projects
      </h2>
      <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {projects.map((p) => (
          <article
            key={p.id}
            className="rounded-xl border p-4"
            style={{
              borderColor: "var(--ms-border-default)",
              background: "var(--ms-bg-elevated)",
            }}
          >
            <div className="flex items-start justify-between gap-2">
              <h3
                className="text-sm font-semibold"
                style={{ color: "var(--ms-text-primary)" }}
              >
                {p.name}
              </h3>
              <span
                className="shrink-0 rounded-full px-2 py-0.5 text-[11px]"
                style={{
                  background: "color-mix(in srgb, var(--brand-blue) 16%, transparent)",
                  color: "var(--brand-blue-light)",
                }}
              >
                {p.statusLabel}
              </span>
            </div>
            <dl className="mt-3 space-y-1.5 text-xs" style={{ color: "var(--ms-text-muted)" }}>
              <div className="flex justify-between gap-2">
                <dt>ID</dt>
                <dd
                  className="max-w-[65%] truncate text-right font-mono"
                  style={{ color: "var(--ms-text-secondary)" }}
                  title={p.id}
                >
                  {p.id}
                </dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt>Этап</dt>
                <dd style={{ color: "var(--ms-text-secondary)" }}>{p.stageLabel}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt>Next step</dt>
                <dd className="max-w-[60%] text-right" style={{ color: "var(--ms-text-secondary)" }}>
                  {p.nextRecommendedStep || unavailableLabel()}
                </dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt>Campaigns</dt>
                <dd style={{ color: "var(--ms-text-secondary)" }}>
                  {p.activeCampaignCount == null
                    ? unavailableLabel()
                    : String(p.activeCampaignCount)}
                </dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt>Обновлено</dt>
                <dd style={{ color: "var(--ms-text-secondary)" }}>{p.updatedAtLabel}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt>Origin</dt>
                <dd style={{ color: "var(--ms-text-secondary)" }}>{p.origin}</dd>
              </div>
            </dl>
            {p.controlCenterHref ? (
              <Link
                href={p.controlCenterHref}
                className="mt-3 inline-block text-xs font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
                style={{
                  color: "var(--brand-blue-light)",
                  outlineColor: "var(--brand-blue-light)",
                }}
              >
                Open Campaign Control Center →
              </Link>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}
