"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type CSSProperties, type ReactNode } from "react";
import { WorkspaceNav } from "@/components/workspace/workspace-nav";
import { PRODUCT_BRAND } from "@/lib/brand/product-brand";
import {
  preparePackageForProject,
  runLocalDryRun,
} from "@/lib/execution-package/mock-packages";
import {
  executionPackageHref,
  implementationHref,
  redirectPackageHref,
  resolvePackageAccess,
  strategyHref,
  verdictHref,
} from "@/lib/execution-package/routing";
import {
  dryRunResultLabel,
  gateStatusLabel,
  packageReadinessColor,
  packageReadinessLabel,
  packageStatusLabel,
  preflightResultLabel,
} from "@/lib/execution-package/selectors";
import {
  listPackageVersions,
  replaceCurrentPackage,
  updatePackageStatus,
} from "@/lib/execution-package/storage";
import { refreshPackageDerived } from "@/lib/execution-package/build-package";
import type { ExecutionPackage } from "@/lib/execution-package/types";
import { preparePlanForProject, ensureVerdict } from "@/lib/implementation-plan/mock-plans";
import { getCurrentPlan } from "@/lib/implementation-plan/storage";
import { getIntegrationMode, integrationModeLabel } from "@/lib/integration/mode";
import { prepareStrategyForProject } from "@/lib/strategy/mock-strategies";
import { getCurrentStrategy } from "@/lib/strategy/storage";
import { VERDICT_SCENARIO_PROJECT } from "@/lib/verdict/mock-verdicts";
import { verdictGlyph, verdictTokenVar } from "@/lib/verdict/selectors";

type Props = { projectId: string };

export function ExecutionPackageWorkspaceView({ projectId }: Props) {
  const router = useRouter();
  const [pkg, setPkg] = useState<ExecutionPackage | null>(null);
  const [versions, setVersions] = useState<ExecutionPackage[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [blocked, setBlocked] = useState<{ reason: string; href: string } | null>(
    null,
  );
  const [loaded, setLoaded] = useState(false);
  const [backendPaused, setBackendPaused] = useState(false);
  const mode = getIntegrationMode();

  useEffect(() => {
    // I7: A7 remains paused. Backend mode must not invent local package as success.
    if (mode === "backend") {
      setPkg(null);
      setVersions([]);
      setBackendPaused(true);
      setNotice(
        "A7 Execution Package paused. Backend mode: local mock package not substituted as live execution SoT.",
      );
      setLoaded(true);
      return;
    }

    const verdict = ensureVerdict(projectId);
    let strategy = getCurrentStrategy(projectId);
    let plan = getCurrentPlan(projectId);
    try {
      if (!strategy && (verdict.type === "GO" || verdict.type === "CONDITIONAL_GO")) {
        strategy = prepareStrategyForProject(projectId);
      }
      if (!plan && strategy) {
        plan = preparePlanForProject(projectId);
      }
    } catch {
      /* access resolver handles */
    }

    const access = resolvePackageAccess(verdict, strategy, plan);
    if (!access.allow) {
      const href = redirectPackageHref(projectId, access.redirect);
      setBlocked({ reason: access.reason, href });
      setLoaded(true);
      router.replace(href);
      return;
    }

    try {
      const p = preparePackageForProject(projectId);
      setPkg(p);
      setVersions(listPackageVersions(projectId));
      if (mode === "hybrid") {
        setNotice(
          "Hybrid · A7 paused prototype. Local dry-run only — not MarketingPlan execution / provider SoT.",
        );
      }
    } catch (e) {
      setBlocked({
        reason: e instanceof Error ? e.message : "Package blocked",
        href: implementationHref(projectId),
      });
    }
    setLoaded(true);
  }, [projectId, router, mode]);

  if (!loaded) {
    return <ShellCenter>Проверка доступа к Execution Package…</ShellCenter>;
  }

  if (backendPaused) {
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
            {PRODUCT_BRAND.displayName} · Execution Package
          </p>
          <h1 className="text-lg font-semibold">A7 paused · backend mode</h1>
          <p className="text-sm" style={{ color: "var(--ms-text-secondary)" }}>
            {notice}
          </p>
          <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
            {integrationModeLabel(mode)}. No Agent Run / provider / publication started.
          </p>
          <Link
            href={implementationHref(projectId)}
            className="text-sm font-medium"
            style={{ color: "var(--brand-blue-light)" }}
          >
            ← Implementation Plan
          </Link>
        </div>
      </div>
    );
  }

  if (blocked || !pkg) {
    return (
      <ShellCenter>
        <p className="max-w-lg text-center text-sm" style={{ color: "var(--ms-text-secondary)" }}>
          {blocked?.reason ?? "Execution package unavailable"}
        </p>
        <Link
          href={blocked?.href ?? implementationHref(projectId)}
          className="mt-4 text-sm font-medium"
          style={{ color: "var(--brand-blue-light)" }}
        >
          Перейти
        </Link>
      </ShellCenter>
    );
  }

  const color = verdictTokenVar(pkg.verdictType);
  const readiness = pkg.readiness;
  const readinessColor = packageReadinessColor(readiness.status);
  const dryRunDisabled =
    readiness.status === "blocked" || readiness.status === "not_ready";

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
                {PRODUCT_BRAND.displayName} · Execution Package
              </p>
              <h1 className="mt-1 text-lg font-semibold sm:text-xl">{pkg.projectName}</h1>
              <div className="mt-2 flex flex-wrap gap-2 text-xs">
                <span
                  className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 font-semibold"
                  style={{
                    background: `color-mix(in srgb, ${color} 22%, transparent)`,
                    color,
                  }}
                >
                  <span aria-hidden>{verdictGlyph(pkg.verdictType)}</span>
                  {pkg.verdictType} · verdict v{pkg.verdictVersion}
                </span>
                <Pill>Strategy v{pkg.strategyVersion}</Pill>
                <Pill>Plan v{pkg.implementationPlanVersion}</Pill>
                <Pill>Package v{pkg.version}</Pill>
                <Pill muted>{packageStatusLabel(pkg.status)}</Pill>
                <span
                  className="rounded-full px-2.5 py-0.5 font-semibold"
                  style={{
                    background: `color-mix(in srgb, ${readinessColor} 20%, transparent)`,
                    color: readinessColor,
                  }}
                  aria-label={`Execution readiness: ${packageReadinessLabel(readiness.status)}`}
                >
                  Readiness: {packageReadinessLabel(readiness.status)}
                </span>
                <Pill muted>Approval: {pkg.approvalReadinessLabel}</Pill>
                <Pill muted>{pkg.localMockLabel}</Pill>
              </div>
              <p className="mt-2 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                Evidence: {pkg.evidenceSnapshotId} · Updated {pkg.updatedAtLabel}
              </p>
              <div className="mt-2 flex flex-wrap gap-3 text-xs">
                <Link href={verdictHref(projectId)} style={{ color: "var(--brand-blue-light)" }}>
                  Verdict
                </Link>
                <Link href={strategyHref(projectId)} style={{ color: "var(--brand-blue-light)" }}>
                  Strategy
                </Link>
                <Link
                  href={implementationHref(projectId)}
                  style={{ color: "var(--brand-blue-light)" }}
                >
                  ← Implementation Plan
                </Link>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <DemoLink
                href={executionPackageHref(VERDICT_SCENARIO_PROJECT.go)}
                label="Demo GO"
              />
              <DemoLink
                href={executionPackageHref(VERDICT_SCENARIO_PROJECT.conditional_go)}
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

        <div className="space-y-4 p-4 sm:space-y-5 sm:p-6">
          <Panel title="Execution Boundary">
            <div
              className="rounded-lg border p-4 text-sm"
              style={{
                ...card,
                borderColor: "var(--ms-verdict-no-go)",
              }}
              role="region"
              aria-label="Execution boundary — Product Alpha does not execute"
            >
              <p className="font-semibold" style={{ color: "var(--ms-verdict-no-go)" }}>
                Product Alpha не выполняет внешние действия
              </p>
              <ul
                className="mt-2 list-disc space-y-1 pl-4 text-xs"
                style={{ color: "var(--ms-text-secondary)" }}
              >
                <li>Нет подключённых provider credentials</li>
                <li>Рекламный бюджет нельзя изменить</li>
                <li>Публикации не происходят</li>
                <li>Кампании не создаются</li>
                <li>Внешние системы не модифицируются</li>
                <li>Все данные локальные и mock-only</li>
              </ul>
            </div>
          </Panel>

          {pkg.summary.mandatoryConditions.length > 0 ? (
            <Panel title="Mandatory conditions">
              <List title="Unresolved / tracked" items={pkg.summary.mandatoryConditions} />
            </Panel>
          ) : null}

          <Panel title="Package summary">
            <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
              <Field label="Objective" value={pkg.summary.executionObjective} />
              <Field label="Budget range" value={pkg.summary.estimatedBudgetRange} />
              <Field
                label="Tasks / deliverables"
                value={`${pkg.summary.taskCount} / ${pkg.summary.deliverableCount}`}
              />
              <Field
                label="Verification coverage"
                value={pkg.summary.verificationCoverage}
              />
              <Field label="Rollback coverage" value={pkg.summary.rollbackCoverage} />
              <Field
                label="Providers"
                value={pkg.summary.requiredProviders.join(" · ") || "—"}
              />
            </dl>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <List title="Workstreams" items={pkg.summary.selectedWorkstreams} />
              <List title="Milestones" items={pkg.summary.selectedMilestones} />
              <List title="Critical risks" items={pkg.summary.criticalRisks} />
              <List title="Current blockers" items={pkg.summary.currentBlockers} />
            </div>
          </Panel>

          <Panel title="Execution readiness">
            <p className="text-sm font-semibold" style={{ color: readinessColor }}>
              {packageReadinessLabel(readiness.status)}
              <span className="sr-only"> — not real execution</span>
            </p>
            <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
              <List title="Blocking reasons" items={readiness.blockingReasons} />
              <List title="Warnings" items={readiness.warnings} />
              <List title="Missing approvals" items={readiness.missingApprovals} />
              <List title="Provider setup gaps" items={readiness.missingProviderSetup} />
              <List title="Verification gaps" items={readiness.verificationGaps} />
              <List title="Rollback gaps" items={readiness.rollbackGaps} />
            </div>
            <p className="mt-3 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
              Next: {readiness.nextRequiredAction}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                className="rounded-md px-5 py-2.5 text-sm font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-40"
                style={{
                  background: "var(--ms-brand-primary)",
                  color: "var(--ms-text-primary)",
                  outlineColor: "var(--brand-blue-light)",
                }}
                disabled={dryRunDisabled}
                aria-disabled={dryRunDisabled}
                onClick={() => {
                  const next = runLocalDryRun(projectId);
                  setPkg(next);
                  setVersions(listPackageVersions(projectId));
                  setNotice(
                    `Dry run: ${dryRunResultLabel(next.dryRunReport?.result ?? "blocked")} · externalActionsPerformed=false`,
                  );
                }}
              >
                Запустить dry run
              </button>
              <button
                type="button"
                className="rounded-md px-5 py-2.5 text-sm font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
                style={{
                  ...secondaryBtn,
                  outlineColor: "var(--brand-blue-light)",
                }}
                onClick={() => {
                  if (readiness.status === "blocked") {
                    setNotice("Нельзя подготовить к утверждению: readiness blocked.");
                    return;
                  }
                  const next = refreshPackageDerived({
                    ...pkg,
                    status: "approval_pending",
                  });
                  replaceCurrentPackage(next);
                  setPkg(next);
                  setNotice("Пакет подготовлен к утверждению (local).");
                }}
              >
                Подготовить к утверждению
              </button>
            </div>
          </Panel>

          {pkg.dryRunReport ? (
            <Panel title="Dry-run report">
              <p className="text-sm font-semibold">
                Result: {dryRunResultLabel(pkg.dryRunReport.result)}
              </p>
              <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                Package v{pkg.dryRunReport.packageVersion} · checked{" "}
                {pkg.dryRunReport.checkedItems} · externalActionsPerformed=
                {String(pkg.dryRunReport.externalActionsPerformed)}
              </p>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <List title="Passed" items={pkg.dryRunReport.passedChecks} />
                <List title="Warnings" items={pkg.dryRunReport.warnings} />
                <List title="Blockers" items={pkg.dryRunReport.blockers} />
                <List title="Approval gaps" items={pkg.dryRunReport.approvalGaps} />
                <List title="Provider gaps" items={pkg.dryRunReport.providerGaps} />
                <List title="Verification gaps" items={pkg.dryRunReport.verificationGaps} />
                <List title="Rollback gaps" items={pkg.dryRunReport.rollbackGaps} />
                <List title="Simulated sequence" items={pkg.dryRunReport.simulatedSequence} />
              </div>
            </Panel>
          ) : null}

          <Panel title="Execution scope">
            <div className="space-y-2">
              {pkg.executionScope.map((s) => (
                <article key={s.id} className="rounded-lg border p-3 text-sm" style={card}>
                  <h3 className="font-semibold">
                    {s.title}{" "}
                    <span className="text-xs font-normal" style={{ color: "var(--ms-text-muted)" }}>
                      · {s.inclusion} · {s.actionClass}
                    </span>
                  </h3>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                    {s.ownerRole} · {s.targetSystem} · risk {s.riskClass}
                    {s.approvalRequired ? " · approval" : ""}
                    {s.verificationRequired ? " · verification" : ""}
                  </p>
                </article>
              ))}
            </div>
          </Panel>

          <Panel title="Execution items">
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full min-w-[720px] text-left text-xs">
                <thead>
                  <tr style={{ color: "var(--ms-text-muted)" }}>
                    <th className="pb-2 pr-2 font-semibold">Item</th>
                    <th className="pb-2 pr-2 font-semibold">Class</th>
                    <th className="pb-2 pr-2 font-semibold">Provider</th>
                    <th className="pb-2 pr-2 font-semibold">Status</th>
                    <th className="pb-2 font-semibold">Verification</th>
                  </tr>
                </thead>
                <tbody>
                  {pkg.executionItems.map((i) => (
                    <tr
                      key={i.id}
                      className="border-t"
                      style={{ borderColor: "var(--ms-border-default)" }}
                    >
                      <td className="py-2 pr-2 align-top">
                        <span className="font-medium">{i.title}</span>
                        <p style={{ color: "var(--ms-text-muted)" }}>{i.ownerRole}</p>
                      </td>
                      <td className="py-2 pr-2 align-top">{i.actionClass}</td>
                      <td className="py-2 pr-2 align-top">{i.targetProvider}</td>
                      <td className="py-2 pr-2 align-top">{i.status}</td>
                      <td className="py-2 align-top">{i.verificationMethod}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="space-y-3 md:hidden">
              {pkg.executionItems.map((i) => (
                <article key={i.id} className="rounded-lg border p-3 text-sm" style={card}>
                  <h3 className="font-semibold">{i.title}</h3>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    {i.status} · {i.actionClass} · {i.targetProvider}
                  </p>
                </article>
              ))}
            </div>
          </Panel>

          <Panel title="Provider requirements">
            <ul className="space-y-2 text-sm" aria-label="Provider requirements">
              {pkg.providerRequirements.map((p) => (
                <li key={p.id} className="rounded-lg border p-3" style={card}>
                  <span className="font-semibold">{p.providerType}</span>
                  <span className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    {" "}
                    · auth {p.authenticationState} · config {p.configurationState} · dry-run{" "}
                    {p.dryRunAvailability}
                  </span>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                    {p.purpose} · Blocker: {p.blocker}
                  </p>
                  <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    Credentials are not requested or stored.
                  </p>
                </li>
              ))}
            </ul>
          </Panel>

          <Panel title="Approval matrix">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-xs" aria-label="Approval matrix">
                <thead>
                  <tr style={{ color: "var(--ms-text-muted)" }}>
                    <th className="pb-2 pr-2 font-semibold">Gate</th>
                    <th className="pb-2 pr-2 font-semibold">Owner</th>
                    <th className="pb-2 pr-2 font-semibold">Status</th>
                    <th className="pb-2 font-semibold">If rejected</th>
                  </tr>
                </thead>
                <tbody>
                  {pkg.approvalMatrix.map((a) => (
                    <tr
                      key={a.id}
                      className="border-t"
                      style={{ borderColor: "var(--ms-border-default)" }}
                    >
                      <td className="py-2 pr-2 align-top">{a.gate}</td>
                      <td className="py-2 pr-2 align-top">{a.decisionOwner}</td>
                      <td className="py-2 pr-2 align-top">{gateStatusLabel(a.status)}</td>
                      <td className="py-2 align-top">{a.consequenceIfRejected}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>

          <Panel title="Budget authorization">
            <dl className="grid gap-3 text-sm sm:grid-cols-2">
              <Field label="Requested" value={pkg.budgetAuthorization.requestedAmountOrRange} />
              <Field label="Approved" value={pkg.budgetAuthorization.approvedAmount} />
              <Field label="Reserved" value={pkg.budgetAuthorization.reservedAmount} />
              <Field label="Mode" value={pkg.budgetAuthorization.mode} />
              <Field label="State" value={gateStatusLabel(pkg.budgetAuthorization.approvalState)} />
              <Field label="Stop-loss" value={pkg.budgetAuthorization.stopLossThreshold} />
              <Field label="Provider allocation" value={pkg.budgetAuthorization.providerAllocation} />
              <Field label="Contingency" value={pkg.budgetAuthorization.contingency} />
            </dl>
            <List title="Unresolved gaps" items={pkg.budgetAuthorization.unresolvedGaps} />
            <p className="mt-2 text-xs" style={{ color: "var(--ms-text-muted)" }}>
              No transaction · no money movement simulated.
            </p>
          </Panel>

          <Panel title="Preflight checks">
            <ul className="space-y-2 text-sm">
              {pkg.preflightChecks.map((c) => (
                <li key={c.id} className="rounded-lg border p-3" style={card}>
                  <span className="font-semibold">{c.title}</span>
                  <span className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    {" "}
                    · {preflightResultLabel(c.result)}
                    {c.blocking ? " · blocking" : ""} · {c.severity}
                  </span>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                    {c.evidence} · Fix: {c.resolutionAction}
                  </p>
                </li>
              ))}
            </ul>
          </Panel>

          <Panel title="Verification plan">
            <ul className="space-y-2 text-sm">
              {pkg.verificationPlan.map((v) => (
                <li key={v.id} className="rounded-lg border p-3" style={card}>
                  <span className="font-semibold">{v.executionItemId}</span>
                  <span className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    {" "}
                    · {v.verificationMethod}
                    {v.acknowledgmentRequired ? " · ack required" : ""}
                  </span>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                    Expected: {v.expectedState} · Escalate: {v.escalationPath}
                  </p>
                </li>
              ))}
            </ul>
          </Panel>

          <Panel title="Rollback plan">
            <ul className="space-y-2 text-sm">
              {pkg.rollbackPlan.map((r) => (
                <li key={r.id} className="rounded-lg border p-3" style={card}>
                  <span className="font-semibold">{r.executionItemId}</span>
                  <span className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    {" "}
                    · {r.state} · {r.rollbackOwner}
                  </span>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                    Trigger: {r.rollbackTrigger} · Action: {r.rollbackAction}
                  </p>
                </li>
              ))}
            </ul>
          </Panel>

          <Panel title="Risk controls">
            <div className="space-y-3">
              {pkg.riskControls.map((r) => (
                <article key={r.id} className="rounded-lg border p-3 text-sm" style={card}>
                  <h3 className="font-semibold">{r.title}</h3>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                    Preventive: {r.preventiveControl}
                  </p>
                  <p className="text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                    Detective: {r.detectiveControl} · Corrective: {r.correctiveAction}
                  </p>
                  <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    {r.ownerRole} · {r.status} · residual {r.residualRisk}
                  </p>
                </article>
              ))}
            </div>
          </Panel>

          <Panel title="Conditions and blockers">
            {pkg.blockers.length === 0 ? (
              <p className="text-sm" style={{ color: "var(--ms-text-secondary)" }}>
                Нет активных blockers в регистре (см. также preflight warnings).
              </p>
            ) : (
              <ul className="space-y-2 text-sm">
                {pkg.blockers.map((b) => (
                  <li key={b.id} className="rounded-lg border p-3" style={card}>
                    <span className="font-semibold">{b.description}</span>
                    <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                      Origin: {b.origin} · Owner: {b.owner}
                    </p>
                    <p className="text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                      Action: {b.requiredAction} · Unblock: {b.unblockCriterion}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel title="Local review & versions">
            <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
              Product Alpha local only — не backend approval.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <ActionBtn
                onClick={() => {
                  updatePackageStatus(projectId, pkg.id, "draft");
                  setPkg({ ...pkg, status: "draft" });
                  setNotice("Draft сохранён локально.");
                }}
              >
                Save draft
              </ActionBtn>
              <ActionBtn
                onClick={() => {
                  updatePackageStatus(projectId, pkg.id, "under_review");
                  setPkg({ ...pkg, status: "under_review" });
                  setNotice("Отправлено на проверку (local).");
                }}
              >
                Send for review
              </ActionBtn>
              <ActionBtn
                onClick={() => {
                  if (readiness.status === "blocked") {
                    setNotice("Нельзя утвердить: readiness blocked.");
                    return;
                  }
                  const next = refreshPackageDerived({ ...pkg, status: "approved" });
                  replaceCurrentPackage(next);
                  setPkg(next);
                  setNotice("Пакет утверждён для dry-run (local). Нет реального исполнения.");
                }}
              >
                Approve for dry run
              </ActionBtn>
              <ActionBtn
                onClick={() => {
                  const next = preparePackageForProject(projectId, { regenerate: true });
                  setPkg(next);
                  setVersions(listPackageVersions(projectId));
                  setNotice(`Новая версия v${next.version}; предыдущая superseded.`);
                }}
              >
                Create new version
              </ActionBtn>
            </div>
            <ul className="mt-3 space-y-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
              {versions.map((v) => (
                <li key={v.id}>
                  v{v.version} · {v.verdictType} · {packageStatusLabel(v.status)}
                  {v.id === pkg.id ? " · current" : ""}
                </li>
              ))}
            </ul>
          </Panel>

          <Panel title="Future Architecture V2.2 handoff">
            <p className="mb-3 text-xs" style={{ color: "var(--ms-text-muted)" }}>
              Техническая граница будущего verified execution — не реализовано в Product Alpha.
            </p>
            <ol className="list-decimal space-y-1 pl-5 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
              {[
                "Execution Intent",
                "Readiness Gate",
                "Human Approval",
                "Provider Adapter",
                "Execution Command",
                "Provider Verification",
                "Evidence",
                "Outcome",
                "Knowledge Candidate",
              ].map((step) => (
                <li key={step}>
                  {step}{" "}
                  <span style={{ color: "var(--ms-text-muted)" }}>· future</span>
                </li>
              ))}
            </ol>
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
