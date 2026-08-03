"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type CSSProperties, type ReactNode } from "react";
import { VerdictSemanticsPanel } from "@/components/verdict/verdict-semantics-panel";
import { WorkspaceNav } from "@/components/workspace/workspace-nav";
import {
  approveBusinessVerdict,
  buildDeterministicVerdictDraft,
  fetchVerdictEvidenceSnapshot,
  submitBusinessVerdictReview,
} from "@/lib/api/endpoints/business-verdicts";
import { fetchLatestInvestigation } from "@/lib/api/endpoints/investigations";
import { PRODUCT_BRAND } from "@/lib/brand/product-brand";
import {
  buildScenarioWorkspace,
  createInvestigationForProject,
  DEMO_PROJECT_IDS,
} from "@/lib/investigation/mock-data";
import { saveInvestigationWorkspace } from "@/lib/investigation/storage";
import type { InvestigationScenarioId } from "@/lib/investigation/types";
import {
  loadBusinessVerdictView,
  type VerdictLoadResult,
} from "@/lib/integration/verdict-adapter";
import { getIntegrationMode } from "@/lib/integration/mode";
import { createEmptyDraft } from "@/lib/project-intake/schema";
import { getMockProject, saveMockProject } from "@/lib/project-intake/storage";
import {
  prepareVerdictForProject,
  VERDICT_SCENARIO_PROJECT,
} from "@/lib/verdict/mock-verdicts";
import {
  listVerdictVersions,
  updateVerdictStatus,
} from "@/lib/verdict/storage";
import {
  ratingLabel,
  statusLabel,
  verdictGlyph,
  verdictPlainLabel,
  verdictTokenVar,
} from "@/lib/verdict/selectors";
import type { BusinessVerdict, VerdictScenarioId } from "@/lib/verdict/types";

type Props = { projectId: string };

export function VerdictWorkspaceView({ projectId }: Props) {
  const [verdict, setVerdict] = useState<BusinessVerdict | null>(null);
  const [versions, setVersions] = useState<BusinessVerdict[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [integrationLoad, setIntegrationLoad] = useState<VerdictLoadResult | null>(null);
  const [lifecycleBusy, setLifecycleBusy] = useState(false);
  const mode = getIntegrationMode();

  const refresh = useCallback(async () => {
    ensureDemoSeed();
    if (mode === "mock" || mode === "hybrid") {
      const inv = createInvestigationForProject(projectId, getMockProject(projectId));
      saveInvestigationWorkspace(inv);
    }

    const result = await loadBusinessVerdictView(projectId, {
      ensureLocalPreview: mode !== "backend",
    });
    setIntegrationLoad(result);

    if (mode === "backend") {
      const v = result.view?.verdict ?? null;
      setVerdict(v);
      setVersions(result.view?.versions ?? []);
      if (result.error) {
        setNotice(`${result.error.message} ${result.error.actionHint}`);
      } else if (!v) {
        setNotice(
          "Backend mode: вердиктов пока нет. Создайте deterministic draft явно (не на page load). Mock не подставляется.",
        );
      } else {
        setNotice(
          "Business Verdict — это коммерческое решение на основе зафиксированного Evidence Snapshot. Оно не является разрешением на исполнение.",
        );
      }
      return;
    }

    const v = result.view?.verdict ?? null;
    setVerdict(v);
    setVersions(result.view?.versions ?? listVerdictVersions(projectId));
    if (mode === "hybrid" && v) {
      setNotice(
        result.view?.noBackendVerdictEntity
          ? "Локальный предварительный вердикт — не persisted на backend и не evidence-verified. Auto-upload отключён."
          : "Backend approved verdict authoritative. Business Verdict ≠ разрешение на исполнение.",
      );
    }
  }, [projectId, mode]);

  useEffect(() => {
    void refresh().finally(() => setLoaded(true));
  }, [refresh]);

  const regenerate = () => {
    if (mode === "backend") {
      setNotice("Backend mode: локальная regenerция отключена (no mock fallback).");
      return;
    }
    const v = prepareVerdictForProject(projectId, { regenerate: true });
    setVerdict(v);
    setVersions(listVerdictVersions(projectId));
    setNotice(
      `Создана новая локальная версия v${v.version} (deterministic_local preview). Не загружена на backend.`,
    );
    void loadBusinessVerdictView(projectId, { ensureLocalPreview: false }).then(setIntegrationLoad);
  };

  const setStatus = (status: BusinessVerdict["status"]) => {
    if (!verdict || mode === "backend") return;
    updateVerdictStatus(projectId, verdict.id, status);
    const updated = listVerdictVersions(projectId).find((x) => x.id === verdict.id);
    if (updated) setVerdict(updated);
    setVersions(listVerdictVersions(projectId));
    setNotice(
      `Статус «${status}» — локальный review only. Не создаёт Execution Approval и не вызывает Strategy backend.`,
    );
  };

  const onBuildVerdictDraft = async () => {
    setLifecycleBusy(true);
    try {
      const investigation = await fetchLatestInvestigation(projectId);
      const draft = await buildDeterministicVerdictDraft(projectId, investigation.id);
      try {
        await fetchVerdictEvidenceSnapshot(projectId, draft.id);
      } catch {
        /* snapshot optional for UI refresh */
      }
      setNotice(
        `Draft вердикта собран (v${draft.version}, ${draft.lifecycle_status}). Agent Run / LLM не вызывались.`,
      );
      await refresh();
    } catch (err) {
      setNotice(
        err instanceof Error
          ? err.message
          : "Не удалось собрать draft вердикта.",
      );
    } finally {
      setLifecycleBusy(false);
    }
  };

  const onSubmitVerdictReview = async () => {
    if (!verdict) return;
    setLifecycleBusy(true);
    try {
      await submitBusinessVerdictReview(projectId, verdict.id);
      setNotice("Вердикт отправлен на проверку (under_review).");
      await refresh();
    } catch (err) {
      setNotice(
        err instanceof Error ? err.message : "Не удалось отправить вердикт на проверку.",
      );
    } finally {
      setLifecycleBusy(false);
    }
  };

  const onApproveVerdict = async () => {
    if (!verdict) return;
    setLifecycleBusy(true);
    try {
      await approveBusinessVerdict(projectId, verdict.id);
      setNotice(
        "Вердикт утверждён (approved). Это не Execution Approval и не создаёт Strategy автоматически.",
      );
      await refresh();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Не удалось утвердить вердикт.");
    } finally {
      setLifecycleBusy(false);
    }
  };

  const switchScenario = (scenario: VerdictScenarioId) => {
    const targetId = VERDICT_SCENARIO_PROJECT[scenario];
    window.location.href = `/workspace/projects/${targetId}/verdict`;
  };

  if (!loaded) {
    return (
      <div
        className="flex min-h-screen items-center justify-center"
        style={{ background: "var(--ms-bg-canvas)", color: "var(--ms-text-muted)" }}
      >
        Подготовка вердикта…
      </div>
    );
  }

  if (mode === "backend" && !verdict) {
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
              {PRODUCT_BRAND.displayName} · Business Verdict
            </p>
            <h1 className="mt-1 text-lg font-semibold">
              {integrationLoad?.projectName ?? "Project"}
            </h1>
          </header>
          <VerdictSemanticsPanel load={integrationLoad} />
          <div className="mx-auto max-w-2xl space-y-4 p-6">
            <p className="text-sm" style={{ color: "var(--ms-text-secondary)" }}>
              Backend mode: durable BusinessVerdict пока отсутствует для проекта. Mock не
              подставляется. Соберите deterministic draft явно после Evidence.
            </p>
            <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
              Business Verdict — это коммерческое решение на основе зафиксированного Evidence
              Snapshot. Оно не является разрешением на исполнение.
            </p>
            {notice ? (
              <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                {notice}
              </p>
            ) : null}
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                data-testid="verdict-build-draft"
                disabled={lifecycleBusy}
                onClick={() => void onBuildVerdictDraft()}
                className="rounded-md px-3 py-2 text-xs font-semibold disabled:opacity-50"
                style={secondaryBtn}
              >
                Собрать draft вердикта
              </button>
              <Link
                href={`/workspace/projects/${projectId}/investigation`}
                className="rounded-md px-3 py-2 text-xs font-medium"
                style={{ color: "var(--brand-blue-light)" }}
              >
                Вернуться в Investigation
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!verdict) {
    return (
      <div
        className="flex min-h-screen items-center justify-center"
        style={{ background: "var(--ms-bg-canvas)", color: "var(--ms-text-muted)" }}
      >
        Вердикт недоступен.
      </div>
    );
  }

  const color = verdictTokenVar(verdict.type);
  const invHref = `/workspace/projects/${projectId}/investigation`;
  const originBadge =
    integrationLoad?.view?.originMeta.labelRu ?? verdict.localMockLabel;

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
                {PRODUCT_BRAND.displayName} · Business Verdict
              </p>
              <h1 className="mt-1 text-lg font-semibold sm:text-xl">{verdict.projectName}</h1>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                <span
                  className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 font-semibold"
                  style={{
                    background: `color-mix(in srgb, ${color} 22%, transparent)`,
                    color,
                  }}
                  aria-label={verdictPlainLabel(verdict.type)}
                >
                  <span aria-hidden>{verdictGlyph(verdict.type)}</span>
                  {verdict.type}
                </span>
                <Pill>status: {statusLabel(verdict.status)}</Pill>
                <Pill>confidence: {verdict.confidence}</Pill>
                <Pill>{verdict.evidenceCoverageLabel}</Pill>
                <Pill muted>v{verdict.version}</Pill>
                <Pill muted>{originBadge}</Pill>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link
                href={invHref}
                className="rounded-md px-3 py-2 text-xs font-medium"
                style={secondaryBtn}
              >
                ← Investigation
              </Link>
              <Link href="/workspace" className="rounded-md px-3 py-2 text-xs font-medium" style={secondaryBtn}>
                Workspace
              </Link>
            </div>
          </div>
        </header>

        <VerdictSemanticsPanel load={integrationLoad} />

        <div className="mx-auto w-full max-w-7xl space-y-6 p-4 sm:p-6">
          {notice ? (
            <p
              role="status"
              className="rounded-md border px-3 py-2 text-xs"
              style={{
                borderColor: "var(--ms-border-default)",
                background: "var(--ms-bg-elevated)",
                color: "var(--ms-text-secondary)",
              }}
            >
              {notice}
            </p>
          ) : null}

          <section
            className="rounded-xl border p-4"
            style={{ borderColor: "var(--ms-border-default)", background: "var(--ms-bg-surface)" }}
            aria-label="Verdict scenarios"
          >
            <h2 className="text-sm font-semibold" style={{ color: "var(--ms-brand-secondary)" }}>
              SCENARIOS A–D
            </h2>
            <div className="mt-3 flex flex-wrap gap-2">
              {(
                [
                  ["go", "A · GO"],
                  ["conditional_go", "B · CONDITIONAL_GO"],
                  ["no_go", "C · NO_GO"],
                  ["insufficient_data", "D · INSUFFICIENT_DATA"],
                ] as const
              ).map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  className="rounded-md px-3 py-2 text-xs font-semibold"
                  style={{
                    background:
                      VERDICT_SCENARIO_PROJECT[id] === projectId
                        ? "var(--ms-brand-primary)"
                        : "var(--ms-bg-elevated)",
                    color: "var(--ms-text-primary)",
                    boxShadow:
                      VERDICT_SCENARIO_PROJECT[id] === projectId
                        ? undefined
                        : "inset 0 0 0 1px var(--ms-border-default)",
                  }}
                  onClick={() => switchScenario(id)}
                >
                  {label}
                </button>
              ))}
            </div>
          </section>

          {/* Executive */}
          <Panel title="Executive verdict">
            <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
              {verdictPlainLabel(verdict.type)}
            </p>
            <p className="mt-3 text-lg font-semibold leading-snug" style={{ color }}>
              {verdict.oneSentenceConclusion}
            </p>
            <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
              <Field label="Executive rationale" value={verdict.executiveRationale} />
              <Field label="Business implication" value={verdict.primaryBusinessImplication} />
              <Field label="Immediate action" value={verdict.recommendedImmediateAction} />
              <Field
                label="Based on readiness (≠ verdict)"
                value={verdict.basedOnReadinessStatus}
              />
            </dl>
          </Panel>

          {/* Scorecard */}
          <Panel title="Decision scorecard">
            <p className="mb-3 text-xs" style={{ color: "var(--ms-text-muted)" }}>
              Qualitative ratings primary. Coverage index is secondary and deterministic.
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              {verdict.scorecard.map((d) => (
                <article
                  key={d.id}
                  className="rounded-md border p-3 text-sm"
                  style={{ borderColor: "var(--ms-border-default)", background: "var(--ms-bg-elevated)" }}
                >
                  <p className="font-medium">
                    [{ratingLabel(d.rating)}] {d.label}
                  </p>
                  <p className="mt-1" style={{ color: "var(--ms-text-secondary)" }}>
                    {d.explanation}
                  </p>
                  {d.criticalGap ? (
                    <p className="mt-1 text-xs" style={{ color: "var(--ms-status-danger)" }}>
                      Gap: {d.criticalGap}
                    </p>
                  ) : null}
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    Evidence: {d.evidenceIds.join(", ") || "—"}
                  </p>
                </article>
              ))}
            </div>
          </Panel>

          <div className="grid gap-6 lg:grid-cols-2">
            <Panel title="Supporting evidence">
              {verdict.supportingEvidence.length === 0 ? (
                <Empty>Нет supporting evidence.</Empty>
              ) : (
                verdict.supportingEvidence.map((e) => (
                  <article key={e.evidenceId} className="mb-3 rounded-md border p-3 text-sm" style={card}>
                    <p className="text-xs font-semibold uppercase">
                      [{e.state}] {e.criterion} · {e.confidence}
                    </p>
                    <p className="mt-1 font-medium">{e.claim}</p>
                    <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                      Sources: {e.sourceTitles.join(", ") || "—"}
                    </p>
                    <p className="mt-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                      Why: {e.whyItMatters}
                    </p>
                  </article>
                ))
              )}
            </Panel>
            <Panel title="Counter-evidence">
              {verdict.counterEvidence.length === 0 ? (
                <Empty>Нет открытого counter-evidence.</Empty>
              ) : (
                verdict.counterEvidence.map((c) => (
                  <article key={c.id} className="mb-3 rounded-md border p-3 text-sm" style={card}>
                    <p className="font-medium">{c.conflictingClaim}</p>
                    <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                      Source: {c.sourceTitle} · {c.resolutionStatus}
                      {c.couldChangeVerdict ? " · MAY CHANGE VERDICT" : ""}
                    </p>
                    <p className="mt-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                      Impact: {c.impact}
                    </p>
                  </article>
                ))
              )}
            </Panel>
          </div>

          <Panel title="Critical risks">
            {verdict.risks.length === 0 ? (
              <Empty>Нет decision-relevant risks.</Empty>
            ) : (
              verdict.risks.map((r) => (
                <article
                  key={r.id}
                  className="mb-3 rounded-md border p-3 text-sm"
                  style={{
                    ...card,
                    boxShadow:
                      r.sensitivity === "verdict_changing"
                        ? "inset 0 0 0 1px var(--ms-verdict-no-go)"
                        : undefined,
                  }}
                >
                  <p className="font-medium">
                    [{r.severity}/{r.probability}] {r.title}
                    {r.sensitivity === "verdict_changing" ? (
                      <span className="ml-2 text-xs font-semibold" style={{ color: "var(--ms-verdict-no-go)" }}>
                        VERDICT-CHANGING
                      </span>
                    ) : (
                      <span className="ml-2 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                        sensitivity: {r.sensitivity}
                      </span>
                    )}
                  </p>
                  <p className="mt-1" style={{ color: "var(--ms-text-secondary)" }}>
                    {r.businessConsequence}
                  </p>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    Mitigation: {r.mitigation}
                  </p>
                </article>
              ))
            )}
          </Panel>

          <Panel title="Assumptions register">
            {verdict.assumptions.length === 0 ? (
              <Empty>Явных допущений нет.</Empty>
            ) : (
              verdict.assumptions.map((a) => (
                <article key={a.id} className="mb-3 rounded-md border p-3 text-sm" style={card}>
                  <p className="font-medium">
                    [{a.state}] {a.statement}
                  </p>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                    Why: {a.reasonRequired}
                  </p>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    Validate: {a.validationMethod} · {a.validationStage}
                  </p>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    If false: {a.effectIfFalse}
                  </p>
                </article>
              ))
            )}
          </Panel>

          {verdict.type === "CONDITIONAL_GO" || verdict.conditions.length > 0 ? (
            <Panel title="Conditions">
              {verdict.conditions.length === 0 ? (
                <Empty>Для этого типа вердикта обязательных conditions нет.</Empty>
              ) : (
                verdict.conditions.map((c) => (
                  <article key={c.id} className="mb-3 rounded-md border p-3 text-sm" style={card}>
                    <p className="font-medium">{c.requiredAction}</p>
                    <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                      Owner: {c.owner} · Milestone: {c.deadlineOrMilestone}
                    </p>
                    <p className="mt-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                      Success: {c.successCriterion}
                    </p>
                    <p className="mt-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                      Evidence required: {c.evidenceRequired}
                    </p>
                    <p className="mt-1 text-xs" style={{ color: "var(--ms-status-warning)" }}>
                      If not met: {c.consequenceIfNotMet}
                    </p>
                  </article>
                ))
              )}
            </Panel>
          ) : null}

          <Panel title="Verdict change triggers">
            {verdict.changeTriggers.map((t) => (
              <article key={t.id} className="mb-3 rounded-md border p-3 text-sm" style={card}>
                <p className="font-medium">{t.description}</p>
                <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                  Now: {t.currentState} · Threshold: {t.threshold}
                </p>
                <p className="mt-1 text-xs" style={{ color: "var(--brand-blue-light)" }}>
                  Transition: {t.possibleTransition}
                </p>
              </article>
            ))}
          </Panel>

          <Panel title="Recommended next step">
            <p className="text-base font-semibold">{verdict.nextStep.primaryAction}</p>
            <ul className="mt-2 list-disc pl-5 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
              {verdict.nextStep.supportingActions.map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ul>
            <p className="mt-3 text-xs" style={{ color: "var(--ms-text-muted)" }}>
              {verdict.nextStep.note}
            </p>
            <div className="mt-4">
              <Link
                href={
                  verdict.nextStep.handoffHref === "strategy"
                    ? `/workspace/projects/${projectId}/strategy`
                    : verdict.nextStep.handoffHref === "pivot"
                      ? `/workspace/projects/${projectId}/pivot`
                      : invHref
                }
                className="inline-flex rounded-md px-4 py-2 text-sm font-semibold"
                style={{
                  background: "var(--ms-brand-primary)",
                  color: "var(--ms-text-primary)",
                }}
              >
                {verdict.nextStep.handoffLabel}
              </Link>
            </div>
          </Panel>

          {/* Approval + versioning */}
          <Panel title={mode === "backend" ? "Backend approval & versions" : "Local approval & versions"}>
            <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
              {mode === "backend"
                ? "Durable BusinessVerdict lifecycle (submit-review / approve). Не Execution Approval."
                : "Product Alpha local behavior only — не backend approval API."}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {mode === "backend" ? (
                <>
                  {verdict.status === "draft" ? (
                    <button
                      type="button"
                      data-testid="verdict-submit-review"
                      disabled={lifecycleBusy}
                      onClick={() => void onSubmitVerdictReview()}
                      className="rounded-md px-3 py-2 text-xs font-semibold disabled:opacity-50"
                      style={secondaryBtn}
                    >
                      Отправить на проверку
                    </button>
                  ) : null}
                  {verdict.status === "under_review" ? (
                    <button
                      type="button"
                      data-testid="verdict-approve"
                      disabled={lifecycleBusy}
                      onClick={() => void onApproveVerdict()}
                      className="rounded-md px-3 py-2 text-xs font-semibold disabled:opacity-50"
                      style={secondaryBtn}
                    >
                      Утвердить вердикт
                    </button>
                  ) : null}
                </>
              ) : (
                <>
                  <ActionBtn onClick={() => setStatus("under_review")}>Отправить на проверку</ActionBtn>
                  <ActionBtn onClick={() => setStatus("approved")}>Утвердить вердикт</ActionBtn>
                  <ActionBtn onClick={regenerate}>Создать новую версию</ActionBtn>
                </>
              )}
            </div>
            <ul className="mt-4 space-y-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
              {versions.map((v) => (
                <li key={v.id}>
                  v{v.version} · {v.type} · {statusLabel(v.status)}
                  {v.id === verdict.id ? " · current" : ""}
                </li>
              ))}
            </ul>
          </Panel>

          {/* Export placeholders */}
          <Panel title="Export / share">
            <div className="flex flex-wrap gap-2">
              {["Export PDF", "Share verdict", "Create presentation", "Send to team"].map(
                (label) => (
                  <button
                    key={label}
                    type="button"
                    disabled
                    className="rounded-md px-3 py-2 text-xs font-medium opacity-40"
                    style={secondaryBtn}
                    title="Unavailable in Product Alpha"
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

function ensureDemoSeed() {
  for (const [scenario, id] of Object.entries(DEMO_PROJECT_IDS) as Array<
    [InvestigationScenarioId, string]
  >) {
    if (getMockProject(id)) continue;
    const ws = buildScenarioWorkspace(scenario, id);
    const draft = createEmptyDraft("review");
    draft.projectBasics.name = ws.projectName;
    draft.projectBasics.ideaDescription = ws.brief.idea;
    saveMockProject({
      id,
      name: ws.projectName,
      status: "investigation_queued",
      statusLabel: `Demo · ${scenario}`,
      createdAt: new Date().toISOString(),
      readiness: {
        status:
          scenario === "not_ready"
            ? "insufficient_data"
            : scenario === "ready_for_review"
              ? "ready"
              : "conditionally_ready",
        completedSections: [],
        missingCritical: [],
        missingOptional: [],
        assumptions: [],
        contradictions: [],
        recommendedAdditions: [],
      },
      draftSnapshot: draft,
    });
    saveInvestigationWorkspace(ws);
  }
}

const secondaryBtn: CSSProperties = {
  background: "var(--ms-bg-elevated)",
  color: "var(--ms-text-secondary)",
  boxShadow: "inset 0 0 0 1px var(--ms-border-default)",
};

const card: CSSProperties = {
  borderColor: "var(--ms-border-default)",
  background: "var(--ms-bg-elevated)",
};

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section
      className="rounded-xl border p-4 sm:p-5"
      style={{ borderColor: "var(--ms-border-default)", background: "var(--ms-bg-surface)" }}
    >
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
        background: muted ? "var(--ms-bg-elevated)" : "color-mix(in srgb, var(--brand-blue) 18%, transparent)",
        color: muted ? "var(--ms-text-muted)" : "var(--brand-blue-light)",
      }}
    >
      {children}
    </span>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
        {label}
      </dt>
      <dd className="mt-0.5" style={{ color: "var(--ms-text-secondary)" }}>
        {value}
      </dd>
    </div>
  );
}

function Empty({ children }: { children: ReactNode }) {
  return (
    <p className="text-sm" style={{ color: "var(--ms-text-muted)" }}>
      {children}
    </p>
  );
}

function ActionBtn({ children, onClick }: { children: ReactNode; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-md px-3 py-2 text-xs font-semibold"
      style={secondaryBtn}
    >
      {children}
    </button>
  );
}
