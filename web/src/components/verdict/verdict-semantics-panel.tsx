"use client";

import type { VerdictLoadResult } from "@/lib/integration/verdict-adapter";
import { integrationModeLabel } from "@/lib/integration/mode";

type Props = { load: VerdictLoadResult | null };

export function VerdictSemanticsPanel({ load }: Props) {
  if (!load) return null;
  const view = load.view;

  return (
    <section
      className="border-b px-4 py-4 sm:px-6"
      style={{ borderColor: "var(--ms-border-default)", background: "var(--ms-bg-elevated)" }}
      aria-label="Business Verdict semantics"
    >
      <h2
        className="text-xs font-semibold uppercase tracking-[0.16em]"
        style={{ color: "var(--ms-brand-secondary)" }}
      >
        Integration I4 · Decision semantics
      </h2>
      <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
        {integrationModeLabel(load.mode)}. Business Verdict ≠ Approval ≠ Execution ≠ CC next
        action ≠ Supervisor finding ≠ Verdict readiness.
      </p>

      {load.error ? (
        <p className="mt-3 text-sm" style={{ color: "var(--ms-status-danger)" }} role="alert">
          {load.error.message} {load.error.actionHint}
        </p>
      ) : null}

      {view ? (
        <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3 text-xs">
          <Fact label="Origin" value={`${view.originMeta.labelRu} (${view.originMeta.origin})`} />
          <Fact label="Authority" value={view.originMeta.authority} />
          <Fact
            label="Evidence basis"
            value={
              view.originMeta.evidenceVerified
                ? "evidence-verified"
                : `${view.originMeta.evidenceBasis} · not evidence-verified`
            }
          />
          <Fact
            label="Persisted backend"
            value={view.originMeta.persistedToBackend ? "yes" : "no"}
          />
          <Fact
            label="Strategy eligibility"
            value={`${view.strategyEligibility.mode} · allow=${view.strategyEligibility.allow}`}
          />
          <Fact
            label="Execution approval"
            value="not created by verdict review (false)"
          />
          <Fact label="Auto-upload local → backend" value="disabled" />
          <Fact label="Backend BusinessVerdict entity" value="absent (Option C)" />
          <Fact
            label="Project"
            value={load.projectName ?? view.verdict?.projectName ?? "—"}
          />
        </div>
      ) : null}

      {view && view.inputSignals.length > 0 ? (
        <div className="mt-4">
          <h3 className="text-xs font-semibold" style={{ color: "var(--ms-text-primary)" }}>
            Verdict input signals ({view.inputSignals.length}) — not verdicts
          </h3>
          <ul className="mt-2 space-y-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
            {view.inputSignals.slice(0, 6).map((s) => (
              <li key={s.id}>
                [{s.category}] {s.title} — {s.disclaimer}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {view?.strategyEligibility ? (
        <p className="mt-3 text-xs" style={{ color: "var(--ms-text-muted)" }}>
          {view.strategyEligibility.reason}
          {view.strategyEligibility.requiresVisibleConditions
            ? " · Conditions must remain visible."
            : ""}
        </p>
      ) : null}
    </section>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <p style={{ color: "var(--ms-text-secondary)" }}>
      <span style={{ color: "var(--ms-text-muted)" }}>{label}: </span>
      {value}
    </p>
  );
}
