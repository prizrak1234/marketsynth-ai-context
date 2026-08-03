/**
 * Deterministic Business Verdict builder — not an LLM / API service.
 * Readiness ≠ verdict.
 */

import type { InvestigationWorkspace } from "@/lib/investigation/types";
import type { ConfidenceLevel } from "@/lib/investigation/types";
import { evaluateVerdictReadiness } from "@/lib/investigation/verdict-readiness";
import { dim, scorecardSummaryIndex } from "@/lib/verdict/scorecard";
import type {
  BusinessVerdict,
  BusinessVerdictType,
  CounterEvidenceItem,
  VerdictAssumption,
  VerdictChangeTrigger,
  VerdictCondition,
  VerdictEvidenceLink,
  VerdictNextStep,
  VerdictRiskItem,
  VerdictScenarioId,
} from "@/lib/verdict/types";

function sourceTitle(
  ws: InvestigationWorkspace,
  id: string,
): string {
  return ws.sources.find((s) => s.id === id)?.title ?? id;
}

function linkEvidence(
  ws: InvestigationWorkspace,
  evidenceId: string,
  criterion: VerdictEvidenceLink["criterion"],
  whyItMatters: string,
): VerdictEvidenceLink | null {
  const e = ws.evidence.find((x) => x.id === evidenceId);
  if (!e) return null;
  return {
    evidenceId: e.id,
    claim: e.claim,
    state: e.state,
    sourceTitles: e.supportingSourceIds.map((id) => sourceTitle(ws, id)),
    confidence: e.confidence,
    criterion,
    whyItMatters,
  };
}

function nextStepFor(type: BusinessVerdictType): VerdictNextStep {
  if (type === "GO") {
    return {
      primaryAction: "Перейти к стратегии",
      handoffLabel: "Открыть Strategy Workspace",
      handoffHref: "strategy",
      supportingActions: [
        "Определить launch plan assumptions",
        "Утвердить бюджетные диапазоны",
      ],
      note: "Strategy Workspace — Product Alpha A5.",
    };
  }
  if (type === "CONDITIONAL_GO") {
    return {
      primaryAction: "Создать план проверки условий",
      handoffLabel: "Strategy + validation conditions",
      handoffHref: "strategy",
      supportingActions: [
        "Закрыть conditions",
        "Вернуться за обновлением вердикта",
      ],
      note: "Стратегия доступна, execution остаётся blocked условиями.",
    };
  }
  if (type === "NO_GO") {
    return {
      primaryAction: "Создать вариант переработки идеи",
      handoffLabel: "Открыть Pivot / Rework",
      handoffHref: "pivot",
      supportingActions: [
        "Остановить текущую концепцию",
        "Пересмотреть модель / позиционирование",
      ],
      note: "Стратегия для NO_GO не строится.",
    };
  }
  return {
    primaryAction: "Вернуться к сбору данных",
    handoffLabel: "Investigation Workspace",
    handoffHref: "investigation",
    supportingActions: [
      "Закрыть critical missing data",
      "Снять blocking contradictions",
    ],
    note: "INSUFFICIENT_DATA → только возврат к evidence, не стратегия.",
  };
}

/**
 * Rule engine: classify verdict type from investigation workspace.
 * Never infer GO from readiness alone.
 */
export function classifyVerdictType(
  ws: InvestigationWorkspace,
): BusinessVerdictType {
  const readiness = ws.verdictReadiness ?? evaluateVerdictReadiness(ws);
  const criticalMissing = ws.missingData.filter(
    (m) => m.severity === "critical" && m.resolution === "open",
  );
  const blockingCx = ws.contradictions.filter((c) => c.blocksVerdict && !c.resolved);
  const economicsWeak = ws.evidence.some(
    (e) =>
      e.area === "economics" &&
      (e.state === "missing" || e.state === "conflicting" || e.confidence === "low"),
  );
  const demandWeak = !ws.evidence.some(
    (e) =>
      (e.area === "demand" || e.area === "market") &&
      e.state === "confirmed" &&
      e.confidence !== "low",
  );
  const verdictChangingRisk = ws.risks.some(
    (r) => r.severity === "critical" && r.status === "open",
  );
  const structuralNoGo =
    ws.scenarioId === "no_go" ||
    (demandWeak && economicsWeak && verdictChangingRisk && blockingCx.length > 0);

  if (
    readiness.status === "not_ready" ||
    criticalMissing.length > 0 ||
    (blockingCx.length > 0 && readiness.completedAreas.length < 3)
  ) {
    // Prefer INSUFFICIENT_DATA when coverage is too low to judge;
    // NO_GO only when we have enough to condemn the model.
    if (structuralNoGo && readiness.completedAreas.length >= 2) {
      return "NO_GO";
    }
    return "INSUFFICIENT_DATA";
  }

  if (structuralNoGo) {
    return "NO_GO";
  }

  const goEligible =
    readiness.status === "ready_for_review" &&
    blockingCx.length === 0 &&
    criticalMissing.length === 0 &&
    !economicsWeak &&
    readiness.completedAreas.includes("market") &&
    readiness.completedAreas.includes("audience") &&
    readiness.completedAreas.includes("economics") &&
    !verdictChangingRisk;

  if (goEligible) {
    return "GO";
  }

  return "CONDITIONAL_GO";
}

export function resolveVerdictScenarioId(
  type: BusinessVerdictType,
): VerdictScenarioId {
  if (type === "GO") return "go";
  if (type === "CONDITIONAL_GO") return "conditional_go";
  if (type === "NO_GO") return "no_go";
  return "insufficient_data";
}

export function buildBusinessVerdict(
  ws: InvestigationWorkspace,
  opts: {
    version: number;
    supersedesVerdictId: string | null;
    status?: BusinessVerdict["status"];
  },
): BusinessVerdict {
  const readiness = ws.verdictReadiness ?? evaluateVerdictReadiness(ws);
  const type = classifyVerdictType(ws);
  const now = new Date().toISOString();

  const supporting: VerdictEvidenceLink[] = [];
  const counter: CounterEvidenceItem[] = [];

  for (const e of ws.evidence) {
    if (e.state === "confirmed" || e.state === "partial") {
      const criterion =
        e.area === "economics"
          ? "economic_viability"
          : e.area === "audience"
            ? "audience_clarity"
            : e.area === "competitors"
              ? "competitive_position"
              : e.area === "risks"
                ? "risk_exposure"
                : e.area === "demand"
                  ? "demand_evidence"
                  : "market_attractiveness";
      const link = linkEvidence(
        ws,
        e.id,
        criterion,
        e.reviewerNote || "Связано с критерием решения.",
      );
      if (link) supporting.push(link);
    }
    if (e.state === "conflicting" || e.state === "missing") {
      counter.push({
        id: `ce_${e.id}`,
        conflictingClaim: e.claim,
        sourceTitle:
          e.supportingSourceIds.map((id) => sourceTitle(ws, id)).join(", ") ||
          "—",
        impact: e.reviewerNote || "Ослабляет уверенность в вердикте.",
        resolutionStatus: "open",
        couldChangeVerdict: e.state === "conflicting" || e.area === "economics",
      });
    }
  }

  for (const cx of ws.contradictions.filter((c) => !c.resolved)) {
    counter.push({
      id: `cx_${cx.id}`,
      conflictingClaim: `${cx.statementA} vs ${cx.statementB}`,
      sourceTitle: `${cx.fieldA} / ${cx.fieldB}`,
      impact: cx.requiredResolution,
      resolutionStatus: "open",
      couldChangeVerdict: cx.blocksVerdict,
    });
  }

  const risks: VerdictRiskItem[] = ws.risks.map((r) => ({
    id: r.id,
    title: r.title,
    severity: r.severity,
    probability: r.probability,
    businessConsequence: r.businessConsequence,
    evidenceIds: r.evidenceIds,
    mitigation: r.mitigation,
    sensitivity:
      r.severity === "critical"
        ? "verdict_changing"
        : r.severity === "high"
          ? "high"
          : r.severity === "medium"
            ? "medium"
            : "low",
  }));

  const assumptions: VerdictAssumption[] = [
    ...ws.brief.assumptions.map((statement, i) => ({
      id: `ba_${i}`,
      statement,
      reasonRequired: "Зафиксировано в brief / missing-data flow",
      supportingEvidenceIds: [] as string[],
      confidence: "low" as ConfidenceLevel,
      validationMethod: "Targeted validation или owner confirmation",
      validationStage: "Before strategy (A5)",
      effectIfFalse: "Вердикт может быть пересмотрен",
      state: "requires_validation" as const,
    })),
    ...ws.missingData
      .filter((m) => m.resolution === "assumed" || m.resolution === "marked_unknown")
      .map((m) => ({
        id: `ma_${m.id}`,
        statement: m.assumptionNote || m.missingInformation,
        reasonRequired: m.whyItMatters,
        supportingEvidenceIds: [] as string[],
        confidence: "low" as ConfidenceLevel,
        validationMethod: m.recommendedAction,
        validationStage: "Investigation follow-up",
        effectIfFalse: m.blockedDecision,
        state:
          m.resolution === "assumed"
            ? ("accepted_for_now" as const)
            : ("requires_validation" as const),
      })),
  ];

  const conditions: VerdictCondition[] =
    type === "CONDITIONAL_GO"
      ? ws.missingData
          .filter((m) => m.severity === "high" || m.severity === "medium")
          .slice(0, 4)
          .map((m, i) => ({
            id: `cond_${m.id}`,
            requiredAction: m.recommendedAction,
            owner: i % 2 === 0 ? "Owner" : "Research Director",
            successCriterion: `Закрыт пробел: ${m.missingInformation}`,
            evidenceRequired: "Обновлённый evidence item со state ≠ missing",
            deadlineOrMilestone: "До Strategy Workspace",
            consequenceIfNotMet: "Вердикт остаётся CONDITIONAL_GO или понижается",
          }))
      : type === "GO"
        ? []
        : [];

  const changeTriggers: VerdictChangeTrigger[] = buildTriggers(type, ws);
  const scorecard = buildScorecard(ws, type);
  const coveragePct = scorecardSummaryIndex(scorecard);

  const narrative = narrativeFor(type, ws);

  return {
    id: `verdict_${ws.projectId}_v${opts.version}_${Math.random().toString(36).slice(2, 7)}`,
    projectId: ws.projectId,
    projectName: ws.projectName,
    version: opts.version,
    type,
    status: opts.status ?? "draft",
    confidence: confidenceFor(type, readiness.status),
    evidenceCoverageLabel: `${coveragePct}% qualitative coverage index (secondary)`,
    preparedAt: now,
    preparedAtLabel: "локальный mock · Product Alpha A4",
    supersedesVerdictId: opts.supersedesVerdictId,
    evidenceSnapshotId: `snap_${ws.projectId}_${ws.updatedAt}`,
    oneSentenceConclusion: narrative.oneSentence,
    executiveRationale: narrative.rationale,
    primaryBusinessImplication: narrative.implication,
    recommendedImmediateAction: narrative.immediate,
    scorecard,
    supportingEvidence: supporting.slice(0, 8),
    counterEvidence: counter.slice(0, 8),
    risks,
    assumptions,
    conditions,
    changeTriggers,
    nextStep: nextStepFor(type),
    basedOnReadinessStatus: readiness.status,
    localMockLabel: "Local mock · deterministic · not LLM",
  };
}

function confidenceFor(
  type: BusinessVerdictType,
  readiness: string,
): ConfidenceLevel {
  if (type === "GO") return "high";
  if (type === "INSUFFICIENT_DATA") return "low";
  if (type === "NO_GO") return readiness === "ready_for_review" ? "medium" : "medium";
  return "medium";
}

function narrativeFor(
  type: BusinessVerdictType,
  ws: InvestigationWorkspace,
): {
  oneSentence: string;
  rationale: string;
  implication: string;
  immediate: string;
} {
  if (type === "GO") {
    return {
      oneSentence: `Проект «${ws.projectName}» достаточно подкреплён evidence, чтобы перейти к strategy planning в заявленных ограничениях.`,
      rationale:
        "Рынок, аудитория и экономика закрыты подтверждёнными evidence items без критических противоречий и без открытых critical gaps. Риски задокументированы и не являются verdict-changing в текущем виде.",
      implication:
        "Можно планировать стратегию и бюджетные допущения; это не обещание коммерческого успеха.",
      immediate: "Открыть Strategy Workspace (A5) и зафиксировать launch assumptions.",
    };
  }
  if (type === "CONDITIONAL_GO") {
    return {
      oneSentence: `Проект «${ws.projectName}» может двигаться дальше только при выполнении явных условий и валидации допущений.`,
      rationale:
        "Есть сигналы жизнеспособности (рынок/аудитория), но экономика или coverage неполны, а часть gaps остаётся open. Условия тестируемы и должны быть закрыты до полной стратегии.",
      implication:
        "Потратить ресурс на validation plan дешевле, чем строить полную стратегию на незакрытых допущениях.",
      immediate: "Сформировать план проверки условий и вернуться за обновлением вердикта.",
    };
  }
  if (type === "NO_GO") {
    return {
      oneSentence: `В текущей форме «${ws.projectName}» не следует запускать: evidence указывает на неприемлемый коммерческий риск.`,
      rationale:
        "Слабый demand/market signal сочетается со структурной экономической уязвимостью и критическим противоречием или риском. Продолжение без переработки модели с высокой вероятностью создаёт потери.",
      implication:
        "Нужен pivot / переработка идеи, а не стратегия масштабирования текущего концепта.",
      immediate: "Остановить текущую концепцию и подготовить вариант переработки идеи.",
    };
  }
  return {
    oneSentence: `По проекту «${ws.projectName}» недостаточно надёжных данных для ответственного GO, CONDITIONAL_GO или NO_GO.`,
    rationale:
      "Критические пробелы, низкое coverage или блокирующие противоречия делают любой «уверенный» вердикт искусственным. Readiness ≠ право вынести коммерческое решение.",
    implication:
      "Любая стратегия сейчас была бы построена на догадках — Marketsynth это запрещает.",
    immediate: "Вернуться в Investigation Workspace и закрыть blocking gaps.",
  };
}

function buildScorecard(ws: InvestigationWorkspace, type: BusinessVerdictType) {
  const has = (area: string, states: string[]) =>
    ws.evidence.some((e) => e.area === area && states.includes(e.state));

  return [
    dim(
      "market_attractiveness",
      has("market", ["confirmed"]) ? "strong" : has("market", ["partial"]) ? "acceptable" : "insufficient_data",
      "Оценка рынка по Evidence Register.",
      ws.evidence.filter((e) => e.area === "market").map((e) => e.id),
      has("market", ["confirmed", "partial"]) ? undefined : "Нет market evidence",
    ),
    dim(
      "demand_evidence",
      has("demand", ["confirmed"]) ? "strong" : has("market", ["confirmed"]) ? "acceptable" : "weak",
      "Demand signals или proxy через market evidence.",
      ws.evidence.filter((e) => e.area === "demand" || e.area === "market").map((e) => e.id),
    ),
    dim(
      "competitive_position",
      has("competitors", ["confirmed"]) ? "acceptable" : has("competitors", ["partial"]) ? "weak" : "insufficient_data",
      "Полнота competitor landscape.",
      ws.evidence.filter((e) => e.area === "competitors").map((e) => e.id),
    ),
    dim(
      "audience_clarity",
      has("audience", ["confirmed"]) ? "strong" : has("audience", ["partial"]) ? "acceptable" : "weak",
      "Ясность сегментов и гипотез аудитории.",
      ws.evidence.filter((e) => e.area === "audience").map((e) => e.id),
    ),
    dim(
      "economic_viability",
      has("economics", ["confirmed"])
        ? "acceptable"
        : has("economics", ["missing", "conflicting"])
          ? type === "NO_GO"
            ? "critical"
            : "weak"
          : "insufficient_data",
      "Unit-экономика и бюджетные диапазоны.",
      ws.evidence.filter((e) => e.area === "economics").map((e) => e.id),
      has("economics", ["confirmed"]) ? undefined : "Экономика не подтверждена",
    ),
    dim(
      "execution_feasibility",
      type === "INSUFFICIENT_DATA" ? "insufficient_data" : type === "NO_GO" ? "weak" : "acceptable",
      "Оценка исполнимости в рамках constraints brief.",
      [],
    ),
    dim(
      "risk_exposure",
      ws.risks.some((r) => r.severity === "critical")
        ? "critical"
        : ws.risks.some((r) => r.severity === "high")
          ? "weak"
          : "acceptable",
      "Открытые риски из Risk Register.",
      ws.risks.flatMap((r) => r.evidenceIds),
    ),
    dim(
      "evidence_quality",
      type === "GO" ? "strong" : type === "CONDITIONAL_GO" ? "acceptable" : type === "NO_GO" ? "acceptable" : "insufficient_data",
      "Качество и полнота Evidence Register относительно решения.",
      ws.evidence.map((e) => e.id),
    ),
  ];
}

function buildTriggers(
  type: BusinessVerdictType,
  ws: InvestigationWorkspace,
): VerdictChangeTrigger[] {
  if (type === "GO") {
    return [
      {
        id: "tr_go_1",
        description: "Провал пилота по CAC",
        currentState: "Экономика acceptable",
        threshold: "CAC выше допустимого порога маржи",
        possibleTransition: "GO → CONDITIONAL_GO или NO_GO",
      },
      {
        id: "tr_go_2",
        description: "Регуляторное ограничение",
        currentState: ws.brief.keyConstraints || "constraints зафиксированы",
        threshold: "Новый запрет канала / креатива",
        possibleTransition: "GO → CONDITIONAL_GO",
      },
    ];
  }
  if (type === "CONDITIONAL_GO") {
    return [
      {
        id: "tr_cg_1",
        description: "Willingness-to-pay / цена подтверждена",
        currentState: "Цена или маржа incomplete",
        threshold: "Target price confirmed в тесте",
        possibleTransition: "CONDITIONAL_GO → GO",
      },
      {
        id: "tr_cg_2",
        description: "Economics остаются unknown после срока",
        currentState: "Conditions open",
        threshold: "Условия не закрыты к milestone",
        possibleTransition: "CONDITIONAL_GO → INSUFFICIENT_DATA или NO_GO",
      },
    ];
  }
  if (type === "NO_GO") {
    return [
      {
        id: "tr_ng_1",
        description: "Gross margin / unit economics улучшены",
        currentState: "Структурно неприемлемая экономика",
        threshold: "Маржа выше required threshold",
        possibleTransition: "NO_GO → CONDITIONAL_GO",
      },
      {
        id: "tr_ng_2",
        description: "Новый demand evidence",
        currentState: "Слабый demand",
        threshold: "Подтверждённый спрос в целевом geo",
        possibleTransition: "NO_GO → CONDITIONAL_GO",
      },
    ];
  }
  return [
    {
      id: "tr_id_1",
      description: "Закрыты critical missing data",
      currentState: "Coverage слишком низкое",
      threshold: "Readiness ≥ conditionally_ready без critical gaps",
      possibleTransition: "INSUFFICIENT_DATA → CONDITIONAL_GO или GO/NO_GO",
    },
  ];
}
