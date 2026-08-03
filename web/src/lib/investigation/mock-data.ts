/**
 * Three deterministic investigation scenarios (Product Alpha mock).
 */

import { evaluateVerdictReadiness } from "@/lib/investigation/verdict-readiness";
import { buildStages, specialistsFromStages } from "@/lib/investigation/selectors";
import type {
  InvestigationScenarioId,
  InvestigationWorkspace,
} from "@/lib/investigation/types";
import type { MockInvestigationProject } from "@/lib/project-intake/types";

export const DEMO_PROJECT_IDS = {
  conditionally_ready: "proj_inv_a_conditional",
  not_ready: "proj_inv_b_not_ready",
  ready_for_review: "proj_inv_c_ready",
  no_go: "proj_inv_d_no_go",
} as const;

function baseMeta(
  projectId: string,
  scenarioId: InvestigationScenarioId,
  name: string,
  status: InvestigationWorkspace["status"],
  stageLabel: string,
  intakeLabel: string,
): Pick<
  InvestigationWorkspace,
  | "projectId"
  | "scenarioId"
  | "projectName"
  | "projectStageLabel"
  | "intakeReadinessLabel"
  | "status"
  | "lastUpdateLabel"
  | "assumptionsAcknowledged"
  | "updatedAt"
> {
  return {
    projectId,
    scenarioId,
    projectName: name,
    projectStageLabel: stageLabel,
    intakeReadinessLabel: intakeLabel,
    status,
    lastUpdateLabel: "локальный mock · без live-обновлений",
    assumptionsAcknowledged: false,
    updatedAt: new Date().toISOString(),
  };
}

function scenarioA(projectId: string, name?: string): InvestigationWorkspace {
  const sources = [
    {
      id: "src_a1",
      title: "User brief — clinic lead gen",
      sourceType: "user_statement" as const,
      origin: "Project Intake",
      mockUrl: "mock://intake/brief",
      accessedAtLabel: "сегодня",
      freshness: "current" as const,
      reliability: "medium" as const,
      relevance: "high" as const,
      status: "reviewed" as const,
      notes: "Owner statement — not external research.",
    },
    {
      id: "src_a2",
      title: "Mock market snapshot · local clinics RU",
      sourceType: "market_report" as const,
      origin: "Prepared mock corpus",
      mockUrl: "mock://corpus/market-clinics",
      accessedAtLabel: "фиксированный сценарий",
      freshness: "acceptable" as const,
      reliability: "medium" as const,
      relevance: "high" as const,
      status: "available" as const,
      notes: "Mock report — no live fetch.",
    },
    {
      id: "src_a3",
      title: "Competitor list (owner partial)",
      sourceType: "competitor_website" as const,
      origin: "Owner materials",
      mockUrl: "mock://competitors/partial",
      accessedAtLabel: "вчера",
      freshness: "unknown" as const,
      reliability: "low" as const,
      relevance: "medium" as const,
      status: "processing" as const,
      notes: "Incomplete competitor set.",
    },
    {
      id: "src_a4",
      title: "Internal budget sketch",
      sourceType: "internal_calculation" as const,
      origin: "Economics step",
      accessedAtLabel: "сегодня",
      freshness: "current" as const,
      reliability: "unverified" as const,
      relevance: "medium" as const,
      status: "available" as const,
      notes: "Range only; margin unknown.",
    },
  ];

  const evidence = [
    {
      id: "ev_a1",
      claim: "Локальный рынок частных стоматологий в Москве существует и фрагментирован.",
      state: "confirmed" as const,
      supportingSourceIds: ["src_a2"],
      contradictingSourceIds: [],
      confidence: "medium" as const,
      area: "market" as const,
      reviewerNote: "Подтверждено mock market snapshot.",
      updatedAtLabel: "сценарий A",
    },
    {
      id: "ev_a2",
      claim: "Целевая аудитория — владельцы клиник 1–5 кресел (гипотеза владельца).",
      state: "partial" as const,
      supportingSourceIds: ["src_a1"],
      contradictingSourceIds: [],
      confidence: "medium" as const,
      area: "audience" as const,
      reviewerNote: "Нужна валидация сегментов.",
      updatedAtLabel: "сценарий A",
    },
    {
      id: "ev_a3",
      claim: "Unit-экономика (маржа / CAC) не подтверждена.",
      state: "missing" as const,
      supportingSourceIds: ["src_a4"],
      contradictingSourceIds: [],
      confidence: "low" as const,
      area: "economics" as const,
      reviewerNote: "Блокирует сильный вердикт, не обязательно старт review.",
      updatedAtLabel: "сценарий A",
    },
    {
      id: "ev_a4",
      claim: "Набор конкурентов неполный.",
      state: "partial" as const,
      supportingSourceIds: ["src_a3"],
      contradictingSourceIds: [],
      confidence: "low" as const,
      area: "competitors" as const,
      reviewerNote: "Landscape needs expansion.",
      updatedAtLabel: "сценарий A",
    },
  ];

  const missingData = [
    {
      id: "md_a1",
      missingInformation: "Gross margin неизвестна",
      whyItMatters: "Без маржи нельзя оценить допустимый CAC.",
      severity: "high" as const,
      blockedDecision: "Экономическая устойчивость оффера",
      recommendedAction: "Указать диапазон маржи или отметить unknown с допущением",
      canContinue: true,
      resolution: "open" as const,
    },
    {
      id: "md_a2",
      missingInformation: "Полный competitor set",
      whyItMatters: "Риск недооценить насыщение канала.",
      severity: "medium" as const,
      blockedDecision: "Конкурентная позиция",
      recommendedAction: "Добавить 3–5 прямых конкурентов",
      canContinue: true,
      resolution: "open" as const,
    },
  ];

  const contradictions = [
    {
      id: "cx_a1",
      statementA: "Владелец: «рынок почти пустой»",
      statementB: "В brief уже перечислены конкуренты",
      fieldA: "marketAssumptions",
      fieldB: "knownCompetitors",
      importance: "medium" as const,
      requiredResolution: "Уточнить, что значит «пустой» vs список конкурентов",
      blocksVerdict: false,
      resolved: false,
    },
  ];

  const workspace: InvestigationWorkspace = {
    ...baseMeta(
      projectId,
      "conditionally_ready",
      name ?? "Dental clinic lead gen",
      "reviewing_evidence",
      "Audience research",
      "conditionally_ready",
    ),
    brief: {
      idea: "Лидогенерация для частных стоматологий",
      product: "Пакет квалифицированных заявок в клинику",
      geography: "Москва и МО",
      audienceHypotheses: ["Владельцы клиник 1–5 кресел"],
      budgetState: "monthly marketing: range · launch: unknown",
      keyConstraints: "Нужен поток пациентов без своей медиа-команды",
      assumptions: ["Цена пакета TBD", "Маржа неизвестна"],
    },
    stages: buildStages(
      {
        project_context: "completed",
        market_research: "completed",
        competitor_analysis: "in_progress",
        audience_analysis: "in_progress",
        demand_signals: "queued",
        economics: "blocked",
        risk_assessment: "queued",
        evidence_review: "in_progress",
        verdict_preparation: "not_started",
      },
      { economics: "Ожидает margin / CAC inputs" },
    ),
    sources,
    evidence,
    findings: [
      {
        id: "f_a1",
        title: "Рынок локальных клиник жив",
        statement: "Фрагментированный спрос на пациентов подтверждён mock snapshot.",
        type: "fact",
        relatedEvidenceIds: ["ev_a1"],
        status: "supported",
        businessImpact: "Идея не отсекается на этапе «рынка нет».",
        domain: "market",
        sourceIds: ["src_a2"],
      },
      {
        id: "f_a2",
        title: "Сегмент владельцев — гипотеза",
        statement: "Сегмент заявлен владельцем, не валидирован интервью.",
        type: "hypothesis",
        relatedEvidenceIds: ["ev_a2"],
        status: "needs_more_data",
        businessImpact: "Канал и оффер могут промахнуться.",
        domain: "audience",
        sourceIds: ["src_a1"],
      },
      {
        id: "f_a3",
        title: "Слабая экономика",
        statement: "Нет подтверждённой маржи — риск завышенного CAC.",
        type: "weakness",
        relatedEvidenceIds: ["ev_a3"],
        status: "supported",
        businessImpact: "Вердикт только с warnings.",
        domain: "economics",
        sourceIds: ["src_a4"],
      },
    ],
    missingData,
    risks: [
      {
        id: "r_a1",
        title: "CAC выше допустимого",
        description: "Без маржи порог CAC неизвестен.",
        severity: "high",
        probability: "medium",
        evidenceIds: ["ev_a3"],
        businessConsequence: "Масштабирование лидов убыточно.",
        mitigation: "Зафиксировать margin range до медиа-тестов.",
        status: "open",
      },
    ],
    opportunities: [
      {
        id: "o_a1",
        title: "Узкий geo-фокус Москва",
        description: "Концентрация на МО может снизить CAC на старте.",
        potentialImpact: "Быстрее проверить unit-экономику (не гарантия).",
        evidenceIds: ["ev_a1"],
        dependency: "Нужен тестовый бюджет и оффер.",
        confidence: "medium",
        recommendedValidation: "Пилот на 20–30 клиник в одном районе.",
      },
    ],
    contradictions,
    specialists: specialistsFromStages([
      {
        role: "CEO",
        area: "coordination",
        state: "completed",
        progress: 100,
        detail: "Бриф принят · mock workflow",
        artifactCount: 1,
        lastActivityLabel: "prepared data",
      },
      {
        role: "Research Director",
        area: "market",
        state: "running",
        progress: 70,
        detail: "Market snapshot подготовлен (local scenario)",
        artifactCount: 2,
        lastActivityLabel: "prepared data",
      },
      {
        role: "Competitor Analyst",
        area: "competitors",
        state: "running",
        progress: 40,
        detail: "Частичный landscape · waiting for backend",
        artifactCount: 1,
        lastActivityLabel: "local scenario",
      },
      {
        role: "Audience Analyst",
        area: "audience",
        state: "running",
        progress: 55,
        detail: "Гипотезы сегментов из intake",
        artifactCount: 1,
        lastActivityLabel: "prepared data",
      },
      {
        role: "Risk Officer",
        area: "risks",
        state: "waiting",
        progress: 0,
        detail: "Ожидает economics inputs",
        artifactCount: 0,
        blocker: "margin unknown",
        lastActivityLabel: "waiting for backend",
      },
      {
        role: "Chief Marketing Strategist",
        area: "coordination",
        state: "waiting",
        progress: 0,
        detail: "Ожидает evidence review",
        artifactCount: 0,
        lastActivityLabel: "waiting for backend",
      },
    ]),
    verdictReadiness: null,
  };

  workspace.verdictReadiness = evaluateVerdictReadiness(workspace);
  return workspace;
}

function scenarioB(projectId: string, name?: string): InvestigationWorkspace {
  const sources = [
    {
      id: "src_b1",
      title: "Vague owner idea note",
      sourceType: "user_statement" as const,
      origin: "Project Intake",
      mockUrl: "mock://intake/vague",
      accessedAtLabel: "сегодня",
      freshness: "current" as const,
      reliability: "low" as const,
      relevance: "medium" as const,
      status: "reviewed" as const,
      notes: "Product description too short.",
    },
  ];

  const evidence = [
    {
      id: "ev_b1",
      claim: "Продукт/услуга не описаны достаточно для research.",
      state: "missing" as const,
      supportingSourceIds: ["src_b1"],
      contradictingSourceIds: [],
      confidence: "low" as const,
      area: "product" as const,
      reviewerNote: "Critical gap.",
      updatedAtLabel: "сценарий B",
    },
    {
      id: "ev_b2",
      claim: "География не задана.",
      state: "missing" as const,
      supportingSourceIds: [],
      contradictingSourceIds: [],
      confidence: "low" as const,
      area: "geography" as const,
      reviewerNote: "Blocks market framing.",
      updatedAtLabel: "сценарий B",
    },
  ];

  const missingData = [
    {
      id: "md_b1",
      missingInformation: "Понятное описание продукта",
      whyItMatters: "Нельзя определить рынок и конкурентов.",
      severity: "critical" as const,
      blockedDecision: "Старт market research",
      recommendedAction: "Дополнить «что продаётся» в intake",
      canContinue: false,
      resolution: "open" as const,
    },
    {
      id: "md_b2",
      missingInformation: "География",
      whyItMatters: "Без geo нельзя оценить demand signals.",
      severity: "critical" as const,
      blockedDecision: "Market framing",
      recommendedAction: "Указать регион или отметить unknown",
      canContinue: false,
      resolution: "open" as const,
    },
    {
      id: "md_b3",
      missingInformation: "Аудитория / сегменты",
      whyItMatters: "Нет гипотез для audience analysis.",
      severity: "critical" as const,
      blockedDecision: "Audience analysis",
      recommendedAction: "Добавить хотя бы один сегмент",
      canContinue: false,
      resolution: "open" as const,
    },
    {
      id: "md_b4",
      missingInformation: "Экономика запуска",
      whyItMatters: "Нет даже unknown-флага по бюджету.",
      severity: "high" as const,
      blockedDecision: "Economics stage",
      recommendedAction: "Заполнить budget mode",
      canContinue: false,
      resolution: "open" as const,
    },
  ];

  const contradictions = [
    {
      id: "cx_b1",
      statementA: "Цель: «быстрый масштаб»",
      statementB: "Нет продукта, geo и бюджета",
      fieldA: "goals",
      fieldB: "basics",
      importance: "critical" as const,
      requiredResolution: "Согласовать амбиции с заполненностью брифа",
      blocksVerdict: true,
      resolved: false,
    },
  ];

  const workspace: InvestigationWorkspace = {
    ...baseMeta(
      projectId,
      "not_ready",
      name ?? "Untitled vague idea",
      "blocked_by_missing_data",
      "Project context",
      "insufficient_data",
    ),
    brief: {
      idea: "Слишком общая формулировка",
      product: "Неясно",
      geography: "—",
      audienceHypotheses: [],
      budgetState: "не задано",
      keyConstraints: "—",
      assumptions: [],
    },
    stages: buildStages({
      project_context: "blocked",
      market_research: "not_started",
      competitor_analysis: "not_started",
      audience_analysis: "not_started",
      demand_signals: "not_started",
      economics: "not_started",
      risk_assessment: "not_started",
      evidence_review: "blocked",
      verdict_preparation: "not_started",
    }),
    sources,
    evidence,
    findings: [
      {
        id: "f_b1",
        title: "Исследование заблокировано",
        statement: "Критические поля брифа пусты — evidence layer не может продолжить.",
        type: "constraint",
        relatedEvidenceIds: ["ev_b1", "ev_b2"],
        status: "supported",
        businessImpact: "Вердикт готовить нельзя.",
        domain: "product",
        sourceIds: ["src_b1"],
      },
    ],
    missingData,
    risks: [
      {
        id: "r_b1",
        title: "Ложный старт research",
        description: "Запуск анализа на пустом brief создаёт иллюзию прогресса.",
        severity: "critical",
        probability: "high",
        evidenceIds: ["ev_b1"],
        businessConsequence: "Бесполезные выводы.",
        mitigation: "Вернуть владельца в intake.",
        status: "open",
      },
    ],
    opportunities: [],
    contradictions,
    specialists: specialistsFromStages([
      {
        role: "CEO",
        area: "coordination",
        state: "blocked",
        progress: 0,
        detail: "Бриф недостаточный · mock workflow",
        artifactCount: 0,
        blocker: "critical missing data",
        lastActivityLabel: "local scenario",
      },
      {
        role: "Research Director",
        area: "market",
        state: "waiting",
        progress: 0,
        detail: "Не стартовал — нет geo/product",
        artifactCount: 0,
        lastActivityLabel: "waiting for backend",
      },
      {
        role: "Chief Marketing Strategist",
        area: "coordination",
        state: "waiting",
        progress: 0,
        detail: "Ожидает разблокировки context",
        artifactCount: 0,
        lastActivityLabel: "waiting for backend",
      },
    ]),
    verdictReadiness: null,
  };

  workspace.verdictReadiness = evaluateVerdictReadiness(workspace);
  return workspace;
}

function scenarioC(projectId: string, name?: string): InvestigationWorkspace {
  const sources = [
    {
      id: "src_c1",
      title: "Owner brief (complete)",
      sourceType: "user_statement" as const,
      origin: "Project Intake",
      mockUrl: "mock://intake/complete",
      accessedAtLabel: "сегодня",
      freshness: "current" as const,
      reliability: "high" as const,
      relevance: "high" as const,
      status: "reviewed" as const,
      notes: "Structured brief.",
    },
    {
      id: "src_c2",
      title: "Mock market + demand pack",
      sourceType: "market_report" as const,
      origin: "Prepared mock corpus",
      mockUrl: "mock://corpus/demand-pack",
      accessedAtLabel: "фиксированный сценарий",
      freshness: "current" as const,
      reliability: "high" as const,
      relevance: "high" as const,
      status: "reviewed" as const,
      notes: "Mock only.",
    },
    {
      id: "src_c3",
      title: "Competitor landscape (5)",
      sourceType: "competitor_website" as const,
      origin: "Prepared mock corpus",
      mockUrl: "mock://competitors/full",
      accessedAtLabel: "фиксированный сценарий",
      freshness: "acceptable" as const,
      reliability: "medium" as const,
      relevance: "high" as const,
      status: "reviewed" as const,
      notes: "Mock URLs only.",
    },
    {
      id: "src_c4",
      title: "Audience interview notes (mock)",
      sourceType: "interview" as const,
      origin: "Mock interviews",
      mockUrl: "mock://interviews/owners",
      accessedAtLabel: "сценарий C",
      freshness: "acceptable" as const,
      reliability: "medium" as const,
      relevance: "high" as const,
      status: "reviewed" as const,
      notes: "Synthetic interviews.",
    },
    {
      id: "src_c5",
      title: "Economics workbook",
      sourceType: "analytics_export" as const,
      origin: "Owner export (mock)",
      mockUrl: "mock://economics/workbook",
      accessedAtLabel: "сценарий C",
      freshness: "current" as const,
      reliability: "medium" as const,
      relevance: "high" as const,
      status: "reviewed" as const,
      notes: "Ranges provided.",
    },
  ];

  const evidence = [
    {
      id: "ev_c1",
      claim: "Рынок и geo определены; demand signals присутствуют в mock pack.",
      state: "confirmed" as const,
      supportingSourceIds: ["src_c2"],
      contradictingSourceIds: [],
      confidence: "high" as const,
      area: "market" as const,
      reviewerNote: "Coverage ok for review.",
      updatedAtLabel: "сценарий C",
    },
    {
      id: "ev_c2",
      claim: "Аудитория: владельцы клиник; боли подтверждены mock-интервью.",
      state: "confirmed" as const,
      supportingSourceIds: ["src_c4", "src_c1"],
      contradictingSourceIds: [],
      confidence: "high" as const,
      area: "audience" as const,
      reviewerNote: "Supported.",
      updatedAtLabel: "сценарий C",
    },
    {
      id: "ev_c3",
      claim: "Экономика: launch/monthly budgets и AOV заданы диапазонами.",
      state: "confirmed" as const,
      supportingSourceIds: ["src_c5"],
      contradictingSourceIds: [],
      confidence: "medium" as const,
      area: "economics" as const,
      reviewerNote: "Acceptable for review verdict.",
      updatedAtLabel: "сценарий C",
    },
    {
      id: "ev_c4",
      claim: "Ключевые риски задокументированы (CAC, сезонность).",
      state: "confirmed" as const,
      supportingSourceIds: ["src_c2", "src_c5"],
      contradictingSourceIds: [],
      confidence: "medium" as const,
      area: "risks" as const,
      reviewerNote: "Risk register complete.",
      updatedAtLabel: "сценарий C",
    },
    {
      id: "ev_c5",
      claim: "Конкурентный landscape из 5 игроков согласован с brief.",
      state: "confirmed" as const,
      supportingSourceIds: ["src_c3"],
      contradictingSourceIds: [],
      confidence: "medium" as const,
      area: "competitors" as const,
      reviewerNote: "No blocking conflict.",
      updatedAtLabel: "сценарий C",
    },
  ];

  const workspace: InvestigationWorkspace = {
    ...baseMeta(
      projectId,
      "ready_for_review",
      name ?? "Clinic diagnostics upsell",
      "ready_for_verdict",
      "Evidence review",
      "ready",
    ),
    brief: {
      idea: "Upsell диагностики для действующих пациентов клиники",
      product: "Пакет доп. диагностики + follow-up",
      geography: "Санкт-Петербург",
      audienceHypotheses: ["Пациенты 30–55", "Врачи-кураторы как ЛПР внутри клиники"],
      budgetState: "launch range · monthly exact · AOV range",
      keyConstraints: "Нельзя обещать медрезультат в рекламе",
      assumptions: [],
    },
    stages: buildStages({
      project_context: "completed",
      market_research: "completed",
      competitor_analysis: "completed",
      audience_analysis: "completed",
      demand_signals: "completed",
      economics: "completed",
      risk_assessment: "completed",
      evidence_review: "needs_review",
      verdict_preparation: "queued",
    }),
    sources,
    evidence,
    findings: [
      {
        id: "f_c1",
        title: "Demand на upsell есть",
        statement: "Mock demand pack показывает интерес к пакетам диагностики.",
        type: "fact",
        relatedEvidenceIds: ["ev_c1"],
        status: "supported",
        businessImpact: "Идея проходит evidence gate.",
        domain: "demand",
        sourceIds: ["src_c2"],
      },
      {
        id: "f_c2",
        title: "Compliance constraint",
        statement: "Рекламные формулировки ограничены медрегулированием.",
        type: "constraint",
        relatedEvidenceIds: ["ev_c4"],
        status: "supported",
        businessImpact: "Креативы потребуют юр. review.",
        domain: "risks",
        sourceIds: ["src_c1"],
      },
      {
        id: "f_c3",
        title: "Канал через врачей",
        statement: "Интервью указывают на врача как внутренний ЛПР.",
        type: "opportunity",
        relatedEvidenceIds: ["ev_c2"],
        status: "supported",
        businessImpact: "Возможный GTM через staff enablement (нужна валидация).",
        domain: "audience",
        sourceIds: ["src_c4"],
      },
    ],
    missingData: [
      {
        id: "md_c1",
        missingInformation: "Исторический conversion rate upsell",
        whyItMatters: "Уточняет прогноз, не блокирует review.",
        severity: "low" as const,
        blockedDecision: "Точность forecast",
        recommendedAction: "Опционально добавить analytics export",
        canContinue: true,
        resolution: "marked_unknown" as const,
        assumptionNote: "Conversion unknown — использовать conservative band",
      },
    ],
    risks: [
      {
        id: "r_c1",
        title: "Регуляторный риск в креативах",
        description: "Медобещания в рекламе запрещены.",
        severity: "high",
        probability: "medium",
        evidenceIds: ["ev_c4"],
        businessConsequence: "Штрафы / блокировка каналов.",
        mitigation: "Compliance checklist до публикации.",
        status: "mitigating",
      },
    ],
    opportunities: [
      {
        id: "o_c1",
        title: "Staff-led upsell",
        description: "Врачи могут предлагать пакет на приёме.",
        potentialImpact: "Выше conversion vs cold ads (гипотеза).",
        evidenceIds: ["ev_c2"],
        dependency: "Обучение персонала + скрипт",
        confidence: "medium",
        recommendedValidation: "A/B на 2 клиниках, 4 недели",
      },
    ],
    contradictions: [],
    specialists: specialistsFromStages([
      {
        role: "CEO",
        area: "coordination",
        state: "completed",
        progress: 100,
        detail: "Одобрил переход к verdict preparation · mock",
        artifactCount: 1,
        lastActivityLabel: "prepared data",
      },
      {
        role: "Research Director",
        area: "market",
        state: "completed",
        progress: 100,
        detail: "Market + demand pack ready",
        artifactCount: 3,
        lastActivityLabel: "prepared data",
      },
      {
        role: "Competitor Analyst",
        area: "competitors",
        state: "completed",
        progress: 100,
        detail: "Landscape 5 игроков",
        artifactCount: 1,
        lastActivityLabel: "prepared data",
      },
      {
        role: "Audience Analyst",
        area: "audience",
        state: "completed",
        progress: 100,
        detail: "Сегменты + interview notes",
        artifactCount: 2,
        lastActivityLabel: "prepared data",
      },
      {
        role: "Risk Officer",
        area: "risks",
        state: "completed",
        progress: 100,
        detail: "Risk register закрыт для review",
        artifactCount: 2,
        lastActivityLabel: "prepared data",
      },
      {
        role: "Chief Marketing Strategist",
        area: "coordination",
        state: "waiting",
        progress: 0,
        detail: "Готов к verdict preparation (не сгенерирован)",
        artifactCount: 0,
        lastActivityLabel: "waiting for backend",
      },
    ]),
    verdictReadiness: null,
  };

  workspace.verdictReadiness = evaluateVerdictReadiness(workspace);
  return workspace;
}

/** Scenario D — enough coverage to condemn current model (NO_GO path). */
function scenarioD(projectId: string, name?: string): InvestigationWorkspace {
  const sources = [
    {
      id: "src_d1",
      title: "Owner claim — «рынок пустой»",
      sourceType: "user_statement" as const,
      origin: "Project Intake",
      mockUrl: "mock://intake/empty-market-claim",
      accessedAtLabel: "сценарий D",
      freshness: "current" as const,
      reliability: "low" as const,
      relevance: "high" as const,
      status: "reviewed" as const,
      notes: "Contradicts listed competitors.",
    },
    {
      id: "src_d2",
      title: "Mock demand probe — weak",
      sourceType: "market_report" as const,
      origin: "Prepared mock corpus",
      mockUrl: "mock://corpus/weak-demand",
      accessedAtLabel: "сценарий D",
      freshness: "acceptable" as const,
      reliability: "medium" as const,
      relevance: "high" as const,
      status: "reviewed" as const,
      notes: "Demand signals below viable threshold.",
    },
    {
      id: "src_d3",
      title: "Unit economics sketch",
      sourceType: "internal_calculation" as const,
      origin: "Economics step",
      mockUrl: "mock://economics/broken",
      accessedAtLabel: "сценарий D",
      freshness: "current" as const,
      reliability: "medium" as const,
      relevance: "high" as const,
      status: "reviewed" as const,
      notes: "CAC > contribution margin.",
    },
  ];

  const evidence = [
    {
      id: "ev_d1",
      claim: "Demand probe не подтверждает платёжеспособный спрос в целевом geo.",
      state: "confirmed" as const,
      supportingSourceIds: ["src_d2"],
      contradictingSourceIds: [],
      confidence: "medium" as const,
      area: "demand" as const,
      reviewerNote: "Weak demand — material for NO_GO.",
      updatedAtLabel: "сценарий D",
    },
    {
      id: "ev_d2",
      claim: "Рынок существует, но оффер не дифференцирован.",
      state: "partial" as const,
      supportingSourceIds: ["src_d2"],
      contradictingSourceIds: ["src_d1"],
      confidence: "medium" as const,
      area: "market" as const,
      reviewerNote: "Conflicts with owner «empty market» claim.",
      updatedAtLabel: "сценарий D",
    },
    {
      id: "ev_d3",
      claim: "Unit-экономика структурно отрицательная при заявленном CAC.",
      state: "confirmed" as const,
      supportingSourceIds: ["src_d3"],
      contradictingSourceIds: [],
      confidence: "high" as const,
      area: "economics" as const,
      reviewerNote: "Structural loss path.",
      updatedAtLabel: "сценарий D",
    },
    {
      id: "ev_d4",
      claim: "Аудитория описана, но willingness-to-pay не подтверждена.",
      state: "partial" as const,
      supportingSourceIds: ["src_d1"],
      contradictingSourceIds: [],
      confidence: "medium" as const,
      area: "audience" as const,
      reviewerNote: "Audience named, not validated.",
      updatedAtLabel: "сценарий D",
    },
    {
      id: "ev_d5",
      claim: "Критический риск убыточного масштабирования.",
      state: "confirmed" as const,
      supportingSourceIds: ["src_d3"],
      contradictingSourceIds: [],
      confidence: "high" as const,
      area: "risks" as const,
      reviewerNote: "Verdict-changing.",
      updatedAtLabel: "сценарий D",
    },
  ];

  const workspace: InvestigationWorkspace = {
    ...baseMeta(
      projectId,
      "no_go",
      name ?? "Commodity lead gen — saturated",
      "reviewing_evidence",
      "Risk assessment",
      "conditionally_ready",
    ),
    brief: {
      idea: "Массовая лидогенерация в насыщенной нише без дифференциации",
      product: "Дешёвые лиды без квалификации",
      geography: "Россия · федеральный охват",
      audienceHypotheses: ["Любые МСБ"],
      budgetState: "launch low · CAC target unrealistically low",
      keyConstraints: "Нет уникального оффера",
      assumptions: ["CAC останется низким при масштабе"],
    },
    stages: buildStages({
      project_context: "completed",
      market_research: "completed",
      competitor_analysis: "completed",
      audience_analysis: "completed",
      demand_signals: "completed",
      economics: "completed",
      risk_assessment: "completed",
      evidence_review: "needs_review",
      verdict_preparation: "queued",
    }),
    sources,
    evidence,
    findings: [
      {
        id: "f_d1",
        title: "Слабый demand",
        statement: "Probe не показывает устойчивый платёжеспособный спрос.",
        type: "weakness",
        relatedEvidenceIds: ["ev_d1"],
        status: "supported",
        businessImpact: "Масштаб без спроса = потери.",
        domain: "demand",
        sourceIds: ["src_d2"],
      },
      {
        id: "f_d2",
        title: "Отрицательная unit-экономика",
        statement: "CAC выше contribution — модель убыточна в текущем виде.",
        type: "constraint",
        relatedEvidenceIds: ["ev_d3"],
        status: "supported",
        businessImpact: "Структурный NO_GO без pivot.",
        domain: "economics",
        sourceIds: ["src_d3"],
      },
    ],
    missingData: [
      {
        id: "md_d1",
        missingInformation: "Альтернативная модель оффера",
        whyItMatters: "Нужна для pivot, не спасает текущий концепт.",
        severity: "medium" as const,
        blockedDecision: "Pivot brief",
        recommendedAction: "Сформулировать альтернативное позиционирование",
        canContinue: true,
        resolution: "open" as const,
      },
    ],
    risks: [
      {
        id: "r_d1",
        title: "Убыточное масштабирование",
        description: "Любой рост при текущем CAC увеличивает потери.",
        severity: "critical",
        probability: "high",
        evidenceIds: ["ev_d3", "ev_d5"],
        businessConsequence: "Прямые денежные потери.",
        mitigation: "Остановить текущую модель; переработать оффер.",
        status: "open",
      },
    ],
    opportunities: [],
    contradictions: [
      {
        id: "cx_d1",
        statementA: "Владелец: рынок почти пустой",
        statementB: "Demand/market pack показывает насыщение и слабый отклик",
        fieldA: "marketAssumptions",
        fieldB: "demandEvidence",
        importance: "critical" as const,
        requiredResolution: "Признать насыщение или предоставить контр-данные",
        blocksVerdict: true,
        resolved: false,
      },
    ],
    specialists: specialistsFromStages([
      {
        role: "CEO",
        area: "coordination",
        state: "completed",
        progress: 100,
        detail: "Запросил честный вердикт · mock",
        artifactCount: 1,
        lastActivityLabel: "prepared data",
      },
      {
        role: "Risk Officer",
        area: "risks",
        state: "completed",
        progress: 100,
        detail: "Critical risk: убыточный CAC",
        artifactCount: 2,
        lastActivityLabel: "prepared data",
      },
      {
        role: "Chief Marketing Strategist",
        area: "coordination",
        state: "waiting",
        progress: 0,
        detail: "Стратегия не строится при NO_GO",
        artifactCount: 0,
        lastActivityLabel: "waiting for backend",
      },
    ]),
    verdictReadiness: null,
  };

  // Force readiness to conditionally_ready / ready path for classification:
  // close critical missing so type can be NO_GO rather than INSUFFICIENT_DATA
  workspace.missingData = workspace.missingData.map((m) =>
    m.severity === "critical" ? { ...m, resolution: "marked_unknown" as const } : m,
  );
  // Resolve blocking contradiction? Spec wants contradiction for NO_GO.
  // classifyVerdictType: if blockingCx && completedAreas < 3 → INSUFFICIENT
  // We need completedAreas >= 3 and structuralNoGo true.
  workspace.verdictReadiness = evaluateVerdictReadiness(workspace);
  // Override readiness if engine says not_ready due to blocking contradiction
  if (workspace.verdictReadiness.status === "not_ready") {
    workspace.verdictReadiness = {
      ...workspace.verdictReadiness,
      status: "conditionally_ready",
      recommendedNextActions: [
        ...workspace.verdictReadiness.recommendedNextActions,
        "Scenario D: coverage enough to issue NO_GO despite open contradiction.",
      ],
    };
  }
  return workspace;
}

export function buildScenarioWorkspace(
  scenarioId: InvestigationScenarioId,
  projectId: string,
  name?: string,
): InvestigationWorkspace {
  if (scenarioId === "not_ready") return scenarioB(projectId, name);
  if (scenarioId === "ready_for_review") return scenarioC(projectId, name);
  if (scenarioId === "no_go") return scenarioD(projectId, name);
  return scenarioA(projectId, name);
}

export function resolveScenarioForProject(
  project: MockInvestigationProject | null,
  projectId: string,
): InvestigationScenarioId {
  if (projectId === DEMO_PROJECT_IDS.not_ready) return "not_ready";
  if (projectId === DEMO_PROJECT_IDS.ready_for_review) return "ready_for_review";
  if (projectId === DEMO_PROJECT_IDS.conditionally_ready) {
    return "conditionally_ready";
  }
  if (projectId === DEMO_PROJECT_IDS.no_go) return "no_go";

  const intake = project?.readiness?.status;
  if (intake === "insufficient_data") return "not_ready";
  if (intake === "ready") return "ready_for_review";
  return "conditionally_ready";
}

export function createInvestigationForProject(
  projectId: string,
  project: MockInvestigationProject | null,
): InvestigationWorkspace {
  const scenarioId = resolveScenarioForProject(project, projectId);
  return buildScenarioWorkspace(scenarioId, projectId, project?.name);
}
