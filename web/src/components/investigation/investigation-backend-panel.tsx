"use client";

/**
 * I3 + P0.2 — backend projection panel for Investigation Workspace.
 * Does not claim Evidence/Source SoT or Business Verdict.
 */

import type { InvestigationLoadResult } from "@/lib/integration/investigation-adapter";
import type { InvestigationLoadDomainResult } from "@/lib/integration/investigation-sync";
import { integrationModeLabel } from "@/lib/integration/mode";

type Props = {
  load: InvestigationLoadResult | null;
  domain?: InvestigationLoadDomainResult | null;
};

export function InvestigationBackendPanel({ load, domain }: Props) {
  if (!load) return null;

  const modeLabel = integrationModeLabel(load.mode);
  const bundle = load.bundle;

  return (
    <section
      className="border-b px-4 py-4 sm:px-6"
      style={{
        borderColor: "var(--ms-border-default)",
        background: "var(--ms-bg-elevated)",
      }}
      aria-label="Investigation backend integration"
    >
      <h2
        className="text-xs font-semibold uppercase tracking-[0.16em]"
        style={{ color: "var(--ms-brand-secondary)" }}
      >
        Integration I3 · P0.2 Investigation domain
      </h2>
      <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
        {modeLabel}. Durable Investigation linked to submitted ProjectBrief version.
        Source/Evidence — unavailable until P0.3/P0.4. No auto Agent Run.
      </p>

      {load.error ? (
        <p className="mt-3 text-sm" style={{ color: "var(--ms-status-danger)" }} role="alert">
          {load.error.message} {load.error.actionHint}
        </p>
      ) : null}

      {!domain?.ok && domain?.error ? (
        <p className="mt-2 text-sm" style={{ color: "var(--ms-status-danger)" }} role="alert">
          {domain.error.message} {domain.error.actionHint}
        </p>
      ) : null}

      {load.partialNotice ? (
        <p className="mt-2 text-xs" style={{ color: "var(--ms-text-secondary)" }} role="status">
          {load.partialNotice.message}
        </p>
      ) : null}

      {domain?.ok ? (
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Fact
            label="Backend Investigation"
            value={
              domain.investigation
                ? `${domain.investigation.id} · v${domain.investigation.version} · ${domain.investigation.status}`
                : "not created (GET has no side effect)"
            }
          />
          <Fact
            label="Brief linkage"
            value={
              domain.investigation
                ? `brief ${domain.investigation.project_brief_id} · v${domain.investigation.project_brief_version}`
                : "requires submitted ProjectBrief"
            }
          />
          <Fact
            label="Readiness"
            value={
              domain.view
                ? `${domain.view.readinessStatus} · Source/Evidence pending`
                : "n/a"
            }
          />
          <Fact label="Source domain" value="unsupported until P0.3" />
          <Fact label="Evidence domain" value="unsupported until P0.4" />
          <Fact label="Reconciliation" value={domain.reconciliation.message} />
          <Fact label="Page-load create" value="false" />
          <Fact label="Agent Run / LLM on create" value="false / false" />
          <Fact
            label="Auto research"
            value="Автоматический исследовательский контур пока не подключён."
          />
        </div>
      ) : null}

      {bundle?.project ? (
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Fact
            label="Backend Project"
            value={`${bundle.project.name} · ${bundle.project.id}`}
          />
          <Fact
            label="View status"
            value={`${bundle.viewStatus.viewStatus} (${bundle.viewStatus.origin})`}
          />
          <Fact
            label="Campaign link"
            value={
              bundle.campaignId
                ? `${bundle.campaignName ?? "campaign"} · ${bundle.campaignId}`
                : "Нет business-campaign — только Project core"
            }
          />
          <Fact label="Evidence SoT" value="absent until P0.4 (no mock claim in backend mode)" />
          <Fact label="Source SoT" value="absent until P0.3" />
          <Fact
            label="Intake / ProjectBrief"
            value={
              bundle.intakeFingerprint
                ? `local fingerprint · ${bundle.intakeFingerprint}`
                : "optional ProjectBrief — Investigation not auto-created"
            }
          />
          <Fact label="Providers on load" value="none (false)" />
          <Fact label="Business Verdict" value="not generated (I4 / P0.5)" />
          <Fact
            label="Mock artifacts allowed"
            value={load.allowMockArtifacts ? "hybrid/mock gaps only" : "no silent mock evidence"}
          />
        </div>
      ) : load.mode === "mock" ? (
        <p className="mt-3 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
          Mock mode: Product Alpha local scenarios. Backend Investigation calls отключены.
        </p>
      ) : null}

      {bundle && bundle.researchArtifacts.length > 0 ? (
        <div className="mt-4">
          <h3 className="text-xs font-semibold" style={{ color: "var(--ms-text-primary)" }}>
            Research artifact candidates ({bundle.researchArtifacts.length})
          </h3>
          <ul className="mt-2 space-y-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
            {bundle.researchArtifacts.slice(0, 8).map((a) => (
              <li key={a.id}>
                [{a.origin}] {a.title} · {a.status} — {a.disclaimer}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {bundle && bundle.qualitySignals.length > 0 ? (
        <div className="mt-4">
          <h3 className="text-xs font-semibold" style={{ color: "var(--ms-text-primary)" }}>
            Campaign quality signals ({bundle.qualitySignals.length}) — not evidence
          </h3>
          <ul className="mt-2 space-y-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
            {bundle.qualitySignals.slice(0, 8).map((s) => (
              <li key={s.id}>
                [{s.role}] {s.title}: {s.description.slice(0, 120)}
                {s.description.length > 120 ? "…" : ""}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[10px] uppercase tracking-wide" style={{ color: "var(--ms-text-muted)" }}>
        {label}
      </dt>
      <dd className="mt-0.5 text-xs break-all" style={{ color: "var(--ms-text-primary)" }}>
        {value}
      </dd>
    </div>
  );
}
