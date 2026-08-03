/**
 * Deterministic Verdict Readiness — NOT a business GO/NO_GO verdict.
 */

import type {
  ContradictionItem,
  EvidenceItem,
  InvestigationArea,
  MissingDataItem,
  VerdictReadinessResult,
  VerdictReadinessStatus,
} from "@/lib/investigation/types";

const CORE_AREAS: InvestigationArea[] = [
  "market",
  "audience",
  "economics",
  "risks",
];

function areaCovered(evidence: EvidenceItem[], area: InvestigationArea): boolean {
  return evidence.some(
    (e) =>
      e.area === area &&
      (e.state === "confirmed" || e.state === "partial") &&
      e.confidence !== "low",
  );
}

export function evaluateVerdictReadiness(input: {
  evidence: EvidenceItem[];
  missingData: MissingDataItem[];
  contradictions: ContradictionItem[];
}): VerdictReadinessResult {
  const { evidence, missingData, contradictions } = input;

  const completedAreas = CORE_AREAS.filter((a) => areaCovered(evidence, a));
  const openCriticalMissing = missingData.filter(
    (m) =>
      (m.severity === "critical" || m.severity === "high") &&
      m.resolution === "open",
  );
  const blockingContradictions = contradictions.filter(
    (c) => c.blocksVerdict && !c.resolved,
  );
  const assumed = missingData.filter((m) => m.resolution === "assumed");

  const blockingGaps: string[] = [
    ...openCriticalMissing.map((m) => m.missingInformation),
    ...blockingContradictions.map(
      (c) => `Противоречие: ${c.statementA.slice(0, 60)}…`,
    ),
  ];

  const unresolvedAssumptions = assumed.map(
    (m) => m.assumptionNote || m.missingInformation,
  );

  const recommendedNextActions: string[] = [];
  for (const m of openCriticalMissing) {
    recommendedNextActions.push(m.recommendedAction);
  }
  for (const c of blockingContradictions) {
    recommendedNextActions.push(c.requiredResolution);
  }

  const missingCore = CORE_AREAS.filter((a) => !completedAreas.includes(a));
  for (const a of missingCore) {
    recommendedNextActions.push(`Усилить evidence по области: ${a}`);
  }

  let status: VerdictReadinessStatus;

  if (
    openCriticalMissing.some((m) => m.severity === "critical") ||
    blockingContradictions.length > 0 ||
    completedAreas.length < 2
  ) {
    status = "not_ready";
  } else if (
    openCriticalMissing.length > 0 ||
    assumed.length > 0 ||
    completedAreas.length < CORE_AREAS.length ||
    evidence.some((e) => e.state === "conflicting" || e.state === "missing")
  ) {
    status = "conditionally_ready";
  } else {
    status = "ready_for_review";
  }

  if (status === "not_ready") {
    recommendedNextActions.push(
      "Закройте критические пробелы и противоречия до подготовки вердикта.",
    );
  } else if (status === "conditionally_ready") {
    recommendedNextActions.push(
      "Вердикт можно готовить только с явным acknowledgement оставшихся допущений.",
    );
  } else {
    recommendedNextActions.push(
      "Evidence coverage достаточна для review-версии вердикта (не авто-GO).",
    );
  }

  return {
    status,
    completedAreas,
    blockingGaps,
    unresolvedAssumptions,
    recommendedNextActions: [...new Set(recommendedNextActions)],
    notABusinessVerdict: true,
  };
}

export function canPrepareVerdict(
  readiness: VerdictReadinessResult,
  assumptionsAcknowledged: boolean,
): boolean {
  if (readiness.status === "not_ready") return false;
  if (readiness.status === "conditionally_ready") return assumptionsAcknowledged;
  return true;
}
