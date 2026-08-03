"use client";

import type { StrategyLoadResult } from "@/lib/integration/strategy-adapter";
import { integrationModeLabel } from "@/lib/integration/mode";

type Props = { load: StrategyLoadResult | null };

export function StrategyPlanPanel({ load }: Props) {
  if (!load) return null;
  const view = load.view;

  return (
    <section
      className="border-b px-4 py-4 sm:px-6"
      style={{ borderColor: "var(--ms-border-default)", background: "var(--ms-bg-elevated)" }}
      aria-label="Strategy and MarketingPlan reconciliation"
    >
      <h2
        className="text-xs font-semibold uppercase tracking-[0.16em]"
        style={{ color: "var(--ms-brand-secondary)" }}
      >
        Integration I5 · Strategy ≠ MarketingPlan
      </h2>
      <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
        {integrationModeLabel(load.mode)}. Option B: MarketingPlan = ops execution spine. Strategy =
        GTM document (local/mock until dedicated domain).
      </p>

      {load.error ? (
        <p className="mt-3 text-sm" style={{ color: "var(--ms-status-danger)" }} role="alert">
          {load.error.message} {load.error.actionHint}
        </p>
      ) : null}

      {view?.semanticNotice ? (
        <p className="mt-2 text-xs" style={{ color: "var(--ms-text-secondary)" }} role="status">
          {view.semanticNotice.message}
        </p>
      ) : null}

      {load.legacyPlanOnBlockedVerdict ? (
        <p className="mt-2 text-xs" style={{ color: "var(--ms-status-danger)" }}>
          Legacy: MarketingPlan есть при blocked Verdict — не доказывает Strategy eligibility.
        </p>
      ) : null}

      {view ? (
        <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3 text-xs">
          <Fact
            label="Strategy origin"
            value={`${view.strategyOrigin.labelRu} (${view.strategyOrigin.origin})`}
          />
          <Fact label="Strategy SoT" value={view.strategyOrigin.isStrategySot ? "yes (labelled)" : "no"} />
          <Fact label="Plan = Strategy" value="false" />
          <Fact label="Write dual-write" value={view.writePolicy.strategyToMarketingPlan} />
          <Fact label="Creates campaign" value="false" />
          <Fact label="Triggers execution" value="false" />
          <Fact
            label="Eligibility"
            value={`${view.eligibility.mode} · allow=${view.eligibility.allow}`}
          />
          <Fact label="Plan selection" value={view.planSelectionRule} />
          <Fact label="Project" value={load.projectName ?? "—"} />
        </div>
      ) : null}

      {view && view.relatedPlans.length > 0 ? (
        <div className="mt-4">
          <h3 className="text-xs font-semibold" style={{ color: "var(--ms-text-primary)" }}>
            Related MarketingPlans ({view.relatedPlans.length}) — ops context
          </h3>
          <ul className="mt-2 space-y-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
            {view.relatedPlans.slice(0, 5).map((p) => (
              <li key={p.id}>
                [{p.status}] v{p.currentVersion} {p.title} — {p.specialistTaskCount} tasks ·{" "}
                {p.disclaimer}
              </li>
            ))}
          </ul>
        </div>
      ) : view ? (
        <p className="mt-3 text-xs" style={{ color: "var(--ms-text-muted)" }}>
          Нет связанных MarketingPlan (или не загружены).
        </p>
      ) : null}

      {view && view.sectionAuthorities.length > 0 && load.mode !== "mock" ? (
        <p className="mt-3 text-xs" style={{ color: "var(--ms-text-muted)" }}>
          Strategic sections authority: {view.sectionAuthorities[0]?.origin} — positioning /
          audience / offers не берутся из MarketingPlan.
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
