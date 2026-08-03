"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState, type CSSProperties, type ReactNode } from "react";
import { StrategyPlanPanel } from "@/components/strategy/strategy-plan-panel";
import { WorkspaceNav } from "@/components/workspace/workspace-nav";
import { fetchLatestBusinessVerdict } from "@/lib/api/endpoints/business-verdicts";
import {
  approveMarketingStrategy,
  buildMarketingStrategyDraft,
  submitMarketingStrategyReview,
} from "@/lib/api/endpoints/marketing-strategies";
import { PRODUCT_BRAND } from "@/lib/brand/product-brand";
import {
  loadStrategyWorkspaceView,
  type StrategyLoadResult,
} from "@/lib/integration/strategy-adapter";
import { getIntegrationMode } from "@/lib/integration/mode";
import { prepareStrategyForProject } from "@/lib/strategy/mock-strategies";
import {
  investigationHref,
  pivotHref,
  resolveStrategyAccess,
  verdictHref,
} from "@/lib/strategy/routing";
import {
  executionStatusColor,
  executionStatusLabel,
  segmentValidationLabel,
  strategyStatusLabel,
} from "@/lib/strategy/selectors";
import {
  listStrategyVersions,
  updateStrategyStatus,
} from "@/lib/strategy/storage";
import type { MarketingStrategy } from "@/lib/strategy/types";
import { ensureVerdict } from "@/lib/strategy/mock-strategies";
import { VERDICT_SCENARIO_PROJECT } from "@/lib/verdict/mock-verdicts";
import { verdictTokenVar, verdictGlyph } from "@/lib/verdict/selectors";

type Props = { projectId: string };

export function StrategyWorkspaceView({ projectId }: Props) {
  const router = useRouter();
  const [strategy, setStrategy] = useState<MarketingStrategy | null>(null);
  const [versions, setVersions] = useState<MarketingStrategy[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [blocked, setBlocked] = useState<{ reason: string; href: string } | null>(
    null,
  );
  const [loaded, setLoaded] = useState(false);
  const [integrationLoad, setIntegrationLoad] = useState<StrategyLoadResult | null>(null);
  const [lifecycleBusy, setLifecycleBusy] = useState(false);
  const [approvedVerdictId, setApprovedVerdictId] = useState<string | null>(null);
  const mode = getIntegrationMode();

  const refresh = useCallback(async () => {
    const result = await loadStrategyWorkspaceView(projectId);
    setIntegrationLoad(result);

    if (!result.view?.eligibility.allow) {
      const reason =
        result.view?.eligibility.reason ??
        result.error?.message ??
        "Strategy blocked by Verdict eligibility";
      const redirect = result.view?.eligibility.redirect;
      const href =
        redirect === "pivot"
          ? pivotHref(projectId)
          : redirect === "investigation"
            ? investigationHref(projectId)
            : verdictHref(projectId);
      setBlocked({ reason, href });
      setStrategy(null);
      setVersions([]);
      if (mode === "mock" || (mode === "hybrid" && !result.legacyPlanOnBlockedVerdict)) {
        router.replace(href);
      }
      return result;
    }

    setBlocked(null);

    if (mode === "backend") {
      const s = result.view.strategy ?? null;
      setStrategy(s);
      setVersions(result.view.versions);
      try {
        const latestVerdict = await fetchLatestBusinessVerdict(projectId);
        setApprovedVerdictId(
          latestVerdict.lifecycle_status === "approved" ? latestVerdict.id : null,
        );
      } catch {
        setApprovedVerdictId(null);
      }
      setNotice(
        s
          ? "Backend MarketingStrategy loaded. Lifecycle ≠ MarketingPlan / Campaign / execution."
          : "Backend mode: MarketingStrategy отсутствует. Соберите draft явно. Mock не подставляется.",
      );
      return result;
    }

    try {
      const s = result.view.strategy ?? prepareStrategyForProject(projectId);
      const verdict = ensureVerdict(projectId);
      const access = resolveStrategyAccess(verdict);
      if (!access.allow) {
        const href =
          access.redirect === "pivot"
            ? pivotHref(projectId)
            : investigationHref(projectId);
        setBlocked({ reason: access.reason, href });
        router.replace(href);
        return result;
      }
      setStrategy(s);
      setVersions(
        result.view.versions.length ? result.view.versions : listStrategyVersions(projectId),
      );
      if (mode === "hybrid") {
        setNotice(
          "Hybrid: локальный Strategy preview + backend MarketingPlan (ops). Dual-write отключён.",
        );
      }
    } catch (e) {
      setBlocked({
        reason: e instanceof Error ? e.message : "Strategy blocked",
        href: verdictHref(projectId),
      });
    }
    return result;
  }, [projectId, router, mode]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      await refresh();
      if (!cancelled) setLoaded(true);
    })();
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  const onBuildStrategyDraft = async () => {
    setLifecycleBusy(true);
    try {
      let verdictId = approvedVerdictId;
      if (!verdictId) {
        const latestVerdict = await fetchLatestBusinessVerdict(projectId);
        if (latestVerdict.lifecycle_status !== "approved") {
          setNotice("Нужен approved BusinessVerdict для сборки Strategy draft.");
          return;
        }
        verdictId = latestVerdict.id;
        setApprovedVerdictId(verdictId);
      }
      const draft = await buildMarketingStrategyDraft(projectId, verdictId);
      const { mapBackendStrategyToProductAlpha } = await import(
        "@/lib/integration/marketing-strategy-api-adapter"
      );
      const mapped = mapBackendStrategyToProductAlpha(
        draft,
        integrationLoad?.projectName ?? projectId,
      );
      setStrategy(mapped);
      setVersions([mapped]);
      setNotice(
        `Strategy draft собран (v${draft.version}, ${draft.lifecycle_status}). Не MarketingPlan.`,
      );
      await refresh();
    } catch (err) {
      setNotice(
        err instanceof Error ? err.message : "Не удалось собрать Strategy draft.",
      );
    } finally {
      setLifecycleBusy(false);
    }
  };

  const onSubmitStrategyReview = async () => {
    if (!strategy) return;
    setLifecycleBusy(true);
    try {
      await submitMarketingStrategyReview(projectId, strategy.id);
      setNotice("Strategy отправлена на проверку (under_review).");
      await refresh();
    } catch (err) {
      setNotice(
        err instanceof Error ? err.message : "Не удалось отправить Strategy на проверку.",
      );
    } finally {
      setLifecycleBusy(false);
    }
  };

  const onApproveStrategy = async () => {
    if (!strategy) return;
    setLifecycleBusy(true);
    try {
      await approveMarketingStrategy(projectId, strategy.id);
      setNotice(
        "Strategy утверждена (approved). Не создаёт Campaign / Agent Run / execution.",
      );
      await refresh();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Не удалось утвердить Strategy.");
    } finally {
      setLifecycleBusy(false);
    }
  };

  if (!loaded) {
    return (
      <ShellCenter>Проверка доступа к Strategy Workspace…</ShellCenter>
    );
  }

  if (mode === "backend" && integrationLoad?.view?.eligibility.allow && !strategy) {
    return (
      <div
        className="flex min-h-screen"
        style={{ background: "var(--ms-bg-canvas)", color: "var(--ms-text-primary)" }}
      >
        <WorkspaceNav />
        <div className="flex min-w-0 flex-1 flex-col">
          <header
            className="border-b px-4 py-4 sm:px-6"
            style={{ borderColor: "var(--ms-border-default)" }}
          >
            <p
              className="text-[11px] font-semibold uppercase tracking-[0.22em]"
              style={{ color: "var(--ms-brand-secondary)" }}
            >
              {PRODUCT_BRAND.displayName} · Strategy Workspace
            </p>
            <h1 className="mt-1 text-lg font-semibold">
              {integrationLoad.projectName ?? "Project"}
            </h1>
          </header>
          <StrategyPlanPanel load={integrationLoad} />
          <div className="mx-auto max-w-2xl space-y-4 p-6">
            <p className="text-sm" style={{ color: "var(--ms-text-secondary)" }}>
              Нет backend MarketingStrategy. Соберите draft явно. MarketingPlan ≠ Strategy
              (Option B).
            </p>
            {notice ? (
              <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                {notice}
              </p>
            ) : null}
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                data-testid="strategy-build-draft"
                disabled={lifecycleBusy}
                onClick={() => void onBuildStrategyDraft()}
                className="rounded-md px-3 py-2 text-xs font-semibold disabled:opacity-50"
                style={secondaryBtn}
              >
                Собрать draft Strategy
              </button>
              <Link href={verdictHref(projectId)} className="rounded-md px-3 py-2 text-xs font-medium" style={{ color: "var(--brand-blue-light)" }}>
                ← Verdict
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (blocked || !strategy) {
    return (
      <div
        className="flex min-h-screen"
        style={{ background: "var(--ms-bg-canvas)", color: "var(--ms-text-primary)" }}
      >
        <WorkspaceNav />
        <div className="flex min-w-0 flex-1 flex-col">
          <StrategyPlanPanel load={integrationLoad} />
          <ShellCenter>
            <p className="max-w-lg text-center text-sm" style={{ color: "var(--ms-text-secondary)" }}>
              {blocked?.reason ?? "Strategy unavailable"}
            </p>
            <Link
              href={blocked?.href ?? verdictHref(projectId)}
              className="mt-4 text-sm font-medium"
              style={{ color: "var(--brand-blue-light)" }}
            >
              Перейти
            </Link>
          </ShellCenter>
        </div>
      </div>
    );
  }

  const er = strategy.executionReadiness;
  const color = verdictTokenVar(strategy.verdictType);
  const originBadge =
    integrationLoad?.view?.strategyOrigin.labelRu ?? strategy.localMockLabel;

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
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p
                className="text-[11px] font-semibold uppercase tracking-[0.22em]"
                style={{ color: "var(--ms-brand-secondary)" }}
              >
                {PRODUCT_BRAND.displayName} · Strategy Workspace
              </p>
              <h1 className="mt-1 text-lg font-semibold sm:text-xl">{strategy.projectName}</h1>
              <div className="mt-2 flex flex-wrap gap-2 text-xs">
                <span
                  className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 font-semibold"
                  style={{
                    background: `color-mix(in srgb, ${color} 22%, transparent)`,
                    color,
                  }}
                >
                  <span aria-hidden>{verdictGlyph(strategy.verdictType)}</span>
                  verdict {strategy.verdictType} · v{strategy.verdictVersion}
                </span>
                <Pill>strategy: {strategyStatusLabel(strategy.status)}</Pill>
                <Pill>v{strategy.version}</Pill>
                <Pill muted>snapshot: {strategy.evidenceSnapshotId.slice(0, 24)}…</Pill>
                <Pill muted>{originBadge}</Pill>
                <Pill muted>{strategy.updatedAtLabel}</Pill>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link href={verdictHref(projectId)} className="rounded-md px-3 py-2 text-xs font-medium" style={secondaryBtn}>
                ← Verdict
              </Link>
              <Link href="/workspace" className="rounded-md px-3 py-2 text-xs font-medium" style={secondaryBtn}>
                Workspace
              </Link>
            </div>
          </div>
        </header>

        <StrategyPlanPanel load={integrationLoad} />

        <div className="mx-auto w-full max-w-7xl space-y-6 p-4 sm:p-6">
          {notice ? (
            <p role="status" className="rounded-md border px-3 py-2 text-xs" style={noticeBox}>
              {notice}
            </p>
          ) : null}

          <section className="rounded-xl border p-4" style={panel} aria-label="Strategy demos">
            <h2 className="text-sm font-semibold" style={{ color: "var(--ms-brand-secondary)" }}>
              DEMO ROUTES
            </h2>
            <div className="mt-3 flex flex-wrap gap-2">
              <DemoLink href={`/workspace/projects/${VERDICT_SCENARIO_PROJECT.go}/strategy`} label="GO strategy" />
              <DemoLink
                href={`/workspace/projects/${VERDICT_SCENARIO_PROJECT.conditional_go}/strategy`}
                label="CONDITIONAL_GO strategy"
              />
              <DemoLink
                href={`/workspace/projects/${VERDICT_SCENARIO_PROJECT.no_go}/strategy`}
                label="NO_GO → should redirect pivot"
              />
              <DemoLink
                href={`/workspace/projects/${VERDICT_SCENARIO_PROJECT.insufficient_data}/strategy`}
                label="INSUFFICIENT → investigation"
              />
            </div>
          </section>

          <Panel title="Strategy summary">
            <dl className="grid gap-3 text-sm sm:grid-cols-2">
              {Object.entries({
                "Business objective": strategy.summary.businessObjective,
                "Target market": strategy.summary.targetMarket,
                "Primary audience": strategy.summary.primaryAudience,
                Positioning: strategy.summary.positioning,
                "Core offer": strategy.summary.coreOffer,
                "Channel mix": strategy.summary.channelMix,
                Budget: strategy.summary.budgetRange,
                Constraints: strategy.summary.keyConstraints,
                Conditions: strategy.summary.criticalConditions,
              }).map(([k, v]) => (
                <div key={k}>
                  <dt className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    {k}
                  </dt>
                  <dd className="mt-0.5" style={{ color: "var(--ms-text-secondary)" }}>
                    {v}
                  </dd>
                </div>
              ))}
            </dl>
          </Panel>

          <Panel title="Strategic objectives">
            <div className="grid gap-3 lg:grid-cols-2">
              {strategy.objectives.map((o) => (
                <article key={o.id} className="rounded-md border p-3 text-sm" style={card}>
                  <p className="font-medium">
                    [{o.priority}] {o.title}
                  </p>
                  <p className="mt-1" style={{ color: "var(--ms-text-secondary)" }}>
                    Business: {o.businessOutcome}
                  </p>
                  <p style={{ color: "var(--ms-text-secondary)" }}>
                    Marketing: {o.marketingOutcome}
                  </p>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    Metric: {o.successMetric} · {o.baseline} → {o.target} · {o.timeframe}
                  </p>
                  <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    Linked criterion: {o.linkedVerdictCriterion}
                  </p>
                </article>
              ))}
            </div>
          </Panel>

          <Panel title="Audience segments">
            <div className="grid gap-3 lg:grid-cols-2">
              {strategy.segments.map((s) => (
                <article key={s.id} className="rounded-md border p-3 text-sm" style={card}>
                  <p className="font-medium">
                    [{s.priority}] {s.name} · {s.model}
                  </p>
                  <p className="mt-1 text-xs font-semibold" style={{ color: "var(--brand-blue-light)" }}>
                    {segmentValidationLabel(s.validationStatus)} · evidence {s.evidenceStrength}
                  </p>
                  <p className="mt-1" style={{ color: "var(--ms-text-secondary)" }}>
                    Problem: {s.problem}
                  </p>
                  <p style={{ color: "var(--ms-text-secondary)" }}>
                    Outcome: {s.desiredOutcome}
                  </p>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    DM: {s.decisionMaker} · {s.userVsBuyer}
                  </p>
                </article>
              ))}
            </div>
          </Panel>

          <Panel title="Positioning">
            <dl className="grid gap-3 text-sm sm:grid-cols-2">
              {Object.entries(strategy.positioning).map(([k, v]) => (
                <div key={k}>
                  <dt className="text-xs uppercase tracking-wide" style={{ color: "var(--ms-text-muted)" }}>
                    {k}
                  </dt>
                  <dd className="mt-0.5" style={{ color: "var(--ms-text-secondary)" }}>
                    {v}
                  </dd>
                </div>
              ))}
            </dl>
          </Panel>

          <Panel title="Offer architecture">
            {strategy.offers.map((o) => (
              <article key={o.id} className="mb-3 rounded-md border p-3 text-sm" style={card}>
                <p className="font-medium">
                  [{o.kind}] {o.name}
                </p>
                <p className="mt-1" style={{ color: "var(--ms-text-secondary)" }}>
                  {o.promisedOutcome} · scope: {o.scope}
                </p>
                <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                  Price: {o.priceMode} · {o.priceValue} · CTA: {o.callToAction}
                </p>
                <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                  Validation: {segmentValidationLabel(o.validationStatus)}
                </p>
              </article>
            ))}
          </Panel>

          <Panel title="Channel strategy">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead>
                  <tr style={{ color: "var(--ms-text-muted)" }}>
                    <th className="py-2 pr-3 font-medium">Channel</th>
                    <th className="py-2 pr-3 font-medium">Status</th>
                    <th className="py-2 pr-3 font-medium">Role</th>
                    <th className="py-2 pr-3 font-medium">Stage</th>
                    <th className="py-2 font-medium">Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {strategy.channels.map((c) => (
                    <tr key={c.id} className="border-t" style={{ borderColor: "var(--ms-border-default)" }}>
                      <td className="py-2 pr-3">{c.label}</td>
                      <td className="py-2 pr-3">{c.status}</td>
                      <td className="py-2 pr-3" style={{ color: "var(--ms-text-secondary)" }}>
                        {c.role}
                      </td>
                      <td className="py-2 pr-3">{c.funnelStage}</td>
                      <td className="py-2">{c.costClass}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>

          <Panel title="Funnel">
            <ol className="space-y-2">
              {strategy.funnel.map((f, i) => (
                <li key={f.id} className="rounded-md border p-3 text-sm" style={card}>
                  <p className="font-medium">
                    {i + 1}. {f.label}
                  </p>
                  <p className="mt-1" style={{ color: "var(--ms-text-secondary)" }}>
                    User: {f.userAction} · Business: {f.businessAction}
                  </p>
                  <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    {f.channel} · {f.asset} · metric: {f.metric} · exit: {f.exitCriterion}
                  </p>
                </li>
              ))}
            </ol>
          </Panel>

          <Panel title="Content and asset plan">
            <div className="grid gap-3 sm:grid-cols-2">
              {strategy.assets.map((a) => (
                <article key={a.id} className="rounded-md border p-3 text-sm" style={card}>
                  <p className="font-medium">
                    [{a.priority}/{a.status}] {a.label}
                  </p>
                  <p className="mt-1" style={{ color: "var(--ms-text-secondary)" }}>
                    {a.purpose}
                  </p>
                  <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    {a.funnelStage} · {a.linkedMessage} · dep: {a.dependency}
                  </p>
                </article>
              ))}
            </div>
            <p className="mt-3 text-xs" style={{ color: "var(--ms-text-muted)" }}>
              Контент в A5 не генерируется — только план активов.
            </p>
          </Panel>

          <Panel title="Budget allocation">
            {strategy.budget.map((b) => (
              <article key={b.id} className="mb-3 rounded-md border p-3 text-sm" style={card}>
                <p className="font-medium">{b.section}</p>
                <p className="mt-1" style={{ color: "var(--ms-text-secondary)" }}>
                  {b.amountOrRange} · {b.percentageLabel}
                </p>
                <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                  {b.rationale} · learning: {b.expectedLearning}
                </p>
              </article>
            ))}
            <p className="text-xs" style={{ color: "var(--ms-status-warning)" }}>
              ROI не гарантируется. Exact figures не выдумываются при unknown budget.
            </p>
          </Panel>

          <Panel title="Metrics and decision gates">
            <div className="grid gap-3 lg:grid-cols-2">
              {strategy.metrics.map((m) => (
                <article key={m.id} className="rounded-md border p-3 text-sm" style={card}>
                  <p className="font-medium">
                    [{m.category}] {m.name}
                  </p>
                  <p className="mt-1" style={{ color: "var(--ms-text-secondary)" }}>
                    {m.purpose}
                  </p>
                  <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    {m.baseline} → {m.target} · {m.measurementPeriod}
                  </p>
                  <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    Threshold: {m.decisionThreshold} · If missed: {m.actionIfMissed}
                  </p>
                </article>
              ))}
            </div>
          </Panel>

          <Panel title="Conditions and blockers">
            {strategy.conditions.length === 0 ? (
              <p className="text-sm" style={{ color: "var(--ms-text-muted)" }}>
                Нет блокирующих conditions (GO path).
              </p>
            ) : (
              strategy.conditions.map((c) => (
                <article key={c.id} className="mb-3 rounded-md border p-3 text-sm" style={card}>
                  <p className="font-medium">
                    {c.blocksExecution ? "[BLOCKS EXECUTION] " : ""}
                    {c.unresolvedCondition}
                  </p>
                  <p className="mt-1" style={{ color: "var(--ms-text-secondary)" }}>
                    Action: {c.requiredAction}
                  </p>
                  <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    Owner: {c.owner} · {c.deadline} · success: {c.successCriterion}
                  </p>
                </article>
              ))
            )}
          </Panel>

          <div className="grid gap-6 lg:grid-cols-2">
            <Panel title="Strategic risks">
              {strategy.risks.map((r) => (
                <article key={r.id} className="mb-3 rounded-md border p-3 text-sm" style={card}>
                  <p className="font-medium">
                    [{r.severity}/{r.probability}] {r.title}
                  </p>
                  <p className="mt-1" style={{ color: "var(--ms-text-secondary)" }}>
                    {r.impact}
                  </p>
                  <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    Stop: {r.stopCondition}
                  </p>
                </article>
              ))}
            </Panel>
            <Panel title="Strategy assumptions">
              {strategy.assumptions.map((a) => (
                <article key={a.id} className="mb-3 rounded-md border p-3 text-sm" style={card}>
                  <p className="font-medium">
                    [{a.status}] {a.statement}
                  </p>
                  <p className="text-xs mt-1" style={{ color: "var(--ms-text-muted)" }}>
                    Validate: {a.validationMethod} · if false: {a.impactIfFalse}
                  </p>
                </article>
              ))}
            </Panel>
          </div>

          <Panel title="Execution readiness">
            <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
              Не является реальным execution approval. notRealExecutionApproval = true.
            </p>
            <p
              className="mt-3 text-2xl font-semibold"
              style={{ color: executionStatusColor(er.status) }}
              aria-label={`Execution readiness: ${executionStatusLabel(er.status)}`}
            >
              [{executionStatusLabel(er.status)}] {er.status}
            </p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 text-sm">
              <List title="Blockers" items={er.blockers} />
              <List title="Unresolved conditions" items={er.unresolvedConditions} />
              <List title="Missing elements" items={er.missingElements} />
              <div>
                <p className="text-xs font-semibold" style={{ color: "var(--ms-text-muted)" }}>
                  Next required action
                </p>
                <p className="mt-1" style={{ color: "var(--ms-text-secondary)" }}>
                  {er.nextRequiredAction}
                </p>
              </div>
            </div>
            <button
              type="button"
              className="mt-4 rounded-md px-5 py-2.5 text-sm font-semibold disabled:opacity-40"
              style={{
                background: "var(--ms-brand-primary)",
                color: "var(--ms-text-primary)",
              }}
              disabled={er.status === "blocked" || er.status === "not_ready"}
              onClick={() => {
                if (er.status === "blocked" || er.status === "not_ready") return;
                router.push(`/workspace/projects/${projectId}/implementation`);
              }}
            >
              Подготовить план реализации
            </button>
          </Panel>

          <Panel title={mode === "backend" ? "Backend review & versions" : "Local review & versions"}>
            <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
              {mode === "backend"
                ? "Durable MarketingStrategy lifecycle. Не Campaign / execution approval."
                : "Product Alpha local only — не backend approval."}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {mode === "backend" ? (
                <>
                  <button
                    type="button"
                    data-testid="strategy-build-draft"
                    disabled={lifecycleBusy}
                    onClick={() => void onBuildStrategyDraft()}
                    className="rounded-md px-3 py-2 text-xs font-semibold disabled:opacity-50"
                    style={secondaryBtn}
                  >
                    Собрать draft Strategy
                  </button>
                  {strategy.status === "draft" ? (
                    <button
                      type="button"
                      data-testid="strategy-submit-review"
                      disabled={lifecycleBusy}
                      onClick={() => void onSubmitStrategyReview()}
                      className="rounded-md px-3 py-2 text-xs font-semibold disabled:opacity-50"
                      style={secondaryBtn}
                    >
                      Отправить на проверку
                    </button>
                  ) : null}
                  {strategy.status === "under_review" ? (
                    <button
                      type="button"
                      data-testid="strategy-approve"
                      disabled={lifecycleBusy}
                      onClick={() => void onApproveStrategy()}
                      className="rounded-md px-3 py-2 text-xs font-semibold disabled:opacity-50"
                      style={secondaryBtn}
                    >
                      Утвердить Strategy
                    </button>
                  ) : null}
                </>
              ) : (
                <>
                  <ActionBtn
                    onClick={() => {
                      updateStrategyStatus(projectId, strategy.id, "draft");
                      setStrategy({ ...strategy, status: "draft" });
                      setNotice("Draft сохранён локально.");
                    }}
                  >
                    Save draft
                  </ActionBtn>
                  <ActionBtn
                    onClick={() => {
                      updateStrategyStatus(projectId, strategy.id, "under_review");
                      setStrategy({ ...strategy, status: "under_review" });
                      setNotice("Отправлено на проверку (local).");
                    }}
                  >
                    Send for review
                  </ActionBtn>
                  <ActionBtn
                    onClick={() => {
                      if (er.status === "blocked") {
                        setNotice("Нельзя утвердить: execution blocked условиями.");
                        return;
                      }
                      updateStrategyStatus(projectId, strategy.id, "approved");
                      setStrategy({ ...strategy, status: "approved" });
                      setNotice("Стратегия утверждена локально.");
                    }}
                  >
                    Approve strategy
                  </ActionBtn>
                  <ActionBtn
                    onClick={() => {
                      const next = prepareStrategyForProject(projectId, { regenerate: true });
                      setStrategy(next);
                      setVersions(listStrategyVersions(projectId));
                      setNotice(`Новая версия v${next.version}; предыдущая superseded.`);
                    }}
                  >
                    Create new version
                  </ActionBtn>
                </>
              )}
            </div>
            <ul className="mt-3 space-y-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
              {versions.map((v) => (
                <li key={v.id}>
                  v{v.version} · {v.verdictType} · {strategyStatusLabel(v.status)}
                  {v.id === strategy.id ? " · current" : ""}
                </li>
              ))}
            </ul>
          </Panel>

          <Panel title="Future handoffs">
            <div className="flex flex-wrap gap-2">
              <Link
                href={`/workspace/projects/${projectId}/implementation`}
                className="rounded-md px-3 py-2 text-xs font-semibold"
                style={{
                  ...secondaryBtn,
                  opacity: er.status === "blocked" || er.status === "not_ready" ? 0.4 : 1,
                  pointerEvents:
                    er.status === "blocked" || er.status === "not_ready" ? "none" : "auto",
                }}
                aria-disabled={er.status === "blocked" || er.status === "not_ready"}
              >
                Implementation Plan
              </Link>
              {["Campaign Planning", "Asset Production", "Budget Approval", "Execution"].map(
                (label) => (
                  <button
                    key={label}
                    type="button"
                    disabled
                    className="rounded-md px-3 py-2 text-xs opacity-40"
                    style={secondaryBtn}
                  >
                    {label} · unavailable
                  </button>
                ),
              )}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}

function ShellCenter({ children }: { children: ReactNode }) {
  return (
    <div
      className="flex min-h-screen flex-col items-center justify-center gap-3 p-6"
      style={{ background: "var(--ms-bg-canvas)", color: "var(--ms-text-primary)" }}
    >
      {children}
    </div>
  );
}

function DemoLink({ href, label }: { href: string; label: string }) {
  return (
    <Link href={href} className="rounded-md px-3 py-2 text-xs font-semibold" style={secondaryBtn}>
      {label}
    </Link>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-xl border p-4 sm:p-5" style={panel}>
      <h2
        className="text-[11px] font-semibold uppercase tracking-[0.16em]"
        style={{ color: "var(--ms-brand-secondary)" }}
      >
        {title}
      </h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function Pill({ children, muted }: { children: ReactNode; muted?: boolean }) {
  return (
    <span
      className="rounded-full px-2.5 py-0.5 font-medium"
      style={{
        background: muted
          ? "var(--ms-bg-elevated)"
          : "color-mix(in srgb, var(--brand-blue) 18%, transparent)",
        color: muted ? "var(--ms-text-muted)" : "var(--brand-blue-light)",
      }}
    >
      {children}
    </span>
  );
}

function List({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <p className="text-xs font-semibold" style={{ color: "var(--ms-text-muted)" }}>
        {title}
      </p>
      {items.length === 0 ? (
        <p className="mt-1 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
          Нет
        </p>
      ) : (
        <ul className="mt-1 list-disc pl-4 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
          {items.map((i) => (
            <li key={i}>{i}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ActionBtn({ children, onClick }: { children: ReactNode; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className="rounded-md px-3 py-2 text-xs font-semibold" style={secondaryBtn}>
      {children}
    </button>
  );
}

const panel: CSSProperties = {
  borderColor: "var(--ms-border-default)",
  background: "var(--ms-bg-surface)",
};
const card: CSSProperties = {
  borderColor: "var(--ms-border-default)",
  background: "var(--ms-bg-elevated)",
};
const secondaryBtn: CSSProperties = {
  background: "var(--ms-bg-elevated)",
  color: "var(--ms-text-secondary)",
  boxShadow: "inset 0 0 0 1px var(--ms-border-default)",
};
const noticeBox: CSSProperties = {
  borderColor: "var(--ms-border-default)",
  background: "var(--ms-bg-elevated)",
  color: "var(--ms-text-secondary)",
};
