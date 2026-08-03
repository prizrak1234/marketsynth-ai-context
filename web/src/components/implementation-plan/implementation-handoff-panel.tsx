"use client";

import { useState } from "react";
import type { ImplementationLoadResult } from "@/lib/integration/implementation-plan-adapter";
import {
  confirmMarketingPlanHandoffDraft,
  requestMarketingPlanHandoffPreview,
} from "@/lib/integration/marketing-plan-handoff-api-adapter";
import type { MarketingPlanHandoffPreviewView } from "@/lib/integration/marketing-plan-handoff-preview-adapter";
import type { MarketingPlanHandoffResultView } from "@/lib/integration/marketing-plan-handoff-api-adapter";
import type { MarketingPlanHandoffError } from "@/lib/integration/marketing-plan-handoff-errors";
import { getIntegrationMode, integrationModeLabel } from "@/lib/integration/mode";

type Props = {
  load: ImplementationLoadResult | null;
  projectId: string;
  implementationPlanId: string | null;
  implementationPlanVersion: number | null;
};

export function ImplementationHandoffPanel({
  load,
  projectId,
  implementationPlanId,
  implementationPlanVersion,
}: Props) {
  const mode = getIntegrationMode();
  const view = load?.view;
  const localPreview = view?.handoffPreview;

  const [backendPreview, setBackendPreview] =
    useState<MarketingPlanHandoffPreviewView | null>(null);
  const [result, setResult] = useState<MarketingPlanHandoffResultView | null>(null);
  const [error, setError] = useState<MarketingPlanHandoffError | null>(null);
  const [busy, setBusy] = useState(false);
  const [explicitDraftOnly, setExplicitDraftOnly] = useState(false);

  async function onCheckReadiness() {
    if (!implementationPlanId) {
      setError({
        kind: "implementation_plan_not_found",
        message: "Нет durable ImplementationPlan id.",
        status: null,
        actionHint: "Откройте backend/hybrid plan с approved ImplementationPlan.",
      });
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    const res = await requestMarketingPlanHandoffPreview({
      projectId,
      implementationPlanId,
    });
    setBusy(false);
    if (!res.ok) {
      setBackendPreview(null);
      setError(res.error);
      return;
    }
    setBackendPreview(res.view);
    setExplicitDraftOnly(false);
  }

  async function onConfirmDraft() {
    if (!implementationPlanId || !backendPreview || !implementationPlanVersion) return;
    if (!explicitDraftOnly) {
      setError({
        kind: "explicit_confirmation_required",
        message: "explicit_confirmation_required",
        status: null,
        actionHint: "Отметьте «Создать только черновик MarketingPlan».",
      });
      return;
    }
    setBusy(true);
    setError(null);
    const res = await confirmMarketingPlanHandoffDraft({
      projectId,
      implementationPlanId,
      handoffPreviewId: backendPreview.handoffId,
      mappingFingerprint: backendPreview.mappingFingerprint,
      expectedImplementationPlanVersion: implementationPlanVersion,
      explicitConfirmation: true,
    });
    setBusy(false);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    setResult(res.view);
  }

  if (!load) return null;

  return (
    <section
      className="border-b px-4 py-4 sm:px-6"
      style={{ borderColor: "var(--ms-border-default)", background: "var(--ms-bg-elevated)" }}
      aria-label="Implementation Plan to MarketingPlan handoff"
    >
      <h2
        className="text-xs font-semibold uppercase tracking-[0.16em]"
        style={{ color: "var(--ms-brand-secondary)" }}
      >
        Передача в MarketingPlan · P1.2
      </h2>
      <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
        {integrationModeLabel(mode)}. Controlled draft handoff. ImplementationPlan ≠ MarketingPlan ≠
        Execution.
      </p>

      {load.error ? (
        <p className="mt-3 text-sm" style={{ color: "var(--ms-status-danger)" }} role="alert">
          {load.error.message} {load.error.actionHint}
        </p>
      ) : null}

      {view ? (
        <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3 text-xs">
          <Fact label="ImplPlan origin" value={view.origin.labelRu} />
          <Fact
            label="Linked MarketingPlan"
            value={
              view.primaryPlan
                ? `${view.primaryPlan.id} · ${view.primaryPlan.status} · v${view.primaryPlan.currentVersion}`
                : "not_linked"
            }
          />
          <Fact
            label="Local mapped / excluded"
            value={
              localPreview
                ? `${localPreview.included.length} mapped · ${localPreview.excluded.length} excluded`
                : "—"
            }
          />
          <Fact label="Creates campaign / Agent Run" value="false / false" />
          <Fact label="Handoff confirm → MP approve" value="false" />
          <Fact label="Project" value={load.projectName ?? "—"} />
        </div>
      ) : null}

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          type="button"
          disabled={busy || !implementationPlanId}
          onClick={() => void onCheckReadiness()}
          className="rounded px-3 py-1.5 text-xs font-medium"
          style={{
            background: "var(--ms-brand-primary)",
            color: "var(--ms-text-on-brand, #fff)",
            opacity: busy || !implementationPlanId ? 0.5 : 1,
          }}
        >
          Проверить готовность к передаче
        </button>
        {!implementationPlanId ? (
          <span className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
            Нужен durable ImplementationPlan (backend/hybrid).
          </span>
        ) : null}
      </div>

      {error ? (
        <p className="mt-3 text-sm" style={{ color: "var(--ms-status-danger)" }} role="alert">
          {error.message} {error.actionHint}
        </p>
      ) : null}

      {backendPreview ? (
        <div className="mt-4 space-y-3 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
          <h3 className="text-xs font-semibold" style={{ color: "var(--ms-text-primary)" }}>
            Preview · {backendPreview.mappingVersion}
          </h3>
          <p>
            Title «{backendPreview.proposedTitle}» · eligible={String(backendPreview.eligible)} ·
            side effects={backendPreview.sideEffects.length ? backendPreview.sideEffects.join(",") : "none"}
          </p>
          <ClassificationList label="Included" items={backendPreview.included} />
          <ClassificationList label="Transformed" items={backendPreview.transformed} />
          <ClassificationList label="Excluded" items={backendPreview.excluded} />
          <ClassificationList label="Unsupported" items={backendPreview.unsupported} />
          <ClassificationList label="Blocked" items={backendPreview.blocked} />
          {backendPreview.dependencyWarnings.length ? (
            <p>Dependencies: {backendPreview.dependencyWarnings.join("; ")}</p>
          ) : null}
          {backendPreview.acceptanceWarnings.length ? (
            <p>Acceptance: {backendPreview.acceptanceWarnings.slice(0, 3).join("; ")}</p>
          ) : null}
          {backendPreview.roleNotes.length ? (
            <p>Roles: {backendPreview.roleNotes.slice(0, 6).join("; ")}</p>
          ) : null}
          {backendPreview.existingPlans.length ? (
            <div>
              <p className="font-semibold" style={{ color: "var(--ms-text-primary)" }}>
                Existing MarketingPlans
              </p>
              <ul className="mt-1 space-y-1">
                {backendPreview.existingPlans.map((p) => (
                  <li key={p.id}>
                    [{p.status}] {p.title} · v{p.version}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {backendPreview.blockers.length ? (
            <p style={{ color: "var(--ms-status-danger)" }}>
              Blockers: {backendPreview.blockers.join("; ")}
            </p>
          ) : null}

          <label className="flex items-start gap-2" style={{ color: "var(--ms-text-primary)" }}>
            <input
              type="checkbox"
              data-testid="handoff-draft-only"
              aria-label="Создать только черновик MarketingPlan"
              checked={explicitDraftOnly}
              onChange={(e) => setExplicitDraftOnly(e.target.checked)}
              disabled={!backendPreview.eligible || busy}
            />
            <span>Создать только черновик MarketingPlan</span>
          </label>

          <button
            type="button"
            disabled={busy || !backendPreview.eligible || !explicitDraftOnly}
            onClick={() => void onConfirmDraft()}
            className="rounded px-3 py-1.5 text-xs font-medium"
            style={{
              background: "var(--ms-brand-secondary)",
              color: "var(--ms-text-on-brand, #fff)",
              opacity: busy || !backendPreview.eligible || !explicitDraftOnly ? 0.45 : 1,
            }}
          >
            Создать черновик MarketingPlan
          </button>
          <p style={{ color: "var(--ms-text-muted)" }}>{backendPreview.notice}</p>
        </div>
      ) : null}

      {result ? (
        <div
          className="mt-4 space-y-2 rounded border p-3 text-xs"
          style={{ borderColor: "var(--ms-border-default)", color: "var(--ms-text-secondary)" }}
          role="status"
        >
          <p style={{ color: "var(--ms-text-primary)" }} className="font-semibold">
            Draft MarketingPlan создан
          </p>
          <p>
            ID {result.marketingPlanId} · v{result.marketingPlanVersion} · status=
            {result.marketingPlanStatus}
            {result.idempotentReplay ? " · idempotent replay" : ""}
          </p>
          <p>
            Included {result.includedTaskCount} · excluded {result.excludedTaskCount} · blocked{" "}
            {result.blockedTaskCount}
          </p>
          <p style={{ color: "var(--ms-brand-primary)" }}>
            MarketingPlan draft ID: {result.marketingPlanId} (ops spine; not approved)
          </p>
          <p style={{ color: "var(--ms-text-muted)" }}>{result.notice}</p>
        </div>
      ) : null}

      <p className="mt-3 text-xs" style={{ color: "var(--ms-text-muted)" }}>
        A7 / AI.592 / V2.2 paused. Handoff ≠ MarketingPlan approval ≠ execution approval.
      </p>
    </section>
  );
}

function ClassificationList({
  label,
  items,
}: {
  label: string;
  items: Array<{ implementation_task_id: string; title: string; reason: string }>;
}) {
  if (!items.length) return null;
  return (
    <div>
      <p className="font-semibold" style={{ color: "var(--ms-text-primary)" }}>
        {label} ({items.length})
      </p>
      <ul className="mt-1 space-y-1">
        {items.slice(0, 5).map((t) => (
          <li key={t.implementation_task_id}>
            {t.title} — {t.reason}
          </li>
        ))}
      </ul>
    </div>
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
