/**
 * Deterministic Marketing Strategy builder — not LLM / API.
 * Must never contradict the Business Verdict.
 */

import type { InvestigationWorkspace } from "@/lib/investigation/types";
import { evaluateExecutionReadiness } from "@/lib/strategy/execution-readiness";
import type {
  AudienceSegment,
  MarketingStrategy,
  StrategyCondition,
  StrategyOffer,
} from "@/lib/strategy/types";
import type { BusinessVerdict } from "@/lib/verdict/types";

export function buildMarketingStrategy(
  verdict: BusinessVerdict,
  investigation: InvestigationWorkspace | null,
  opts: { version: number; supersedesStrategyId: string | null },
): MarketingStrategy {
  if (verdict.type !== "GO" && verdict.type !== "CONDITIONAL_GO") {
    throw new Error(
      `Strategy builder refused verdict type ${verdict.type} — use Pivot or Investigation.`,
    );
  }

  const isConditional = verdict.type === "CONDITIONAL_GO";
  const now = new Date().toISOString();
  const geo =
    investigation?.brief.geography ||
    verdict.scorecard.find((d) => d.id === "market_attractiveness")?.explanation ||
    "Defined geography from verdict";

  const segments = buildSegments(verdict, investigation, isConditional);
  const primarySeg = segments.find((s) => s.priority === "primary") ?? segments[0]!;
  const offers = buildOffers(primarySeg, isConditional, verdict);
  const conditions = buildConditions(verdict, isConditional);

  const draft: Omit<MarketingStrategy, "executionReadiness"> = {
    id: `strat_${verdict.projectId}_v${opts.version}_${Math.random().toString(36).slice(2, 7)}`,
    projectId: verdict.projectId,
    projectName: verdict.projectName,
    verdictId: verdict.id,
    verdictVersion: verdict.version,
    verdictType: verdict.type,
    version: opts.version,
    status: isConditional && conditions.some((c) => c.blocksExecution) ? "blocked" : "draft",
    createdAt: now,
    updatedAt: now,
    updatedAtLabel: "локальный mock · Product Alpha A5",
    supersedesStrategyId: opts.supersedesStrategyId,
    evidenceSnapshotId: verdict.evidenceSnapshotId,
    localMockLabel: "Local mock · deterministic strategy · not LLM",
    summary: {
      businessObjective: isConditional
        ? `Валидировать жизнеспособность «${verdict.projectName}» при выполнении условий вердикта`
        : `Подготовить go-to-market для «${verdict.projectName}» в заявленных ограничениях`,
      targetMarket: geo,
      primaryAudience: primarySeg.name,
      positioning: isConditional
        ? "Позиционирование как проверяемая гипотеза до закрытия economics/conditions"
        : "Доказательный оффер для приоритетного сегмента без slogans",
      coreOffer: offers.find((o) => o.kind === "core" || o.kind === "validation")?.name ?? "Core offer",
      channelMix: isConditional
        ? "Узкий test mix: content + direct outreach + 1 paid test"
        : "Сфокусированный mix: content, partnerships, paid search test",
      budgetRange: budgetRangeLabel(verdict, isConditional),
      keyConstraints: investigation?.brief.keyConstraints || "См. verdict constraints",
      criticalConditions: isConditional
        ? conditions.map((c) => c.unresolvedCondition).join("; ") || "Условия вердикта"
        : "Нет блокирующих conditions",
    },
    objectives: [
      {
        id: "obj_1",
        title: isConditional ? "Validate willingness to pay" : "Acquire first qualified leads",
        businessOutcome: isConditional
          ? "Подтвердить платёжеспособный спрос"
          : "Получить первые квалифицированные заявки",
        marketingOutcome: isConditional
          ? "Ценовой тест / validation offer"
          : "Стабильный поток SQL в primary segment",
        priority: "critical",
        timeframe: isConditional ? "2–4 недели" : "4–8 недель",
        successMetric: isConditional ? "WTP confirmation rate" : "Qualified lead rate",
        baseline: "unknown / intake",
        target: isConditional ? "≥ порога из conditions" : "Диапазон из metrics gate",
        dependency: isConditional ? "Economics condition" : "Offer + landing ready",
        linkedVerdictCriterion: "economic_viability",
      },
      {
        id: "obj_2",
        title: "Prove unit economics band",
        businessOutcome: "Понять допустимый CAC относительно маржи",
        marketingOutcome: "Тест канала с measurable CAC",
        priority: isConditional ? "critical" : "high",
        timeframe: "4–6 недель",
        successMetric: "CAC range vs contribution",
        baseline: "unknown or range from verdict",
        target: "CAC ниже contribution threshold",
        dependency: "Gross margin / price clarity",
        linkedVerdictCriterion: "economic_viability",
      },
      {
        id: "obj_3",
        title: "Validate primary segment",
        businessOutcome: "Подтвердить, что primary audience — покупатели",
        marketingOutcome: "Интервью / response rate на оффер",
        priority: "high",
        timeframe: "2–3 недели",
        successMetric: "Segment response / interview confirmations",
        baseline: primarySeg.validationStatus,
        target: "evidence_supported_hypothesis или confirmed",
        dependency: "Audience evidence",
        linkedVerdictCriterion: "audience_clarity",
      },
      {
        id: "obj_4",
        title: isConditional ? "Reduce acquisition risk before scale" : "Enter defined geography",
        businessOutcome: isConditional
          ? "Не масштабировать до закрытия условий"
          : `Сфокусированный запуск в ${geo}`,
        marketingOutcome: isConditional ? "Stop-loss на spend" : "Geo-limited campaigns",
        priority: "medium",
        timeframe: "ongoing",
        successMetric: isConditional ? "Spend ≤ test cap" : "Geo coverage + lead quality",
        baseline: "—",
        target: isConditional ? "No scale beyond validation" : "Primary geo active",
        dependency: "Budget gate",
        linkedVerdictCriterion: "risk_exposure",
      },
    ],
    segments,
    positioning: {
      targetCustomer: primarySeg.name,
      category: investigation?.brief.product
        ? categoryFromProduct(investigation.brief.product)
        : "B2B service offer",
      coreProblem: primarySeg.problem,
      alternativeUsed: "Статус-кво: разрозненные каналы / ручной поиск клиентов",
      primaryDifferentiation:
        "Сфокусированный оффер под один сегмент с проверяемыми proof points из evidence",
      proof: verdict.supportingEvidence[0]?.claim ?? "Evidence Register (verdict)",
      reasonToBelieve: "Вердикт и evidence coverage, не слоган",
      keyMessage: isConditional
        ? `Проверяем, стоит ли масштабировать «${verdict.projectName}» на условиях вердикта`
        : `Для ${primarySeg.name}: предсказуемый результат без размытого «AI-powered» обещания`,
      positioningRisks: isConditional
        ? "Риск overclaim до закрытия economics"
        : "Риск смешения сегментов и размытия сообщения",
    },
    offers,
    channels: [
      {
        id: "ch_content",
        channel: "content",
        label: "Content",
        role: "Educate primary segment; support SEO/sales",
        funnelStage: "interest",
        targetSegmentId: primarySeg.id,
        expectedSignal: "Engagement + inbound questions",
        costClass: "low",
        evidenceNote: "Low-cost learning channel",
        dependency: "Key message approved",
        risk: "Slow signal",
        status: "recommended",
      },
      {
        id: "ch_direct",
        channel: "direct_sales",
        label: "Direct outreach",
        role: isConditional ? "Validation conversations" : "Primary acquisition assist",
        funnelStage: "qualification",
        targetSegmentId: primarySeg.id,
        expectedSignal: "Meetings / WTP feedback",
        costClass: "medium",
        evidenceNote: "Tied to audience hypothesis",
        dependency: "Segment list",
        risk: "Founder bandwidth",
        status: isConditional ? "test" : "recommended",
      },
      {
        id: "ch_paid",
        channel: "paid_search",
        label: "Paid search",
        role: "Controlled demand test",
        funnelStage: "awareness",
        targetSegmentId: primarySeg.id,
        expectedSignal: "CAC / intent signal",
        costClass: "high",
        evidenceNote: isConditional ? "Only after price hypothesis" : "Limited test budget",
        dependency: isConditional ? "WTP condition" : "Landing + offer",
        risk: "CAC spike",
        status: isConditional ? "conditional" : "test",
      },
      {
        id: "ch_tg",
        channel: "telegram",
        label: "Telegram",
        role: "Community / nurture",
        funnelStage: "retention",
        targetSegmentId: primarySeg.id,
        expectedSignal: "Reply rate",
        costClass: "low",
        evidenceNote: "Optional",
        dependency: "Content cadence",
        risk: "Noise",
        status: "excluded",
      },
      {
        id: "ch_infl",
        channel: "influencer",
        label: "Influencer",
        role: "Not primary",
        funnelStage: "awareness",
        targetSegmentId: primarySeg.id,
        expectedSignal: "—",
        costClass: "unknown",
        evidenceNote: "No evidence for fit",
        dependency: "—",
        risk: "Brand mismatch",
        status: "excluded",
      },
    ],
    funnel: [
      {
        id: "awareness",
        label: "Awareness",
        userAction: "Обнаруживает проблему / оффер",
        businessAction: "Точечный контент + ограниченный paid test",
        channel: "content / paid search",
        asset: "Landing / lead magnet",
        metric: "Qualified visit rate",
        exitCriterion: "Понятный интерес к офферу",
        risk: "Нецелевой трафик",
      },
      {
        id: "interest",
        label: "Interest",
        userAction: "Изучает proof / comparison",
        businessAction: "Дать evidence-linked messaging",
        channel: "content",
        asset: "Comparison / case note",
        metric: "Content engagement",
        exitCriterion: "Запрос следующего шага",
        risk: "Слабый proof",
      },
      {
        id: "qualification",
        label: "Qualification",
        userAction: "Оставляет заявку / отвечает на outreach",
        businessAction: "Квалификация по сегменту и budget fit",
        channel: "direct sales",
        asset: "Qualification script",
        metric: "SQL rate",
        exitCriterion: "Fit = primary segment",
        risk: "Мусорные лиды",
      },
      {
        id: "validation",
        label: "Validation",
        userAction: "Участвует в цене / пилоте",
        businessAction: isConditional ? "WTP / economics test" : "Pilot offer",
        channel: "direct / validation offer",
        asset: "Validation offer page",
        metric: isConditional ? "WTP result" : "Pilot conversion",
        exitCriterion: isConditional ? "Condition success criterion" : "Pilot accepted",
        risk: "Ложноположительный сигнал",
      },
      {
        id: "conversion",
        label: "Conversion",
        userAction: "Покупает / подписывает",
        businessAction: "Закрытие core offer",
        channel: "direct sales",
        asset: "Offer / contract pack",
        metric: "Close rate",
        exitCriterion: "Paid conversion",
        risk: isConditional ? "Blocked until conditions" : "Discount pressure",
      },
      {
        id: "onboarding",
        label: "Onboarding",
        userAction: "Стартует использование",
        businessAction: "Передача результата",
        channel: "email / ops",
        asset: "Onboarding material",
        metric: "Time-to-value",
        exitCriterion: "First value delivered",
        risk: "Churn early",
      },
      {
        id: "retention",
        label: "Retention",
        userAction: "Продолжает",
        businessAction: "Nurture + upsell hypothesis",
        channel: "email",
        asset: "Nurture sequence",
        metric: "Retention / repeat",
        exitCriterion: "Stable usage",
        risk: "Over-promise",
      },
      {
        id: "referral",
        label: "Referral",
        userAction: "Рекомендует",
        businessAction: "Ask for intro",
        channel: "referral",
        asset: "Referral ask",
        metric: "Referral rate",
        exitCriterion: "Warm intro",
        risk: "Premature ask",
      },
    ],
    assets: [
      {
        id: "as_1",
        kind: "landing_page",
        label: "Landing page",
        purpose: "Донести key message и CTA",
        targetSegmentId: primarySeg.id,
        funnelStage: "awareness",
        linkedMessage: "Positioning key message",
        dependency: "Positioning locked",
        priority: "critical",
        status: "planned",
      },
      {
        id: "as_2",
        kind: "offer_page",
        label: isConditional ? "Validation offer page" : "Core offer page",
        purpose: isConditional ? "Ценовой / scope тест" : "Конверсия в SQL",
        targetSegmentId: primarySeg.id,
        funnelStage: "validation",
        linkedMessage: "Offer promise",
        dependency: isConditional ? "Price hypothesis" : "Core offer",
        priority: "critical",
        status: isConditional ? "blocked" : "planned",
      },
      {
        id: "as_3",
        kind: "sales_deck",
        label: "Sales deck",
        purpose: "Discovery / close assist",
        targetSegmentId: primarySeg.id,
        funnelStage: "qualification",
        linkedMessage: "Proof + differentiation",
        dependency: "Evidence excerpts",
        priority: "high",
        status: "planned",
      },
      {
        id: "as_4",
        kind: "case_study",
        label: "Case / proof note",
        purpose: "Reason to believe",
        targetSegmentId: primarySeg.id,
        funnelStage: "interest",
        linkedMessage: "Proof",
        dependency: "Available proof from evidence",
        priority: "medium",
        status: "deferred",
      },
    ],
    budget: buildBudget(verdict, isConditional),
    metrics: [
      {
        id: "m_1",
        category: "validation",
        name: "Willingness-to-pay result",
        purpose: "Подтвердить ценовую гипотезу",
        baseline: "unknown",
        target: isConditional ? "Condition success" : "Confirmed band",
        measurementPeriod: "2–4 weeks",
        dataSource: "Validation interviews / offer tests",
        decisionThreshold: "Fail → revise offer / revisit verdict",
        actionIfMissed: "Stop paid scale; update verdict conditions",
      },
      {
        id: "m_2",
        category: "marketing",
        name: "Qualified lead rate",
        purpose: "Качество трафика и оффера",
        baseline: "—",
        target: "Segment-fit SQL share",
        measurementPeriod: "weekly",
        dataSource: "CRM / intake log (mock)",
        decisionThreshold: "Low SQL → message/segment fix",
        actionIfMissed: "Pause weak channel",
      },
      {
        id: "m_3",
        category: "business",
        name: "CAC range",
        purpose: "Сравнить с contribution",
        baseline: "unknown/range",
        target: "Below contribution threshold",
        measurementPeriod: "campaign test window",
        dataSource: "Spend + SQL (mock)",
        decisionThreshold: "CAC above threshold",
        actionIfMissed: "Stop-loss; no scale",
      },
      {
        id: "m_4",
        category: "stop_loss",
        name: "Test spend cap",
        purpose: "Не сжечь бюджет на гипотезе",
        baseline: budgetRangeLabel(verdict, isConditional),
        target: "Stay within validation envelope",
        measurementPeriod: "continuous",
        dataSource: "Budget tracker (mock)",
        decisionThreshold: "Hit cap without learning",
        actionIfMissed: "Freeze acquisition; review strategy",
      },
      {
        id: "m_5",
        category: "risk_indicator",
        name: "Gross margin clarity",
        purpose: "Economics gate",
        baseline: isConditional ? "incomplete" : "acceptable band",
        target: "Known range",
        measurementPeriod: "before scale",
        dataSource: "Owner finance / intake",
        decisionThreshold: "Still unknown at milestone",
        actionIfMissed: "Keep execution blocked",
      },
    ],
    conditions,
    risks: verdict.risks.map((r) => ({
      id: `sr_${r.id}`,
      title: `Strategy impact: ${r.title}`,
      source: "Verdict risk register",
      probability: r.probability,
      severity: r.severity,
      impact: `Влияет на канал/бюджет: ${r.businessConsequence}`,
      mitigation: r.mitigation,
      earlyWarning: `Sensitivity ${r.sensitivity}`,
      stopCondition:
        r.sensitivity === "verdict_changing"
          ? "Остановить scale; эскалация к обновлению вердикта"
          : "Скорректировать канал/оффер",
      linkedVerdictRiskId: r.id,
    })),
    assumptions: [
      ...verdict.assumptions.map((a) => ({
        id: `sa_${a.id}`,
        statement: a.statement,
        source: "Verdict assumptions",
        confidence: a.confidence,
        validationMethod: a.validationMethod,
        validationStage: a.validationStage,
        owner: "Owner / Research",
        impactIfFalse: a.effectIfFalse,
        status:
          a.state === "requires_validation"
            ? ("requires_validation" as const)
            : a.state === "confirmed"
              ? ("confirmed" as const)
              : ("accepted_for_planning" as const),
      })),
      {
        id: "sa_geo",
        statement: `Старт ограничен географией: ${geo}`,
        source: "Investigation brief",
        confidence: "medium",
        validationMethod: "Lead geo quality check",
        validationStage: "First acquisition wave",
        owner: "Marketing lead",
        impactIfFalse: "Пересбор channel mix",
        status: "accepted_for_planning",
      },
    ],
  };

  const executionReadiness = evaluateExecutionReadiness(draft, verdict);

  return { ...draft, executionReadiness };
}

function categoryFromProduct(product: string): string {
  const p = product.toLowerCase();
  if (p.includes("лид") || p.includes("lead")) return "Lead generation service";
  if (p.includes("saas")) return "B2B SaaS";
  return "Professional service offer";
}

function budgetRangeLabel(verdict: BusinessVerdict, isConditional: boolean): string {
  const econ = verdict.scorecard.find((d) => d.id === "economic_viability");
  if (!econ || econ.rating === "insufficient_data" || econ.rating === "weak") {
    return isConditional
      ? "Minimum test budget only · exact ROI unknown · insufficient precision"
      : "Recommended range · exact figures unknown";
  }
  return isConditional
    ? "Validation envelope (range) · no guaranteed ROI"
    : "Launch range from verdict economics · no guaranteed ROI";
}

function buildSegments(
  verdict: BusinessVerdict,
  investigation: InvestigationWorkspace | null,
  isConditional: boolean,
): AudienceSegment[] {
  const hyp = investigation?.brief.audienceHypotheses ?? [];
  const primaryName = hyp[0] || "Primary target segment (from verdict)";
  const secondaryName = hyp[1] || "Secondary adjacent segment";

  return [
    {
      id: "seg_primary",
      name: primaryName,
      model: "b2b",
      problem: "Непредсказуемый поток клиентов / загрузка",
      desiredOutcome: "Стабильные квалифицированные заявки",
      buyingTrigger: "Пустующее расписание / рост CAC текущего канала",
      objections: "Цена, доверие, сроки результата",
      decisionMaker: "Owner / commercial lead",
      userVsBuyer: "Buyer ≈ decision maker; users = ops/staff",
      evidenceStrength: isConditional ? "medium" : "high",
      priority: "primary",
      validationStatus: isConditional
        ? "evidence_supported_hypothesis"
        : "confirmed",
    },
    {
      id: "seg_secondary",
      name: secondaryName,
      model: "b2b",
      problem: "Смежные потребности",
      desiredOutcome: "Опциональный рост",
      buyingTrigger: "После proof на primary",
      objections: "Приоритет неясен",
      decisionMaker: "Varies",
      userVsBuyer: "May differ",
      evidenceStrength: "low",
      priority: "secondary",
      validationStatus: "unvalidated_hypothesis",
    },
    {
      id: "seg_excl",
      name: "Broad SMB cold spray",
      model: "b2b",
      problem: "—",
      desiredOutcome: "—",
      buyingTrigger: "—",
      objections: "—",
      decisionMaker: "—",
      userVsBuyer: "—",
      evidenceStrength: "low",
      priority: "excluded",
      validationStatus: "unvalidated_hypothesis",
    },
  ];
}

function buildOffers(
  primary: AudienceSegment,
  isConditional: boolean,
  verdict: BusinessVerdict,
): StrategyOffer[] {
  const priceMode = isConditional ? "hypothesis" : "range";
  return [
    {
      id: "off_validation",
      name: isConditional ? "Validation offer" : "Entry diagnostic",
      kind: isConditional ? "validation" : "entry",
      targetSegmentId: primary.id,
      customerProblem: primary.problem,
      promisedOutcome: "Проверяемый результат на ограниченном scope",
      scope: "Narrow geo / limited volume",
      priceMode,
      priceValue: isConditional ? "hypothesis · unknown exact" : "range · from economics band",
      proof: verdict.supportingEvidence[0]?.claim ?? "Evidence-linked proof",
      riskReversal: "Ограниченный пилот / clear stop criteria",
      callToAction: isConditional ? "Записаться на validation call" : "Запросить пилот",
      validationStatus: isConditional
        ? "unvalidated_hypothesis"
        : "evidence_supported_hypothesis",
    },
    {
      id: "off_core",
      name: "Core delivery package",
      kind: "core",
      targetSegmentId: primary.id,
      customerProblem: primary.problem,
      promisedOutcome: primary.desiredOutcome,
      scope: "Primary segment only",
      priceMode: isConditional ? "unknown" : "range",
      priceValue: isConditional ? "unknown until conditions closed" : "range",
      proof: "Case/proof note when available",
      riskReversal: "Milestone-based delivery",
      callToAction: "Перейти к коммерческому предложению",
      validationStatus: isConditional
        ? "unvalidated_hypothesis"
        : "evidence_supported_hypothesis",
    },
  ];
}

function buildConditions(
  verdict: BusinessVerdict,
  isConditional: boolean,
): StrategyCondition[] {
  if (!isConditional) {
    return verdict.conditions.slice(0, 1).map((c) => ({
      id: `sc_${c.id}`,
      unresolvedCondition: c.requiredAction,
      requiredAction: c.requiredAction,
      successCriterion: c.successCriterion,
      owner: c.owner,
      deadline: c.deadlineOrMilestone,
      evidenceRequired: c.evidenceRequired,
      effectOnStrategy: "Dependency, не блокирует planning",
      blocksExecution: false,
    }));
  }

  const fromVerdict = verdict.conditions.map((c) => ({
    id: `sc_${c.id}`,
    unresolvedCondition: c.requiredAction,
    requiredAction: c.requiredAction,
    successCriterion: c.successCriterion,
    owner: c.owner,
    deadline: c.deadlineOrMilestone,
    evidenceRequired: c.evidenceRequired,
    effectOnStrategy: "Блокирует execution plan до закрытия",
    blocksExecution: true,
  }));

  if (fromVerdict.length > 0) return fromVerdict;

  return [
    {
      id: "sc_default_econ",
      unresolvedCondition: "Economics / margin still incomplete",
      requiredAction: "Закрыть gross margin или явный unknown с validation plan",
      successCriterion: "Margin range known or formally deferred with cap",
      owner: "Owner",
      deadline: "Before Implementation Plan",
      evidenceRequired: "Updated economics evidence item",
      effectOnStrategy: "Paid scale остаётся blocked",
      blocksExecution: true,
    },
  ];
}

function buildBudget(verdict: BusinessVerdict, isConditional: boolean) {
  const unclear =
    verdict.scorecard.find((d) => d.id === "economic_viability")?.rating ===
      "insufficient_data" ||
    verdict.scorecard.find((d) => d.id === "economic_viability")?.rating === "weak";

  const range = unclear
    ? "insufficient data · use minimum test budget only"
    : isConditional
      ? "range · validation envelope"
      : "range · launch allocation";

  return [
    {
      id: "b_1",
      section: "Research and validation",
      amountOrRange: unclear ? "minimum test budget" : range,
      percentageLabel: unclear ? "unknown %" : isConditional ? "~30–40%" : "~15–25%",
      rationale: "Сначала learning, не scale",
      condition: isConditional ? "Mandatory before paid scale" : "Recommended",
      risk: "Skipping validation",
      expectedLearning: "WTP / segment fit",
    },
    {
      id: "b_2",
      section: "Content and assets",
      amountOrRange: range,
      percentageLabel: unclear ? "unknown %" : "~20–30%",
      rationale: "Landing + offer + deck",
      condition: "Message locked",
      risk: "Asset delay",
      expectedLearning: "Message-market fit signals",
    },
    {
      id: "b_3",
      section: "Acquisition",
      amountOrRange: isConditional
        ? "capped test only · unknown exact ROI"
        : range,
      percentageLabel: unclear ? "unknown %" : isConditional ? "~10–20% capped" : "~35–45%",
      rationale: "Controlled channel tests",
      condition: isConditional ? "After economics condition" : "After landing live",
      risk: "CAC overrun",
      expectedLearning: "CAC band",
    },
    {
      id: "b_4",
      section: "Tools",
      amountOrRange: "low fixed / unknown",
      percentageLabel: "~5–10%",
      rationale: "CRM / analytics mock stack",
      condition: "—",
      risk: "Tool sprawl",
      expectedLearning: "Measurement readiness",
    },
    {
      id: "b_5",
      section: "Specialist work",
      amountOrRange: range,
      percentageLabel: unclear ? "unknown %" : "~15–25%",
      rationale: "Strategy ops / research follow-up",
      condition: "—",
      risk: "Bandwidth",
      expectedLearning: "Execution quality",
    },
    {
      id: "b_6",
      section: "Contingency reserve",
      amountOrRange: "reserve · not ROI forecast",
      percentageLabel: "~10%",
      rationale: "Buffer for failed tests",
      condition: "Do not spend on vanity",
      risk: "Reserve raid",
      expectedLearning: "Optionality",
    },
  ];
}
