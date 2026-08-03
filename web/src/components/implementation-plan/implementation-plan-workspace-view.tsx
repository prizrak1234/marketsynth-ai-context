"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState, type CSSProperties, type ReactNode } from "react";
import { ImplementationHandoffPanel } from "@/components/implementation-plan/implementation-handoff-panel";
import { WorkspaceNav } from "@/components/workspace/workspace-nav";
import {
  approveImplementationPlan,
  buildImplementationPlanDraft,
  prepareImplementationPlanForHandoff,
  submitImplementationPlanReview,
} from "@/lib/api/endpoints/implementation-plans";
import { fetchLatestMarketingStrategy } from "@/lib/api/endpoints/marketing-strategies";
import { PRODUCT_BRAND } from "@/lib/brand/product-brand";
import { preparePlanForProject, ensureVerdict } from "@/lib/implementation-plan/mock-plans";
import {
  implementationHref,
  redirectHref,
  resolveImplementationAccess,
  strategyHref,
  verdictHref,
} from "@/lib/implementation-plan/routing";
import {
  gateStatusLabel,
  planStatusLabel,
  planningReadinessColor,
  planningReadinessLabel,
  taskStatusLabel,
  workstreamStatusLabel,
} from "@/lib/implementation-plan/selectors";
import {
  listPlanVersions,
  updatePlanStatus,
} from "@/lib/implementation-plan/storage";
import type {
  AgencyRole,
  ImplementationPlan,
  PlanPriority,
  TaskStatus,
} from "@/lib/implementation-plan/types";
import {
  futureExecutionChainDocumented,
  loadImplementationPlanWorkspace,
  type ImplementationLoadResult,
} from "@/lib/integration/implementation-plan-adapter";
import { getIntegrationMode } from "@/lib/integration/mode";
import { prepareStrategyForProject } from "@/lib/strategy/mock-strategies";
import { getCurrentStrategy } from "@/lib/strategy/storage";
import { VERDICT_SCENARIO_PROJECT } from "@/lib/verdict/mock-verdicts";
import { verdictGlyph, verdictTokenVar } from "@/lib/verdict/selectors";

type Props = { projectId: string };

type TaskFilters = {
  status: TaskStatus | "all";
  workstream: string | "all";
  owner: AgencyRole | "all";
  milestone: string | "all";
  priority: PlanPriority | "all";
  blocker: "all" | "blocked" | "clear";
  approval: "all" | "required" | "not_required";
};

const defaultFilters: TaskFilters = {
  status: "all",
  workstream: "all",
  owner: "all",
  milestone: "all",
  priority: "all",
  blocker: "all",
  approval: "all",
};

export function ImplementationPlanWorkspaceView({ projectId }: Props) {
  const router = useRouter();
  const [plan, setPlan] = useState<ImplementationPlan | null>(null);
  const [versions, setVersions] = useState<ImplementationPlan[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [blocked, setBlocked] = useState<{ reason: string; href: string } | null>(
    null,
  );
  const [loaded, setLoaded] = useState(false);
  const [filters, setFilters] = useState<TaskFilters>(defaultFilters);
  const [integrationLoad, setIntegrationLoad] =
    useState<ImplementationLoadResult | null>(null);
  const [lifecycleBusy, setLifecycleBusy] = useState(false);
  const mode = getIntegrationMode();

  const refresh = useCallback(async () => {
    const result = await loadImplementationPlanWorkspace(projectId);
    setIntegrationLoad(result);

    if (mode === "backend") {
      setPlan(result.view?.plan ?? null);
      setVersions(result.view?.versions ?? []);
      setNotice(
        result.view?.plan
          ? "Backend ImplementationPlan + P1.2 handoff. Lifecycle ниже. Mock не подставляется."
          : "Backend mode: durable ImplementationPlan отсутствует. Соберите draft явно из approved Strategy.",
      );
      return;
    }

    const verdict = ensureVerdict(projectId);
    let strategy = getCurrentStrategy(projectId);
    try {
      if (!strategy && (verdict.type === "GO" || verdict.type === "CONDITIONAL_GO")) {
        strategy = prepareStrategyForProject(projectId);
      }
    } catch {
      strategy = null;
    }

    const access = resolveImplementationAccess(verdict, strategy);
    if (!access.allow) {
      const href = redirectHref(projectId, access.redirect);
      setBlocked({ reason: access.reason, href });
      router.replace(href);
      return;
    }

    try {
      const p = result.view?.plan ?? preparePlanForProject(projectId);
      setPlan(p);
      setVersions(
        result.view?.versions.length
          ? result.view.versions
          : listPlanVersions(projectId),
      );
      if (mode === "hybrid") {
        setNotice(
          "Hybrid: локальный Implementation Plan + backend P1.2 draft handoff (только из durable approved ImplementationPlan).",
        );
      }
    } catch (e) {
      setBlocked({
        reason: e instanceof Error ? e.message : "Plan blocked",
        href: strategyHref(projectId),
      });
    }
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

  const onBuildImplDraft = async () => {
    setLifecycleBusy(true);
    try {
      const strategy = await fetchLatestMarketingStrategy(projectId);
      if (strategy.lifecycle_status !== "approved") {
        setNotice(
          `Нужна approved MarketingStrategy (сейчас: ${strategy.lifecycle_status}).`,
        );
        return;
      }
      await buildImplementationPlanDraft(projectId, strategy.id);
      setNotice("Draft ImplementationPlan собран. Campaign / Execution не создавались.");
      await refresh();
    } catch (err) {
      setNotice(
        err instanceof Error ? err.message : "Не удалось собрать draft ImplementationPlan.",
      );
    } finally {
      setLifecycleBusy(false);
    }
  };

  const onPrepareImplHandoff = async () => {
    const planId = plan?.id ?? integrationLoad?.view?.plan?.id;
    if (!planId) return;
    setLifecycleBusy(true);
    try {
      const updated = await prepareImplementationPlanForHandoff(projectId, planId);
      setNotice(
        `Локальные gates сняты. readiness=${updated.readiness_status}. MarketingPlan ещё не создан.`,
      );
      await refresh();
    } catch (err) {
      setNotice(
        err instanceof Error
          ? err.message
          : "Не удалось подготовить ImplementationPlan к handoff.",
      );
    } finally {
      setLifecycleBusy(false);
    }
  };

  const onSubmitImplReview = async () => {
    const planId = plan?.id ?? integrationLoad?.view?.plan?.id;
    if (!planId) return;
    setLifecycleBusy(true);
    try {
      await submitImplementationPlanReview(projectId, planId);
      setNotice("ImplementationPlan отправлен на проверку (under_review).");
      await refresh();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Не удалось отправить план на проверку.");
    } finally {
      setLifecycleBusy(false);
    }
  };

  const onApproveImpl = async () => {
    const planId = plan?.id ?? integrationLoad?.view?.plan?.id;
    if (!planId) return;
    setLifecycleBusy(true);
    try {
      await approveImplementationPlan(projectId, planId);
      setNotice(
        "ImplementationPlan утверждён. Handoff preview обновится при readiness ready_for_handoff.",
      );
      await refresh();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Не удалось утвердить план.");
    } finally {
      setLifecycleBusy(false);
    }
  };

  const filteredTasks = useMemo(() => {
    if (!plan) return [];
    return plan.tasks.filter((t) => {
      if (filters.status !== "all" && t.status !== filters.status) return false;
      if (filters.workstream !== "all" && t.workstreamId !== filters.workstream) {
        return false;
      }
      if (filters.owner !== "all" && t.responsibleRole !== filters.owner) return false;
      if (filters.milestone !== "all" && t.milestoneId !== filters.milestone) {
        return false;
      }
      if (filters.priority !== "all" && t.priority !== filters.priority) return false;
      if (filters.blocker === "blocked" && t.status !== "blocked") return false;
      if (filters.blocker === "clear" && t.status === "blocked") return false;
      if (filters.approval === "required" && !t.approvalRequired) return false;
      if (filters.approval === "not_required" && t.approvalRequired) return false;
      return true;
    });
  }, [plan, filters]);

  if (!loaded) {
    return <ShellCenter>Проверка доступа к Implementation Plan…</ShellCenter>;
  }

  if (mode === "backend") {
    const backendPlan = plan ?? integrationLoad?.view?.plan ?? null;
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
              {PRODUCT_BRAND.displayName} · Implementation Plan
            </p>
            <h1 className="mt-1 text-lg font-semibold">
              {integrationLoad?.projectName ?? "Project"}
            </h1>
            {notice ? (
              <p className="mt-3 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
                {notice}
              </p>
            ) : null}
          </header>
          <ImplementationHandoffPanel
            load={integrationLoad}
            projectId={projectId}
            implementationPlanId={
              backendPlan?.id && !String(backendPlan.id).startsWith("local")
                ? backendPlan.id
                : backendPlan?.id ?? null
            }
            implementationPlanVersion={backendPlan?.version ?? null}
          />
          <div className="mx-auto max-w-2xl space-y-3 p-6 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
            <p>
              Option B: ImplementationPlan — higher-level delivery plan.
              MarketingPlan — executable specialist-task spine (backend SoT). Они не равны.
            </p>
            {backendPlan ? (
              <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                Plan v{backendPlan.version} · {planStatusLabel(backendPlan.status)} · readiness{" "}
                {backendPlan.readiness.status}
              </p>
            ) : (
              <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                Durable ImplementationPlan ещё нет.
              </p>
            )}
            <div className="flex flex-wrap gap-2">
              {!backendPlan ? (
                <button
                  type="button"
                  data-testid="impl-build-draft"
                  disabled={lifecycleBusy}
                  onClick={() => void onBuildImplDraft()}
                  className="rounded-md px-3 py-2 text-xs font-semibold disabled:opacity-50"
                  style={secondaryBtn}
                >
                  Собрать draft ImplementationPlan
                </button>
              ) : null}
              {backendPlan?.status === "draft" ? (
                <>
                  <button
                    type="button"
                    data-testid="impl-prepare-handoff"
                    disabled={lifecycleBusy}
                    onClick={() => void onPrepareImplHandoff()}
                    className="rounded-md px-3 py-2 text-xs font-semibold disabled:opacity-50"
                    style={secondaryBtn}
                  >
                    Подготовить к handoff (снять локальные gates)
                  </button>
                  <button
                    type="button"
                    data-testid="impl-submit-review"
                    disabled={lifecycleBusy}
                    onClick={() => void onSubmitImplReview()}
                    className="rounded-md px-3 py-2 text-xs font-semibold disabled:opacity-50"
                    style={secondaryBtn}
                  >
                    Отправить план на проверку
                  </button>
                </>
              ) : null}
              {backendPlan?.status === "under_review" ? (
                <button
                  type="button"
                  data-testid="impl-approve"
                  disabled={lifecycleBusy}
                  onClick={() => void onApproveImpl()}
                  className="rounded-md px-3 py-2 text-xs font-semibold disabled:opacity-50"
                  style={secondaryBtn}
                >
                  Утвердить план
                </button>
              ) : null}
              <Link href={strategyHref(projectId)} className="text-sm" style={{ color: "var(--brand-blue-light)" }}>
                ← Strategy
              </Link>
            </div>
            <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
              Future chain: {futureExecutionChainDocumented().join(" → ")}. A7 paused.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (blocked || !plan) {
    return (
      <ShellCenter>
        <p className="max-w-lg text-center text-sm" style={{ color: "var(--ms-text-secondary)" }}>
          {blocked?.reason ?? "Implementation plan unavailable"}
        </p>
        <Link
          href={blocked?.href ?? strategyHref(projectId)}
          className="mt-4 text-sm font-medium"
          style={{ color: "var(--brand-blue-light)" }}
        >
          Перейти
        </Link>
      </ShellCenter>
    );
  }

  const color = verdictTokenVar(plan.verdictType);
  const readiness = plan.readiness;
  const readinessColor = planningReadinessColor(readiness.status);
  const ctaDisabled =
    readiness.status === "blocked" || readiness.status === "not_ready";
  const wsTitle = (id: string) =>
    plan.workstreams.find((w) => w.id === id)?.title ?? id;
  const msTitle = (id: string) =>
    plan.milestones.find((m) => m.id === id)?.title ?? id;

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
                {PRODUCT_BRAND.displayName} · Implementation Plan
              </p>
              <h1 className="mt-1 text-lg font-semibold sm:text-xl">{plan.projectName}</h1>
              <div className="mt-2 flex flex-wrap gap-2 text-xs">
                <span
                  className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 font-semibold"
                  style={{
                    background: `color-mix(in srgb, ${color} 22%, transparent)`,
                    color,
                  }}
                >
                  <span aria-hidden>{verdictGlyph(plan.verdictType)}</span>
                  {plan.verdictType} · verdict v{plan.verdictVersion}
                </span>
                <Pill>Strategy v{plan.strategyVersion}</Pill>
                <Pill>Plan v{plan.version}</Pill>
                <Pill muted>{planStatusLabel(plan.status)}</Pill>
                <span
                  className="rounded-full px-2.5 py-0.5 font-semibold"
                  style={{
                    background: `color-mix(in srgb, ${readinessColor} 20%, transparent)`,
                    color: readinessColor,
                  }}
                  aria-label={`Execution planning readiness: ${planningReadinessLabel(readiness.status)}`}
                >
                  Planning: {planningReadinessLabel(readiness.status)}
                </span>
                <Pill muted>{plan.localMockLabel}</Pill>
              </div>
              <p className="mt-2 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                Evidence: {plan.evidenceSnapshotId} · Updated {plan.updatedAtLabel}
              </p>
              <div className="mt-2 flex flex-wrap gap-3 text-xs">
                <Link href={strategyHref(projectId)} style={{ color: "var(--brand-blue-light)" }}>
                  ← Strategy
                </Link>
                <Link href={verdictHref(projectId)} style={{ color: "var(--brand-blue-light)" }}>
                  Verdict
                </Link>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <DemoLink
                href={implementationHref(VERDICT_SCENARIO_PROJECT.go)}
                label="Demo GO"
              />
              <DemoLink
                href={implementationHref(VERDICT_SCENARIO_PROJECT.conditional_go)}
                label="Demo CONDITIONAL"
              />
            </div>
          </div>
          {notice ? (
            <p className="mt-3 rounded-md border px-3 py-2 text-sm" style={noticeBox} role="status">
              {notice}
            </p>
          ) : null}
        </header>

        <ImplementationHandoffPanel
          load={integrationLoad}
          projectId={projectId}
          implementationPlanId={
            mode === "mock" ? null : (integrationLoad?.view?.plan?.id ?? plan?.id ?? null)
          }
          implementationPlanVersion={
            mode === "mock"
              ? null
              : (integrationLoad?.view?.plan?.version ?? plan?.version ?? null)
          }
        />

        <div className="space-y-4 p-4 sm:space-y-5 sm:p-6">
          {plan.conditions.some((c) => c.blocksPlanning) ? (
            <Panel title="Mandatory conditions (CONDITIONAL_GO)">
              <p className="mb-3 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                Неразрешённые условия блокируют execution planning readiness.
              </p>
              <div className="space-y-3">
                {plan.conditions
                  .filter((c) => c.blocksPlanning)
                  .map((c) => (
                    <article key={c.id} className="rounded-lg border p-3 text-sm" style={card}>
                      <h3 className="font-semibold">{c.requiredAction}</h3>
                      <dl className="mt-2 grid gap-1 text-xs sm:grid-cols-2" style={{ color: "var(--ms-text-secondary)" }}>
                        <div>
                          <dt className="font-semibold">Owner</dt>
                          <dd>{c.ownerRole}</dd>
                        </div>
                        <div>
                          <dt className="font-semibold">Status</dt>
                          <dd>{c.status}</dd>
                        </div>
                        <div>
                          <dt className="font-semibold">Validation</dt>
                          <dd>{c.validationMethod}</dd>
                        </div>
                        <div>
                          <dt className="font-semibold">Success</dt>
                          <dd>{c.successCriterion}</dd>
                        </div>
                        <div>
                          <dt className="font-semibold">Evidence</dt>
                          <dd>{c.evidenceRequired}</dd>
                        </div>
                        <div>
                          <dt className="font-semibold">Execution impact</dt>
                          <dd>{c.executionImpact}</dd>
                        </div>
                      </dl>
                    </article>
                  ))}
              </div>
            </Panel>
          ) : null}

          <Panel title="Plan overview">
            <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
              <Field label="Strategic objective" value={plan.overview.strategicObjective} />
              <Field label="Horizon" value={plan.overview.implementationHorizon} />
              <Field label="Budget range" value={plan.overview.estimatedBudgetRange} />
              <Field label="Readiness" value={plan.overview.readinessLabel} />
              <Field label="Next decision" value={plan.overview.nextManagementDecision} />
              <Field
                label="Primary workstreams"
                value={plan.overview.primaryWorkstreams.join(" · ")}
              />
            </dl>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <List title="Critical milestones" items={plan.overview.criticalMilestones} />
              <List title="Mandatory conditions" items={plan.overview.mandatoryConditions} />
              <List title="Current blockers" items={plan.overview.currentBlockers} />
            </div>
          </Panel>

          <Panel title="Execution planning readiness">
            <p className="text-sm font-semibold" style={{ color: readinessColor }}>
              {planningReadinessLabel(readiness.status)}
              <span className="sr-only"> — not real execution</span>
            </p>
            <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
              Readiness ≠ real execution. No provider or budget actions.
            </p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 text-sm">
              <List title="Blockers" items={readiness.blockers} />
              <List title="Unresolved gates" items={readiness.unresolvedGates} />
              <List title="Incomplete workstreams" items={readiness.incompleteWorkstreams} />
              <List title="Critical missing inputs" items={readiness.criticalMissingInputs} />
            </div>
            <p className="mt-3 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
              Recommended: {readiness.recommendedNextAction}
            </p>
            <button
              type="button"
              className="mt-4 rounded-md px-5 py-2.5 text-sm font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-40"
              style={{
                background: "var(--ms-brand-primary)",
                color: "var(--ms-text-primary)",
                outlineColor: "var(--brand-blue-light)",
              }}
              disabled={ctaDisabled}
              aria-disabled={ctaDisabled}
              onClick={() => {
                if (ctaDisabled) return;
                router.push(`/workspace/projects/${projectId}/execution-package`);
              }}
            >
              Подготовить пакет исполнения
            </button>
          </Panel>

          <Panel title="Roadmap (relative horizons)">
            <ol className="space-y-3">
              {plan.roadmap.map((phase) => (
                <li key={phase.id} className="rounded-lg border p-3" style={card}>
                  <h3 className="text-sm font-semibold">{phase.horizon}</h3>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    {phase.note}
                  </p>
                  <p className="mt-2 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                    Milestones: {phase.milestoneIds.map(msTitle).join(" · ") || "—"}
                  </p>
                  <p className="text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                    Workstreams: {phase.workstreamIds.map(wsTitle).join(" · ") || "—"}
                  </p>
                </li>
              ))}
            </ol>
          </Panel>

          <Panel title="Workstreams">
            <div className="space-y-3">
              {plan.workstreams.map((ws) => (
                <article key={ws.id} className="rounded-lg border p-3 text-sm" style={card}>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="font-semibold">{ws.title}</h3>
                    <span className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                      {workstreamStatusLabel(ws.status)} · {ws.priority} · {ws.ownerRole}
                    </span>
                  </div>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                    {ws.purpose}
                  </p>
                  <dl className="mt-2 grid gap-1 text-xs sm:grid-cols-2" style={{ color: "var(--ms-text-secondary)" }}>
                    <div>
                      <dt className="font-semibold">Horizon</dt>
                      <dd>
                        {ws.plannedStart} → {ws.plannedFinish}
                      </dd>
                    </div>
                    <div>
                      <dt className="font-semibold">Budget</dt>
                      <dd>{ws.budgetRange}</dd>
                    </div>
                    <div>
                      <dt className="font-semibold">Success</dt>
                      <dd>{ws.successCriteria}</dd>
                    </div>
                    <div>
                      <dt className="font-semibold">Blockers</dt>
                      <dd>{ws.blockers}</dd>
                    </div>
                  </dl>
                </article>
              ))}
            </div>
          </Panel>

          <Panel title="Milestones">
            <div className="space-y-3">
              {plan.milestones.map((m) => (
                <article key={m.id} className="rounded-lg border p-3 text-sm" style={card}>
                  <h3 className="font-semibold">{m.title}</h3>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                    {m.description}
                  </p>
                  <p className="mt-2 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    {m.targetPeriod} · {workstreamStatusLabel(m.status)}
                    {m.approvalRequired ? " · approval required" : ""}
                  </p>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                    Entry: {m.entryCriteria} · Exit: {m.exitCriteria}
                  </p>
                </article>
              ))}
            </div>
          </Panel>

          <Panel title="Tasks">
            <fieldset className="mb-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              <legend className="sr-only">Task filters</legend>
              <FilterSelect
                label="Status"
                value={filters.status}
                onChange={(v) => setFilters((f) => ({ ...f, status: v as TaskFilters["status"] }))}
                options={[
                  "all",
                  "backlog",
                  "ready",
                  "blocked",
                  "in_progress",
                  "review",
                  "approved",
                  "completed",
                  "cancelled",
                ]}
              />
              <FilterSelect
                label="Workstream"
                value={filters.workstream}
                onChange={(v) => setFilters((f) => ({ ...f, workstream: v }))}
                options={["all", ...plan.workstreams.map((w) => w.id)]}
                labels={Object.fromEntries(plan.workstreams.map((w) => [w.id, w.title]))}
              />
              <FilterSelect
                label="Owner"
                value={filters.owner}
                onChange={(v) =>
                  setFilters((f) => ({ ...f, owner: v as TaskFilters["owner"] }))
                }
                options={["all", ...Array.from(new Set(plan.tasks.map((t) => t.responsibleRole)))]}
              />
              <FilterSelect
                label="Milestone"
                value={filters.milestone}
                onChange={(v) => setFilters((f) => ({ ...f, milestone: v }))}
                options={["all", ...plan.milestones.map((m) => m.id)]}
                labels={Object.fromEntries(plan.milestones.map((m) => [m.id, m.title]))}
              />
              <FilterSelect
                label="Priority"
                value={filters.priority}
                onChange={(v) =>
                  setFilters((f) => ({ ...f, priority: v as TaskFilters["priority"] }))
                }
                options={["all", "critical", "high", "medium", "low"]}
              />
              <FilterSelect
                label="Blocker"
                value={filters.blocker}
                onChange={(v) =>
                  setFilters((f) => ({ ...f, blocker: v as TaskFilters["blocker"] }))
                }
                options={["all", "blocked", "clear"]}
              />
              <FilterSelect
                label="Approval"
                value={filters.approval}
                onChange={(v) =>
                  setFilters((f) => ({ ...f, approval: v as TaskFilters["approval"] }))
                }
                options={["all", "required", "not_required"]}
              />
            </fieldset>

            <div className="hidden overflow-x-auto md:block">
              <table className="w-full min-w-[720px] text-left text-xs">
                <thead>
                  <tr style={{ color: "var(--ms-text-muted)" }}>
                    <th className="pb-2 pr-2 font-semibold">Task</th>
                    <th className="pb-2 pr-2 font-semibold">Workstream</th>
                    <th className="pb-2 pr-2 font-semibold">Owner</th>
                    <th className="pb-2 pr-2 font-semibold">Status</th>
                    <th className="pb-2 pr-2 font-semibold">Priority</th>
                    <th className="pb-2 font-semibold">Acceptance</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTasks.map((t) => (
                    <tr key={t.id} className="border-t" style={{ borderColor: "var(--ms-border-default)" }}>
                      <td className="py-2 pr-2 align-top">
                        <span className="font-medium">{t.title}</span>
                        <p style={{ color: "var(--ms-text-muted)" }}>{t.description}</p>
                      </td>
                      <td className="py-2 pr-2 align-top">{wsTitle(t.workstreamId)}</td>
                      <td className="py-2 pr-2 align-top">{t.responsibleRole}</td>
                      <td className="py-2 pr-2 align-top">{taskStatusLabel(t.status)}</td>
                      <td className="py-2 pr-2 align-top">{t.priority}</td>
                      <td className="py-2 align-top">{t.acceptanceCriteria}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="space-y-3 md:hidden">
              {filteredTasks.map((t) => (
                <article key={t.id} className="rounded-lg border p-3 text-sm" style={card}>
                  <h3 className="font-semibold">{t.title}</h3>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                    {t.description}
                  </p>
                  <p className="mt-2 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    {taskStatusLabel(t.status)} · {t.priority} · {t.responsibleRole}
                    {t.approvalRequired ? " · approval required" : ""}
                  </p>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                    {wsTitle(t.workstreamId)} · {msTitle(t.milestoneId)}
                  </p>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                    Acceptance: {t.acceptanceCriteria}
                  </p>
                </article>
              ))}
            </div>
          </Panel>

          <Panel title="Responsible roles">
            <div className="grid gap-3 sm:grid-cols-2">
              {plan.roles.map((r) => (
                <article key={r.role} className="rounded-lg border p-3 text-sm" style={card}>
                  <h3 className="font-semibold">{r.role}</h3>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                    {r.responsibility}
                  </p>
                  <p className="mt-2 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    Authority: {r.decisionAuthority}
                  </p>
                  <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    Review: {r.reviewRelationship}
                  </p>
                </article>
              ))}
            </div>
          </Panel>

          <Panel title="Dependency map">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-xs">
                <thead>
                  <tr style={{ color: "var(--ms-text-muted)" }}>
                    <th className="pb-2 pr-2 font-semibold">Predecessor</th>
                    <th className="pb-2 pr-2 font-semibold">Successor</th>
                    <th className="pb-2 pr-2 font-semibold">Type</th>
                    <th className="pb-2 pr-2 font-semibold">Blocking</th>
                    <th className="pb-2 font-semibold">Resolution</th>
                  </tr>
                </thead>
                <tbody>
                  {plan.dependencies.map((d) => (
                    <tr key={d.id} className="border-t" style={{ borderColor: "var(--ms-border-default)" }}>
                      <td className="py-2 pr-2 align-top">{d.predecessor}</td>
                      <td className="py-2 pr-2 align-top">{d.successor}</td>
                      <td className="py-2 pr-2 align-top">{d.type}</td>
                      <td className="py-2 pr-2 align-top">{d.blocking ? "yes" : "no"}</td>
                      <td className="py-2 align-top">{d.resolutionAction}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>

          <Panel title="Deliverables register">
            <ul className="space-y-2 text-sm">
              {plan.deliverables.map((d) => (
                <li key={d.id} className="rounded-lg border p-3" style={card}>
                  <span className="font-semibold">{d.name}</span>
                  <span className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    {" "}
                    · {d.type} · {d.ownerRole} · {taskStatusLabel(d.status)} · {d.duePeriod}
                  </span>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                    Linked: {d.linkedStrategyElement} · Acceptance: {d.acceptanceCriteria}
                  </p>
                </li>
              ))}
            </ul>
          </Panel>

          <Panel title="Budget plan (ranges)">
            <div className="space-y-3">
              {plan.budgetPlan.map((b) => (
                <article key={b.id} className="rounded-lg border p-3 text-sm" style={card}>
                  <h3 className="font-semibold">{b.category}</h3>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    Mode: {b.mode} · Min: {b.minimum} · Recommended: {b.recommendedRange} ·
                    Upper: {b.upperBoundary}
                  </p>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                    {b.rationale} · Release: {b.releaseCondition}
                  </p>
                </article>
              ))}
            </div>
          </Panel>

          <Panel title="Budget gates">
            <ul className="space-y-2 text-sm" aria-label="Budget gates">
              {plan.budgetGates.map((g) => (
                <li key={g.id} className="rounded-lg border p-3" style={card}>
                  <span className="font-semibold">{g.name}</span>
                  <span className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    {" "}
                    · {gateStatusLabel(g.status)} · {g.amountOrRange}
                  </span>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                    Owner: {g.approvalOwner} · Prerequisite: {g.prerequisite}
                  </p>
                </li>
              ))}
            </ul>
          </Panel>

          <Panel title="Approval gates">
            <ul className="space-y-2 text-sm" aria-label="Approval gates">
              {plan.approvalGates.map((g) => (
                <li key={g.id} className="rounded-lg border p-3" style={card}>
                  <span className="font-semibold">{g.title}</span>
                  <span className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    {" "}
                    · {gateStatusLabel(g.status)} · {g.decisionOwner}
                  </span>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                    Artifacts: {g.requiredArtifacts.join(", ")} · If rejected:{" "}
                    {g.consequenceIfRejected}
                  </p>
                </li>
              ))}
            </ul>
          </Panel>

          <Panel title="Implementation risks">
            <div className="space-y-3">
              {plan.risks.map((r) => (
                <article key={r.id} className="rounded-lg border p-3 text-sm" style={card}>
                  <h3 className="font-semibold">{r.title}</h3>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    {r.probability} · {r.severity} · {r.status} · {r.ownerRole}
                  </p>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                    Mitigation: {r.mitigation}
                  </p>
                  <p className="text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                    Stop: {r.stopCondition}
                  </p>
                </article>
              ))}
            </div>
          </Panel>

          <Panel title="Assumptions register">
            <ul className="space-y-2 text-sm">
              {plan.assumptions.map((a) => (
                <li key={a.id} className="rounded-lg border p-3" style={card}>
                  <span className="font-semibold">{a.statement}</span>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    {a.status} · {a.confidence} · {a.owner}
                  </p>
                  <p className="text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                    If false: {a.impactIfFalse} · Validate: {a.validationAction}
                  </p>
                </li>
              ))}
            </ul>
          </Panel>

          <Panel title="Local review & versions">
            <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
              Product Alpha local only — не backend approval.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <ActionBtn
                onClick={() => {
                  updatePlanStatus(projectId, plan.id, "draft");
                  setPlan({ ...plan, status: "draft" });
                  setNotice("Draft сохранён локально.");
                }}
              >
                Save draft
              </ActionBtn>
              <ActionBtn
                onClick={() => {
                  updatePlanStatus(projectId, plan.id, "under_review");
                  setPlan({ ...plan, status: "under_review" });
                  setNotice("Отправлено на проверку (local).");
                }}
              >
                Send for review
              </ActionBtn>
              <ActionBtn
                onClick={() => {
                  if (readiness.status === "blocked") {
                    setNotice("Нельзя утвердить: planning readiness blocked.");
                    return;
                  }
                  updatePlanStatus(projectId, plan.id, "approved");
                  setPlan({ ...plan, status: "approved" });
                  setNotice("План утверждён локально.");
                }}
              >
                Approve plan
              </ActionBtn>
              <ActionBtn
                onClick={() => {
                  const next = preparePlanForProject(projectId, { regenerate: true });
                  setPlan(next);
                  setVersions(listPlanVersions(projectId));
                  setNotice(`Новая версия v${next.version}; предыдущая superseded.`);
                }}
              >
                Create new version
              </ActionBtn>
            </div>
            <ul className="mt-3 space-y-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
              {versions.map((v) => (
                <li key={v.id}>
                  v{v.version} · {v.verdictType} · {planStatusLabel(v.status)}
                  {v.id === plan.id ? " · current" : ""}
                </li>
              ))}
            </ul>
          </Panel>

          <Panel title="Execution handoff (paused · I6)">
            <p className="mb-3 text-xs" style={{ color: "var(--ms-text-muted)" }}>
              A7 Execution Package paused. Local ImplPlan approval ≠ MarketingPlan approve ≠
              execution/publication approval. Backend refs: MarketingPlan approve, execution
              readiness, execution-approvals, publication path — not called from this page.
            </p>
            <p className="mb-3 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
              {futureExecutionChainDocumented().join(" → ")}
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled
                className="rounded-md px-3 py-2 text-xs opacity-40"
                style={secondaryBtn}
                title="Create MarketingPlan draft — blocked until handoff API"
              >
                Создать черновик MarketingPlan · blocked
              </button>
              {[
                "Execution Package (A7 paused)",
                "Campaign Planning",
                "Asset Production",
                "Provider Configuration",
                "Budget Approval",
                "Real Execution",
              ].map((label) => (
                <button
                  key={label}
                  type="button"
                  disabled
                  className="rounded-md px-3 py-2 text-xs opacity-40"
                  style={secondaryBtn}
                >
                  {label}
                </button>
              ))}
            </div>
            <List
              title="Gates before execution can begin"
              items={[
                ...plan.approvalGates
                  .filter((g) => g.status !== "approved" && g.status !== "not_required")
                  .map((g) => `${g.title}: ${gateStatusLabel(g.status)}`),
                ...plan.budgetGates
                  .filter((g) => g.status !== "approved" && g.status !== "not_required")
                  .map((g) => `${g.name}: ${gateStatusLabel(g.status)}`),
              ]}
            />
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

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-semibold" style={{ color: "var(--ms-text-muted)" }}>
        {label}
      </dt>
      <dd className="mt-1" style={{ color: "var(--ms-text-secondary)" }}>
        {value}
      </dd>
    </div>
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

function FilterSelect({
  label,
  value,
  onChange,
  options,
  labels,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
  labels?: Record<string, string>;
}) {
  return (
    <label className="block text-xs">
      <span className="font-semibold" style={{ color: "var(--ms-text-muted)" }}>
        {label}
      </span>
      <select
        className="mt-1 w-full rounded-md border px-2 py-1.5 text-xs focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
        style={{
          background: "var(--ms-bg-elevated)",
          borderColor: "var(--ms-border-default)",
          color: "var(--ms-text-primary)",
          outlineColor: "var(--brand-blue-light)",
        }}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {labels?.[o] ?? o}
          </option>
        ))}
      </select>
    </label>
  );
}

function ActionBtn({ children, onClick }: { children: ReactNode; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-md px-3 py-2 text-xs font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
      style={{ ...secondaryBtn, outlineColor: "var(--brand-blue-light)" }}
    >
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
