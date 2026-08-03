"use client";

import Link from "next/link";
import { useEffect, useState, type CSSProperties } from "react";
import { WorkspaceNav } from "@/components/workspace/workspace-nav";
import { PRODUCT_BRAND } from "@/lib/brand/product-brand";
import { getIntegrationMode, integrationModeLabel } from "@/lib/integration/mode";
import { ensureVerdict } from "@/lib/strategy/mock-strategies";
import {
  investigationHref,
  resolveStrategyAccess,
  strategyHref,
  verdictHref,
} from "@/lib/strategy/routing";
import { getCurrentVerdict } from "@/lib/verdict/storage";
import type { BusinessVerdict } from "@/lib/verdict/types";
import { verdictGlyph, verdictTokenVar } from "@/lib/verdict/selectors";

type Props = { projectId: string };

/**
 * Pivot / Rework Workspace — NO_GO only. Not a full pivot engine.
 */
export function PivotWorkspaceView({ projectId }: Props) {
  const [verdict, setVerdict] = useState<BusinessVerdict | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [backendEmpty, setBackendEmpty] = useState(false);
  const mode = getIntegrationMode();

  useEffect(() => {
    // I7: backend mode must not invent a local verdict as pivot success.
    if (mode === "backend") {
      const existing = getCurrentVerdict(projectId);
      if (!existing) {
        setVerdict(null);
        setBackendEmpty(true);
        setNotice(
          "Backend mode: Business Verdict SoT отсутствует. Локальный mock verdict не подставляется.",
        );
        setLoaded(true);
        return;
      }
      setVerdict(existing);
      const access = resolveStrategyAccess(existing);
      if (access.allow) {
        window.location.replace(strategyHref(projectId));
        return;
      }
      if (access.redirect === "investigation") {
        window.location.replace(investigationHref(projectId));
        return;
      }
      setLoaded(true);
      return;
    }

    const v = ensureVerdict(projectId);
    setVerdict(v);
    const access = resolveStrategyAccess(v);
    if (access.allow) {
      // GO / CONDITIONAL should use strategy, not pivot
      window.location.replace(strategyHref(projectId));
      return;
    }
    if (access.redirect === "investigation") {
      window.location.replace(investigationHref(projectId));
      return;
    }
    if (mode === "hybrid") {
      setNotice("Hybrid: локальный Verdict preview для Pivot. Не backend SoT.");
    }
    setLoaded(true);
  }, [projectId, mode]);

  if (!loaded) {
    return (
      <div
        className="flex min-h-screen items-center justify-center"
        style={{ background: "var(--ms-bg-canvas)", color: "var(--ms-text-muted)" }}
      >
        Загрузка Pivot Workspace…
      </div>
    );
  }

  if (backendEmpty || !verdict) {
    return (
      <div
        className="flex min-h-screen"
        style={{ background: "var(--ms-bg-canvas)", color: "var(--ms-text-primary)" }}
      >
        <WorkspaceNav />
        <div className="mx-auto flex max-w-xl flex-1 flex-col justify-center gap-3 p-6">
          <p
            className="text-[11px] font-semibold uppercase tracking-[0.22em]"
            style={{ color: "var(--ms-brand-secondary)" }}
          >
            {PRODUCT_BRAND.displayName} · Pivot / Rework
          </p>
          <h1 className="text-lg font-semibold">Pivot unavailable</h1>
          <p className="text-sm" style={{ color: "var(--ms-text-secondary)" }}>
            {notice ?? "Verdict unavailable"}
          </p>
          <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
            {integrationModeLabel(mode)}
          </p>
          <Link
            href={verdictHref(projectId)}
            className="text-sm font-medium"
            style={{ color: "var(--brand-blue-light)" }}
          >
            ← Verdict
          </Link>
        </div>
      </div>
    );
  }

  const color = verdictTokenVar(verdict.type);

  return (
    <div
      className="flex min-h-screen"
      style={{ background: "var(--ms-bg-canvas)", color: "var(--ms-text-primary)" }}
    >
      <WorkspaceNav />
      <div className="flex min-w-0 flex-1 flex-col">
        <header
          className="border-b px-4 py-4 sm:px-6"
          style={{
            borderColor: "var(--ms-border-default)",
            background: "color-mix(in srgb, var(--ms-bg-surface) 92%, transparent)",
          }}
        >
          <p
            className="text-[11px] font-semibold uppercase tracking-[0.22em]"
            style={{ color: "var(--ms-brand-secondary)" }}
          >
            {PRODUCT_BRAND.displayName} · Pivot / Rework
          </p>
          <h1 className="mt-1 text-lg font-semibold">{verdict.projectName}</h1>
          <p className="mt-2 inline-flex items-center gap-2 text-sm" style={{ color }}>
            <span aria-hidden>{verdictGlyph(verdict.type)}</span>
            {verdict.type} · стратегия не строится
          </p>
        </header>

        <div className="mx-auto w-full max-w-3xl space-y-6 p-4 sm:p-6">
          {notice ? (
            <p role="status" className="rounded-md border px-3 py-2 text-xs" style={box}>
              {notice}
            </p>
          ) : null}

          <section className="rounded-xl border p-5" style={panel}>
            <h2 className="text-sm font-semibold" style={{ color: "var(--ms-brand-secondary)" }}>
              WHY NOT PROCEED
            </h2>
            <p className="mt-3 text-base font-medium">{verdict.oneSentenceConclusion}</p>
            <p className="mt-2 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
              {verdict.executiveRationale}
            </p>
          </section>

          <section className="rounded-xl border p-5" style={panel}>
            <h2 className="text-sm font-semibold" style={{ color: "var(--ms-brand-secondary)" }}>
              CAUSES OF NO_GO
            </h2>
            <ul className="mt-3 list-disc space-y-2 pl-5 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
              {verdict.risks
                .filter((r) => r.sensitivity === "verdict_changing" || r.severity === "critical")
                .map((r) => (
                  <li key={r.id}>
                    {r.title}: {r.businessConsequence}
                  </li>
                ))}
              {verdict.counterEvidence
                .filter((c) => c.couldChangeVerdict)
                .map((c) => (
                  <li key={c.id}>{c.conflictingClaim}</li>
                ))}
              {verdict.scorecard
                .filter((d) => d.rating === "critical" || d.rating === "weak")
                .map((d) => (
                  <li key={d.id}>
                    {d.label}: {d.criticalGap || d.explanation}
                  </li>
                ))}
            </ul>
          </section>

          <section className="rounded-xl border p-5" style={panel}>
            <h2 className="text-sm font-semibold" style={{ color: "var(--ms-brand-secondary)" }}>
              MAY PRESERVE
            </h2>
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
              <li>Собранный evidence corpus и contradiction log</li>
              <li>Понимание сегмента (если было) как гипотеза для другой модели</li>
              <li>Ограничения и risk register как вход для pivot brief</li>
            </ul>
          </section>

          <section className="rounded-xl border p-5" style={panel}>
            <h2 className="text-sm font-semibold" style={{ color: "var(--ms-brand-secondary)" }}>
              MUST CHANGE
            </h2>
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
              <li>Текущая коммерческая модель / оффер в заявленном виде</li>
              <li>Unit-экономика или канал, давший структурный убыток</li>
              <li>Позиционирование, противоречащее evidence</li>
            </ul>
          </section>

          <section className="rounded-xl border p-5" style={panel}>
            <h2 className="text-sm font-semibold" style={{ color: "var(--ms-brand-secondary)" }}>
              POSSIBLE PIVOT DIRECTIONS (placeholder)
            </h2>
            <p className="mt-2 text-sm" style={{ color: "var(--ms-text-muted)" }}>
              Полный pivot engine не реализован в A5. Направления — ориентиры для revised intake:
            </p>
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
              <li>Узкий geo + другой оффер для того же сегмента</li>
              <li>Смена ценовой модели / delivery</li>
              <li>Другой сегмент с пересборкой brief</li>
            </ul>
          </section>

          <div className="flex flex-wrap gap-3">
            <Link
              href={investigationHref(projectId)}
              className="rounded-md px-4 py-2 text-sm font-semibold"
              style={{ background: "var(--ms-brand-primary)", color: "var(--ms-text-primary)" }}
            >
              Вернуться в Investigation
            </Link>
            <Link
              href={verdictHref(projectId)}
              className="rounded-md px-4 py-2 text-sm font-medium"
              style={secondaryBtn}
            >
              Открыть Verdict
            </Link>
            <button
              type="button"
              className="rounded-md px-4 py-2 text-sm font-medium"
              style={secondaryBtn}
              onClick={() =>
                setNotice(
                  "Create revised intake — placeholder. Новый business model в A5 не генерируется.",
                )
              }
            >
              Create revised intake (placeholder)
            </button>
            <Link href="/workspace/projects/new" className="rounded-md px-4 py-2 text-sm font-medium" style={secondaryBtn}>
              Новый бриф
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

const panel: CSSProperties = {
  borderColor: "var(--ms-border-default)",
  background: "var(--ms-bg-surface)",
};
const box: CSSProperties = {
  borderColor: "var(--ms-border-default)",
  background: "var(--ms-bg-elevated)",
  color: "var(--ms-text-secondary)",
};
const secondaryBtn: CSSProperties = {
  background: "var(--ms-bg-elevated)",
  color: "var(--ms-text-secondary)",
  boxShadow: "inset 0 0 0 1px var(--ms-border-default)",
};
