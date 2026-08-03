/**

 * Agency Home analysis presentation — maps UserRequest DTO → stages + verdict UI.

 * Not a substitute for Business Verdict entities; honest product framing.

 */



import type { BackendUserRequestDto } from "@/lib/api/types/user-requests";
import type { BusinessIdeaValidationOutput } from "@/lib/api/types/business-idea-validation";
import {
  confirmedEvidence,
} from "@/lib/api/types/business-idea-validation";
import {
  customerGapItems,
  isInsufficientEvidence,
} from "@/lib/biv/research-gap-presentation";



export type AgencyStageId =

  | "task"

  | "market"

  | "competitors"

  | "audience"

  | "demand"

  | "economics"

  | "risks"

  | "conclusion";



export type AgencyStageStatus = "pending" | "running" | "done";



export type AgencyStage = {

  id: AgencyStageId;

  labelKey: string;

  status: AgencyStageStatus;

};



export type AgencyVerdictTone = "go" | "conditional" | "no_go" | "insufficient_data";



export type AgencyResearchStatus =

  | "not_started"

  | "in_progress"

  | "completed"

  | "insufficient_evidence"

  | "unavailable";



export type AgencyEvidenceAssessment = {

  hasEvidence: boolean;

  sourceCount: number;

  evidenceCount: number;

  researchRunId: string | null;

  researchStatus: AgencyResearchStatus;

  blockReasonKey: string;

  researchWorking: boolean;

};



export type AgencyVerdictView = {

  tone: AgencyVerdictTone;

  titleKey: string;

  why: string;

  whyKey: string | null;

  risks: string[];

  strengths: string[];

  economics: string;

  successChance: string;

  forecast: string;

  whatToChange: string[];

  sourcesNote: string;

  rawAssistant: string;

  nextHref: string | null;

  requestId: string;

  evidence: AgencyEvidenceAssessment;

  showMetrics: boolean;

  primaryActionKey: string;

};



export const AGENCY_STAGE_ORDER: readonly AgencyStageId[] = [

  "task",

  "market",

  "competitors",

  "audience",

  "demand",

  "economics",

  "risks",

  "conclusion",

] as const;



export const AGENCY_STAGE_LABEL_KEYS: Record<AgencyStageId, string> = {

  task: "agency.stage.task",

  market: "agency.stage.market",

  competitors: "agency.stage.competitors",

  audience: "agency.stage.audience",

  demand: "agency.stage.demand",

  economics: "agency.stage.economics",

  risks: "agency.stage.risks",

  conclusion: "agency.stage.conclusion",

};



export function buildRunningStages(doneCount: number): AgencyStage[] {

  return AGENCY_STAGE_ORDER.map((id, index) => ({

    id,

    labelKey: AGENCY_STAGE_LABEL_KEYS[id],

    status:

      index < doneCount ? "done" : index === doneCount ? "running" : "pending",

  }));

}

/** Map backend BivRunProgress → agency stage UI (no local timer simulation). */
const PIPELINE_STAGE_ORDER = [
  "normalizing_input",
  "decomposing_queries",
  "searching_direct",
  "searching_indirect",
  "searching_international",
  "searching_local",
  "searching_adjacent",
  "validating_sources",
  "extracting_evidence",
  "synthesizing_findings",
  "calculating_confidence",
  "calculating_coverage",
  "generating_verdict",
  "building_report",
  "completed",
] as const;

function pipelineStageIndex(stage: string): number {
  const idx = PIPELINE_STAGE_ORDER.indexOf(stage as (typeof PIPELINE_STAGE_ORDER)[number]);
  return idx >= 0 ? idx : 0;
}

export function buildStagesFromBackendProgress(progress: {
  progress_percent: number;
  current_stage: string;
  completed_stages?: string[];
  state: string;
}): AgencyStage[] {
  const total = AGENCY_STAGE_ORDER.length;
  if (progress.state === "succeeded" || progress.current_stage === "completed") {
    return allStagesDone();
  }

  const pipelineTotal = PIPELINE_STAGE_ORDER.length;
  const completedPipeline = progress.completed_stages?.length ?? 0;
  const currentPipeline = pipelineStageIndex(progress.current_stage);
  const pipelineDone = Math.max(completedPipeline, currentPipeline);

  let doneCount = Math.min(
    total - 1,
    Math.floor((pipelineDone / Math.max(pipelineTotal - 1, 1)) * total),
  );

  if (progress.state === "queued" || progress.state === "pending") {
    doneCount = 0;
  }

  if (progress.progress_percent > 0 && doneCount === 0 && progress.state === "running") {
    doneCount = Math.min(
      total - 1,
      Math.floor((progress.progress_percent / 100) * total),
    );
  }

  return buildRunningStages(doneCount);
}



export function allStagesDone(): AgencyStage[] {

  return AGENCY_STAGE_ORDER.map((id) => ({

    id,

    labelKey: AGENCY_STAGE_LABEL_KEYS[id],

    status: "done" as const,

  }));

}



export function buildStagesFromValidationOutput(
  output: BusinessIdeaValidationOutput,
): AgencyStage[] {
  const coverage = output.category_coverage ?? [];
  if (coverage.length > 0) {
    const stageCategoryMap: Partial<Record<AgencyStageId, string[]>> = {
      market: ["market"],
      competitors: ["competitors"],
      audience: ["audience"],
      demand: ["demand"],
      economics: ["pricing"],
      risks: ["commercial_risks"],
    };
    const attemptedStatuses = new Set([
      "confirmed",
      "not_confirmed",
      "not_found",
      "found_but_irrelevant",
      "found_but_low_quality",
      "user_hypothesis",
      "conflicted",
    ]);

    return AGENCY_STAGE_ORDER.map((id) => {
      if (id === "task") {
        return { id, labelKey: AGENCY_STAGE_LABEL_KEYS[id], status: "done" as const };
      }
      if (id === "conclusion") {
        return {
          id,
          labelKey: AGENCY_STAGE_LABEL_KEYS[id],
          status: isInsufficientEvidence(output) ? ("pending" as const) : ("done" as const),
        };
      }
      const cats = stageCategoryMap[id] ?? [];
      const rows = coverage.filter((c) => cats.includes(c.category));
      if (!rows.length) {
        return { id, labelKey: AGENCY_STAGE_LABEL_KEYS[id], status: "pending" as const };
      }
      if (rows.some((r) => r.coverage_status === "confirmed")) {
        return { id, labelKey: AGENCY_STAGE_LABEL_KEYS[id], status: "done" as const };
      }
      if (rows.some((r) => attemptedStatuses.has(r.coverage_status))) {
        return { id, labelKey: AGENCY_STAGE_LABEL_KEYS[id], status: "running" as const };
      }
      return { id, labelKey: AGENCY_STAGE_LABEL_KEYS[id], status: "pending" as const };
    });
  }

  if (isInsufficientEvidence(output)) {
    return AGENCY_STAGE_ORDER.map((id, index) => ({
      id,
      labelKey: AGENCY_STAGE_LABEL_KEYS[id],
      status: index === 0 ? ("done" as const) : ("pending" as const),
    }));
  }
  const confirmed = confirmedEvidence(output.evidence);
  if (confirmed.length === 0) {
    return AGENCY_STAGE_ORDER.map((id, index) => ({
      id,
      labelKey: AGENCY_STAGE_LABEL_KEYS[id],
      status: index === 0 ? ("done" as const) : ("pending" as const),
    }));
  }
  return allStagesDone();
}

export function buildStagesFromEvidence(

  assessment: AgencyEvidenceAssessment,

): AgencyStage[] {

  if (!assessment.hasEvidence) {

    return AGENCY_STAGE_ORDER.map((id, index) => ({

      id,

      labelKey: AGENCY_STAGE_LABEL_KEYS[id],

      status: index === 0 ? ("done" as const) : ("pending" as const),

    }));

  }

  return allStagesDone();

}



function splitBullets(text: string): string[] {

  return text

    .split(/\n+/)

    .map((l) => l.replace(/^[-•*]\s*/, "").trim())

    .filter((l) => l.length > 12)

    .slice(0, 6);

}



/** Honest evidence gate — NO EVIDENCE → NO COMMERCIAL VERDICT. */

export function assessResearchEvidence(

  dto: BackendUserRequestDto,

): AgencyEvidenceAssessment {

  const research = dto.research_collection;

  const sourceCount = research?.source_candidates?.length ?? 0;

  const report = research?.retrieval_report;

  const candidateCount = report?.candidate_count ?? sourceCount;

  const researchRunId = dto.research_run_id ?? null;

  const skillIsResearch = dto.skill_code === "research.web_source_collection";

  const researchEnabledAttempt =

    skillIsResearch || Boolean(researchRunId) || Boolean(research);

  const mockProviders = Boolean(research?.provider_coverage?.mock_providers);



  let researchStatus: AgencyResearchStatus = "not_started";

  if (dto.status === "failed" || dto.status === "cancelled") {

    researchStatus = "unavailable";

  } else if (researchRunId && sourceCount > 0) {

    researchStatus = "completed";

  } else if (researchRunId || dto.status === "in_progress") {

    researchStatus = "in_progress";

  } else if (!researchEnabledAttempt) {

    researchStatus = "not_started";

  } else if (researchEnabledAttempt && sourceCount === 0) {

    researchStatus = "in_progress";

  }



  const evidenceCount = candidateCount;

  const hasEvidence = sourceCount > 0 && evidenceCount > 0;



  let blockReasonKey = "agency.research.block.notExecuted";

  if (!skillIsResearch && !researchRunId && !research) {

    blockReasonKey = "agency.research.block.notConnected";

  } else if (mockProviders && !hasEvidence) {

    blockReasonKey = "agency.research.block.mockOnly";

  } else if (

    dto.status === "needs_clarification" ||

    (dto.missing_inputs && dto.missing_inputs.length > 0)

  ) {

    blockReasonKey = "agency.research.block.insufficientInput";

  } else if (sourceCount === 0) {

    blockReasonKey = "agency.research.block.noSources";

  } else if (dto.status === "failed") {

    blockReasonKey = "agency.research.block.unavailable";

  }



  const researchWorking =

    hasEvidence &&

    Boolean(researchRunId) &&

    skillIsResearch &&

    !mockProviders;



  return {

    hasEvidence,

    sourceCount,

    evidenceCount,

    researchRunId,

    researchStatus,

    blockReasonKey,

    researchWorking,

  };

}



/** Map backend UserRequest → agency Verdict card (product presentation). */

export function mapDtoToAgencyVerdict(dto: BackendUserRequestDto): AgencyVerdictView {

  const msg = (dto.assistant_message || "").trim();

  const clarify = (dto.clarification_question || "").trim();

  const research = dto.research_collection;

  const evidence = assessResearchEvidence(dto);



  if (!evidence.hasEvidence) {

    return {

      tone: "insufficient_data",

      titleKey: "agency.verdict.insufficientData",

      whyKey: "agency.verdict.insufficientWhy",

      why: "",

      risks: [],

      strengths: [],

      economics: "",

      successChance: "",

      forecast: "",

      whatToChange: clarify ? [clarify] : [],

      sourcesNote: "agency.verdict.sourcesMissing",

      rawAssistant: [msg, clarify].filter(Boolean).join("\n\n"),

      nextHref: null,

      requestId: dto.id,

      evidence,

      showMetrics: false,

      primaryActionKey: "agency.action.startResearch",

    };

  }



  const bullets = splitBullets(msg);

  let tone: AgencyVerdictTone = "go";

  let titleKey = "agency.verdict.go";



  if (dto.status === "failed" || dto.status === "cancelled") {

    tone = "no_go";

    titleKey = "agency.verdict.noGo";

  } else if (

    dto.status === "needs_clarification" ||

    Boolean(clarify) ||

    (dto.missing_inputs && dto.missing_inputs.length > 0)

  ) {

    tone = "conditional";

    titleKey = "agency.verdict.conditional";

  } else if (

    research &&

    ((research.contradictions && research.contradictions.length > 0) ||

      (research.missing_data && research.missing_data.length > 0))

  ) {

    tone = "conditional";

    titleKey = "agency.verdict.conditional";

  }



  const sourcesCount = research?.source_candidates?.length ?? 0;

  const sourcesNote =

    sourcesCount > 0

      ? "agency.verdict.sourcesFound"

      : "agency.verdict.sourcesPipeline";



  return {

    tone,

    titleKey,

    whyKey: null,

    why: msg || clarify || "—",

    risks:

      tone === "no_go"

        ? bullets.slice(0, 3)

        : bullets.filter((b) => /риск|risk|угроз|weak/i.test(b)).slice(0, 3),

    strengths: bullets.filter((b) => /сильн|преимущ|strong|opportun/i.test(b)).slice(0, 3),

    economics:

      bullets.find((b) => /экономик|unit.?econ|марж|budget|бюджет|CAC|LTV/i.test(b)) ||

      msg.slice(0, 280),

    successChance:

      tone === "go"

        ? "agency.verdict.chanceHigh"

        : tone === "conditional"

          ? "agency.verdict.chanceMid"

          : "agency.verdict.chanceLow",

    forecast: msg.slice(0, 400) || clarify,

    whatToChange: clarify

      ? [clarify]

      : bullets.filter((b) => /нужно|следует|recommend|доработ|измени/i.test(b)).slice(0, 4),

    sourcesNote,

    rawAssistant: [msg, clarify].filter(Boolean).join("\n\n"),

    nextHref: null,

    requestId: dto.id,

    evidence,

    showMetrics: true,

    primaryActionKey: "agency.action.continue",

  };

}



export type AgencyNextStepId =

  | "marketing_strategy"

  | "prepare_content"

  | "content_plan"

  | "ads"

  | "website"

  | "telegram_bot"

  | "youtube"

  | "refine_idea";



export type AgencyNextStep = {

  id: AgencyNextStepId;

  labelKey: string;

  scenario: string | null;

  href: string | null;

};



export const AGENCY_NEXT_STEPS: readonly AgencyNextStep[] = [

  {

    id: "marketing_strategy",

    labelKey: "agency.next.strategy",

    scenario: "marketing_strategy",

    href: null,

  },

  {

    id: "prepare_content",

    labelKey: "agency.next.prepareContent",

    scenario: "content_plan",

    href: null,

  },

  {

    id: "content_plan",

    labelKey: "agency.next.contentPlan",

    scenario: "content_plan",

    href: null,

  },

  {

    id: "ads",

    labelKey: "agency.next.ads",

    scenario: "social_media",

    href: null,

  },

  {

    id: "website",

    labelKey: "agency.next.website",

    scenario: "website",

    href: null,

  },

  {

    id: "telegram_bot",

    labelKey: "agency.next.telegramBot",

    scenario: "telegram_bot",

    href: null,

  },

  {

    id: "youtube",

    labelKey: "agency.next.youtube",

    scenario: "youtube",

    href: null,

  },

  {

    id: "refine_idea",

    labelKey: "agency.next.refine",

    scenario: "idea_validation",

    href: null,

  },

] as const;



/** Commercial Home must never redirect entrepreneurs to Investigation Workspace. */

export function isInvestigationWorkspaceHref(href: string | null | undefined): boolean {

  if (!href) return false;

  return (

    href.includes("/investigation") ||

    href.includes("/projects/new") ||

    href.includes("scenario=idea_validation") ||

    href.includes("scenario=market_research") ||

    href.includes("scenario=competitor_analysis") ||

    href.includes("scenario=marketing_strategy")

  );

}

/** Map CMVP.1 validation output → agency verdict presentation. */
export function mapValidationToAgencyVerdict(
  dto: BackendUserRequestDto,
  output: BusinessIdeaValidationOutput,
): AgencyVerdictView {
  const confirmed = confirmedEvidence(output.evidence);
  const insufficient = isInsufficientEvidence(output);
  const hasEvidence = confirmed.length >= 1 && !insufficient;
  const gapItems = customerGapItems(output);
  const evidence: AgencyEvidenceAssessment = {
    hasEvidence,
    sourceCount: output.sources.length,
    evidenceCount: confirmed.length,
    researchRunId: output.run_id ?? null,
    researchStatus: insufficient
      ? "insufficient_evidence"
      : output.research_terminal_state === "succeeded_complete" ||
          output.research_terminal_state === "succeeded_insufficient"
        ? "completed"
        : output.research_terminal_state === "running"
          ? "in_progress"
          : hasEvidence
            ? "completed"
            : "in_progress",
    blockReasonKey: insufficient
      ? "agency.research.block.noSources"
      : hasEvidence
        ? ""
        : "agency.research.block.noSources",
    researchWorking: Boolean(output.run_id) && hasEvidence,
  };

  const toneMap: Record<string, AgencyVerdictTone> = {
    proceed: "go",
    proceed_with_conditions: "conditional",
    revise: "conditional",
    reject: "no_go",
    insufficient_evidence: "insufficient_data",
  };
  const titleMap: Record<string, string> = {
    proceed: "agency.biv.verdict.proceed",
    proceed_with_conditions: "agency.biv.verdict.proceedWithConditions",
    revise: "agency.biv.verdict.revise",
    reject: "agency.biv.verdict.reject",
    insufficient_evidence: "agency.biv.verdict.insufficientEvidence",
  };

  const tone = toneMap[output.verdict] ?? "insufficient_data";
  const titleKey = titleMap[output.verdict] ?? "agency.biv.verdict.insufficientEvidence";

  const gapMessages = gapItems.map((g) => g.customer_message);
  const gapActions = gapItems
    .map((g) => g.recommended_action)
    .filter((a): a is string => Boolean(a?.trim()));

  return {
    tone,
    titleKey,
    whyKey: insufficient ? "agency.biv.insufficientWhy" : "agency.verdict.why",
    why: insufficient
      ? gapMessages[0] ?? ""
      : output.customer_report?.executive_summary.status_line ??
        output.findings.map((f) => f.statement).slice(0, 3).join("\n"),
    risks: insufficient ? [] : output.risks.map((r) => r.title),
    strengths: insufficient ? [] : output.opportunities.map((o) => o.title),
    economics: "",
    successChance: insufficient
      ? "agency.verdict.chanceLow"
      : output.confidence.total_score >= 70
        ? "agency.verdict.chanceHigh"
        : output.confidence.total_score >= 45
          ? "agency.verdict.chanceMid"
          : "agency.verdict.chanceLow",
    forecast: "",
    whatToChange: insufficient ? [...gapMessages, ...gapActions] : gapMessages,
    sourcesNote: hasEvidence ? "agency.verdict.sourcesFound" : "agency.verdict.sourcesMissing",
    rawAssistant:
      output.customer_report?.structured_verdict.recommendation ??
      output.customer_report?.executive_summary.status_line ??
      "",
    nextHref: null,
    requestId: dto.id,
    evidence,
    showMetrics: false,
    primaryActionKey: insufficient
      ? "agency.action.refineInputs"
      : hasEvidence
        ? "agency.action.continue"
        : "agency.action.startResearch",
  };
}

