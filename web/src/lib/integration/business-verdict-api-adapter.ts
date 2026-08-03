/**
 * P0.5 — BusinessVerdict API adapter (backend → Product Alpha view model).
 * Does not collapse with execution/publication approval.
 */

import type { BackendVerdictDto } from "@/lib/api/types/business-verdicts";
import type {
  BusinessVerdict,
  BusinessVerdictType,
  CounterEvidenceItem,
  VerdictAssumption,
  VerdictChangeTrigger,
  VerdictCondition,
  VerdictEvidenceLink,
  VerdictRiskItem,
  VerdictStatus,
} from "@/lib/verdict/types";
import type { ConfidenceLevel, EvidenceState } from "@/lib/investigation/types";

const TYPE_MAP: Record<string, BusinessVerdictType> = {
  go: "GO",
  conditional_go: "CONDITIONAL_GO",
  no_go: "NO_GO",
  insufficient_data: "INSUFFICIENT_DATA",
};

function mapStatus(lifecycle: string): VerdictStatus {
  if (lifecycle === "approved") return "approved";
  if (lifecycle === "under_review") return "under_review";
  if (lifecycle === "superseded") return "superseded";
  return "draft";
}

function mapConfidence(level: string): ConfidenceLevel {
  if (level === "high" || level === "medium" || level === "low") return level;
  return "low";
}

function mapEvidenceState(state: string): EvidenceState {
  const allowed: EvidenceState[] = [
    "confirmed",
    "partial",
    "conflicting",
    "missing",
    "outdated",
  ];
  return (allowed.includes(state as EvidenceState)
    ? state
    : "partial") as EvidenceState;
}

export function mapBackendVerdictToProductAlpha(
  dto: BackendVerdictDto,
  projectName: string,
): BusinessVerdict {
  const supportingEvidence: VerdictEvidenceLink[] = (dto.evidence_links || [])
    .filter((l) => l.role === "supports" || l.role === "condition_basis")
    .map((l) => ({
      evidenceId: l.evidence_id,
      claim: l.note || l.decision_criterion || l.evidence_id,
      state: mapEvidenceState(l.assessment_state_at_snapshot),
      sourceTitles: [],
      confidence: mapConfidence(l.confidence_at_snapshot),
      criterion: "evidence_quality",
      whyItMatters: l.decision_criterion || "Связано с вердиктом",
    }));

  const counterEvidence: CounterEvidenceItem[] = (dto.evidence_links || [])
    .filter((l) =>
      ["weakens", "contradicts", "risk_basis"].includes(l.role),
    )
    .map((l, i) => ({
      id: `ce_${i}`,
      conflictingClaim: l.note || l.decision_criterion || l.evidence_id,
      sourceTitle: "Evidence snapshot",
      impact: l.role,
      resolutionStatus: "open" as const,
      couldChangeVerdict: l.role === "contradicts",
    }));

  const risks: VerdictRiskItem[] = (dto.critical_risks || []).map((r, i) => {
    const sev = String(r.severity ?? "medium");
    const severity =
      sev === "critical" || sev === "high" || sev === "medium" || sev === "low"
        ? sev
        : "medium";
    const sens = String(r.verdict_sensitivity ?? "medium");
    const sensitivity =
      sens === "verdict_changing" ||
      sens === "high" ||
      sens === "medium" ||
      sens === "low"
        ? sens
        : "medium";
    return {
      id: `risk_${i}`,
      title: String(r.title ?? "Risk"),
      severity: severity as VerdictRiskItem["severity"],
      probability: mapConfidence(String(r.probability ?? "low")),
      businessConsequence: String(r.business_consequence ?? ""),
      evidenceIds: Array.isArray(r.linked_evidence_ids)
        ? (r.linked_evidence_ids as string[])
        : [],
      mitigation: String(r.mitigation ?? ""),
      sensitivity: sensitivity as VerdictRiskItem["sensitivity"],
    };
  });

  const assumptions: VerdictAssumption[] = (dto.assumptions || []).map((a, i) => {
    const st = String(a.status ?? "accepted_for_now");
    const state =
      st === "requires_validation" ||
      st === "invalidated" ||
      st === "confirmed" ||
      st === "accepted_for_now"
        ? st
        : "accepted_for_now";
    return {
      id: `asm_${i}`,
      statement: String(a.statement ?? ""),
      reasonRequired: String(a.reason_required ?? ""),
      supportingEvidenceIds: Array.isArray(a.linked_evidence_ids)
        ? (a.linked_evidence_ids as string[])
        : [],
      confidence: mapConfidence(String(a.confidence ?? "low")),
      validationMethod: String(a.validation_method ?? ""),
      validationStage: String(a.validation_stage ?? ""),
      effectIfFalse: String(a.impact_if_false ?? ""),
      state: state as VerdictAssumption["state"],
    };
  });

  const conditions: VerdictCondition[] = (dto.conditions || []).map((c, i) => ({
    id: String(c.id ?? `cond_${i}`),
    requiredAction: String(c.required_action ?? c.title ?? ""),
    owner: String(c.owner_role ?? ""),
    successCriterion: String(c.success_criterion ?? ""),
    evidenceRequired: String(c.evidence_required ?? true),
    deadlineOrMilestone: String(c.target_milestone ?? ""),
    consequenceIfNotMet: String(c.consequence_if_unmet ?? ""),
  }));

  const changeTriggers: VerdictChangeTrigger[] = (dto.change_triggers || []).map(
    (t, i) => ({
      id: `trg_${i}`,
      description: String(t.title ?? ""),
      currentState: String(t.current_state ?? ""),
      threshold: String(t.threshold_or_event ?? ""),
      possibleTransition: String(t.possible_transition ?? ""),
    }),
  );

  return {
    id: dto.id,
    projectId: dto.project_id,
    projectName,
    version: dto.version,
    type: TYPE_MAP[dto.verdict_type] ?? "INSUFFICIENT_DATA",
    status: mapStatus(dto.lifecycle_status),
    confidence: mapConfidence(dto.confidence_level),
    evidenceCoverageLabel: `Snapshot ${dto.evidence_snapshot_hash.slice(0, 12)}… · readiness ${dto.readiness_snapshot}`,
    preparedAt: dto.created_at,
    preparedAtLabel: new Date(dto.created_at).toLocaleString("ru-RU"),
    supersedesVerdictId: dto.supersedes_verdict_id,
    evidenceSnapshotId: dto.evidence_snapshot_id,
    oneSentenceConclusion: dto.executive_conclusion,
    executiveRationale: dto.executive_rationale,
    primaryBusinessImplication: dto.primary_business_implication,
    recommendedImmediateAction: dto.recommended_next_action,
    scorecard: [],
    supportingEvidence,
    counterEvidence,
    risks,
    assumptions,
    conditions,
    changeTriggers,
    nextStep: {
      primaryAction: dto.recommended_next_action,
      handoffLabel: dto.strategy_eligibility.strategy_eligible
        ? "Strategy eligibility: eligible (не создаёт Strategy)"
        : "Strategy blocked",
      handoffHref: "strategy",
      supportingActions: [],
      note: "Business Verdict — коммерческое решение на основе Evidence Snapshot. Не разрешение на исполнение.",
    },
    basedOnReadinessStatus: dto.readiness_snapshot,
    localMockLabel: "",
  };
}
