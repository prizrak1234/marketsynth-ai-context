/** RUNTIME-01D — derive customer-safe partial research panel sections from persisted output. */

import type {
  BivEvidenceItem,
  BivFindingItem,
  BivRemediationQuestion,
  BusinessIdeaValidationOutput,
} from "@/lib/api/types/business-idea-validation";
import { isPartialResearchOutput } from "@/lib/api/types/business-idea-validation";

import { customerGapItems } from "./research-gap-presentation";
import { resolvePartialStopReasonText } from "./partial-research-stop-reason";

export type PartialResearchFindingView = {
  id: string;
  title: string;
  summary: string | null;
  category: string | null;
  confidencePercent: number | null;
  linkedEvidenceCount: number;
};

export type PartialResearchEvidenceView = {
  id: string;
  title: string;
  url: string | null;
  excerpt: string | null;
  claim: string | null;
  accepted: boolean;
};

export type PartialResearchPanelViewModel = {
  stopReasonText: string;
  interimConclusion: string | null;
  establishedFindings: string[];
  probableSignals: string[];
  limitations: string[];
  nextSteps: Array<{ id: string; label: string }>;
  findings: PartialResearchFindingView[];
  evidence: PartialResearchEvidenceView[];
  gaps: Array<{ code: string; message: string; action?: string | null }>;
  remediationQuestions: BivRemediationQuestion[];
  hasFindingsSection: boolean;
  hasEvidenceSection: boolean;
  hasGapsSection: boolean;
  hasRemediationSection: boolean;
  hasNextStepsSection: boolean;
  hasLimitationsSection: boolean;
};

function mapFinding(
  item: BivFindingItem,
  evidenceById: Map<string, BivEvidenceItem>,
): PartialResearchFindingView | null {
  const title = (item.claim || item.interpretation || "").trim();
  if (!title) return null;
  const linkedAccepted = item.evidence_ids.filter((id) => evidenceById.get(id)?.accepted).length;
  const confidence =
    typeof item.confidence === "number" && Number.isFinite(item.confidence)
      ? Math.round(Math.min(100, Math.max(0, item.confidence * (item.confidence <= 1 ? 100 : 1))))
      : null;
  return {
    id: item.finding_id,
    title,
    summary: item.interpretation?.trim() || item.business_impact?.trim() || null,
    category: item.category?.trim() || null,
    confidencePercent: confidence,
    linkedEvidenceCount: linkedAccepted,
  };
}

function mapEvidence(item: BivEvidenceItem): PartialResearchEvidenceView | null {
  const title = (item.source_title || item.claim_supported || "").trim();
  if (!title && !item.source_url?.trim()) return null;
  return {
    id: item.evidence_id,
    title: title || item.source_url,
    url: item.source_url?.trim() || null,
    excerpt: item.excerpt?.trim() || null,
    claim: item.claim_supported?.trim() || null,
    accepted: item.accepted,
  };
}

function safeUrl(url: string | null): string | null {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    if (parsed.protocol === "http:" || parsed.protocol === "https:") {
      return parsed.toString();
    }
  } catch {
    return null;
  }
  return null;
}

export function buildPartialResearchPanelViewModel(
  output: BusinessIdeaValidationOutput,
  translate: (key: string) => string,
): PartialResearchPanelViewModel | null {
  if (!isPartialResearchOutput(output)) return null;

  const evidenceItems = output.evidence_items ?? [];
  const evidenceById = new Map(evidenceItems.map((item) => [item.evidence_id, item]));

  const findings = (output.finding_items ?? [])
    .map((item) => mapFinding(item, evidenceById))
    .filter((item): item is PartialResearchFindingView => item !== null);

  const acceptedEvidence = evidenceItems
    .filter((item) => item.accepted)
    .map(mapEvidence)
    .filter((item): item is PartialResearchEvidenceView => item !== null)
    .map((item) => ({ ...item, url: safeUrl(item.url) }));

  const gaps = customerGapItems(output).map((gap) => ({
    code: gap.code,
    message: gap.customer_message?.trim() || translate("agency.biv.gap.unknown"),
    action: gap.recommended_action?.trim() || null,
  }));

  const remediationQuestions = (output.remediation_questions ?? []).filter(
    (item) => (item.question ?? "").trim().length > 0,
  );

  const stopReasonText = resolvePartialStopReasonText({
    partialFailureCode: output.partial_failure_code,
    researchStopReasonMessage: output.research_stop_reason?.customer_message,
    partialSafeMessage: output.partial_safe_message,
    translate,
  });

  const partialReport = output.partial_report;
  const establishedFindings = (partialReport?.established_findings ?? []).filter(Boolean);
  const probableSignals = (partialReport?.probable_signals ?? []).filter(Boolean);
  const interimConclusion = partialReport?.interim_conclusion?.trim() || null;
  const limitations = (output.limitations ?? []).filter((item) => item.trim().length > 0);
  const nextSteps = (output.next_steps ?? [])
    .filter((step) => (step.label ?? "").trim().length > 0)
    .map((step) => ({ id: step.id, label: step.label.trim() }));

  return {
    stopReasonText,
    interimConclusion,
    establishedFindings,
    probableSignals,
    limitations,
    nextSteps,
    findings,
    evidence: acceptedEvidence,
    gaps,
    remediationQuestions,
    hasFindingsSection: findings.length > 0 || establishedFindings.length > 0,
    hasEvidenceSection: acceptedEvidence.length > 0,
    hasGapsSection: gaps.length > 0,
    hasRemediationSection: remediationQuestions.length > 0,
    hasNextStepsSection: nextSteps.length > 0,
    hasLimitationsSection: limitations.length > 0,
  };
}
