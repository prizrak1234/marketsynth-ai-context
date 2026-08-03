"use client";

import Link from "next/link";
import type { AgencySpecialistStatus } from "@/lib/workspace/types";
import type {
  AgencySpecialistStatusWithOrigin,
  DataOrigin,
  RuntimeMonitorFindingView,
} from "@/lib/integration/contracts";

type SpecialistRow = AgencySpecialistStatus | AgencySpecialistStatusWithOrigin;

type Props = {
  specialists: SpecialistRow[];
  projectName?: string;
  badgeLabel?: string;
  healthLabel?: string;
  nextActionLabel?: string;
  nextActionDescription?: string;
  unavailableCapabilities?: string[];
  controlCenterHref?: string | null;
  findings?: RuntimeMonitorFindingView[];
  metricsSummary?: string;
  origin?: DataOrigin;
};

function ProgressBar({
  value,
  state,
}: {
  value: number;
  state: AgencySpecialistStatus["state"];
}) {
  if (state === "waiting" || state === "blocked") {
    return (
      <div
        className="h-2 w-full rounded-full"
        style={{ background: "var(--ms-border-default)" }}
        aria-hidden
      />
    );
  }

  return (
    <div
      className="h-2 w-full overflow-hidden rounded-full"
      style={{ background: "var(--ms-border-default)" }}
      role="progressbar"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className="h-full rounded-full"
        style={{
          width: `${Math.max(0, Math.min(100, value))}%`,
          background:
            state === "completed"
              ? "var(--ms-status-success)"
              : "linear-gradient(90deg, var(--brand-blue-dark), var(--brand-blue-light))",
        }}
      />
    </div>
  );
}

function StateGlyph({ state }: { state: AgencySpecialistStatus["state"] }) {
  if (state === "completed") {
    return (
      <span style={{ color: "var(--ms-status-success)" }} aria-hidden>
        ✔
      </span>
    );
  }
  if (state === "waiting") {
    return (
      <span style={{ color: "var(--ms-text-muted)" }} aria-hidden>
        ◌
      </span>
    );
  }
  if (state === "blocked") {
    return (
      <span style={{ color: "var(--ms-status-danger)" }} aria-hidden>
        ■
      </span>
    );
  }
  return (
    <span style={{ color: "var(--brand-blue-light)" }} aria-hidden>
      ●
    </span>
  );
}

function rowOrigin(s: SpecialistRow): DataOrigin | undefined {
  return "origin" in s ? s.origin : undefined;
}

/**
 * Agency Runtime Monitor — frontend projection (mock or Campaign Control Center).
 * Not a state engine. Static progress only — no live animation.
 */
export function AgencyRuntimeMonitor({
  specialists,
  projectName,
  badgeLabel = "Live mock · Phase A1",
  healthLabel,
  nextActionLabel,
  nextActionDescription,
  unavailableCapabilities = [],
  controlCenterHref,
  findings = [],
  metricsSummary,
  origin,
}: Props) {
  return (
    <section
      className="rounded-xl border p-5 sm:p-6"
      style={{
        borderColor: "var(--ms-border-default)",
        background:
          "radial-gradient(ellipse 70% 50% at 50% 0%, color-mix(in srgb, var(--brand-blue) 16%, transparent), transparent 60%), var(--ms-bg-elevated)",
      }}
      aria-label="Agency Runtime Monitor"
    >
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p
            className="text-[11px] font-semibold uppercase tracking-[0.2em]"
            style={{ color: "var(--ms-brand-secondary)" }}
          >
            Agency Runtime Monitor
          </p>
          <h2
            className="mt-1 text-xl font-semibold"
            style={{ color: "var(--ms-text-primary)" }}
          >
            Работа цифрового агентства
          </h2>
          <p className="mt-1 text-sm" style={{ color: "var(--ms-text-muted)" }}>
            {projectName
              ? `Проект «${projectName}» — operational projection, не чат.`
              : "Наблюдайте за этапами агентства, а не за ответом модели."}
          </p>
          {healthLabel ? (
            <p className="mt-2 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
              Health: {healthLabel}
              {origin ? ` · data origin: ${origin}` : ""}
            </p>
          ) : null}
          {nextActionLabel ? (
            <p className="mt-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
              Next: {nextActionLabel}
              {nextActionDescription ? ` — ${nextActionDescription}` : ""}
            </p>
          ) : null}
          {metricsSummary ? (
            <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
              Metrics: {metricsSummary}
            </p>
          ) : null}
        </div>
        <span
          className="rounded-full px-3 py-1 text-xs font-medium"
          style={{
            background: "color-mix(in srgb, var(--ms-status-info) 20%, transparent)",
            color: "var(--brand-blue-light)",
          }}
        >
          {badgeLabel}
        </span>
      </div>

      {specialists.length === 0 ? (
        <p className="text-sm" style={{ color: "var(--ms-text-secondary)" }}>
          Capability not integrated / data unavailable for specialist board.
        </p>
      ) : (
        <ul className="space-y-0">
          {specialists.map((s, index) => (
            <li key={s.id}>
              <div className="py-4">
                <div className="mb-2 flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <StateGlyph state={s.state} />
                    <p
                      className="text-sm font-semibold"
                      style={{ color: "var(--ms-text-primary)" }}
                    >
                      {s.role}
                    </p>
                    {rowOrigin(s) ? (
                      <span
                        className="text-[10px] uppercase tracking-wide"
                        style={{ color: "var(--ms-text-muted)" }}
                        title={`Data origin: ${rowOrigin(s)}`}
                      >
                        [{rowOrigin(s)}]
                      </span>
                    ) : null}
                  </div>
                  {s.state === "completed" ? (
                    <span className="text-xs" style={{ color: "var(--ms-status-success)" }}>
                      Done
                    </span>
                  ) : null}
                  {s.state === "running" ? (
                    <span className="text-xs" style={{ color: "var(--brand-blue-light)" }}>
                      {s.progress}%
                    </span>
                  ) : null}
                  {s.state === "waiting" ? (
                    <span className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                      Waiting
                    </span>
                  ) : null}
                  {s.state === "blocked" ? (
                    <span className="text-xs" style={{ color: "var(--ms-status-danger)" }}>
                      Blocked
                    </span>
                  ) : null}
                </div>
                <ProgressBar value={s.progress} state={s.state} />
                <p className="mt-2 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
                  {s.state === "completed" ? `✔ ${s.detail}` : s.detail}
                </p>
              </div>
              {index < specialists.length - 1 ? (
                <div
                  className="h-px w-full"
                  style={{
                    background:
                      "linear-gradient(90deg, transparent, var(--ms-border-default), transparent)",
                  }}
                />
              ) : null}
            </li>
          ))}
        </ul>
      )}

      {findings.length > 0 ? (
        <div className="mt-4 border-t pt-4" style={{ borderColor: "var(--ms-border-default)" }}>
          <h3 className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--ms-text-muted)" }}>
            Supervisor findings
          </h3>
          <ul className="mt-2 space-y-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
            {findings.map((f) => (
              <li key={f.id}>
                [{f.severity}] {f.title}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {unavailableCapabilities.length > 0 ? (
        <details className="mt-4 text-xs" style={{ color: "var(--ms-text-muted)" }}>
          <summary className="cursor-pointer font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
            style={{ outlineColor: "var(--brand-blue-light)" }}
          >
            Backend gaps (AI.591 overlay absent / not connected)
          </summary>
          <ul className="mt-2 list-disc pl-4">
            {unavailableCapabilities.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </details>
      ) : null}

      {controlCenterHref ? (
        <Link
          href={controlCenterHref}
          className="mt-4 inline-block text-xs font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
          style={{
            color: "var(--brand-blue-light)",
            outlineColor: "var(--brand-blue-light)",
          }}
        >
          Open existing Campaign Control Center →
        </Link>
      ) : null}
    </section>
  );
}
