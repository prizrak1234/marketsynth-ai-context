/**
 * Integration I3 selfcheck — semantic firewall + stage/source/status projections.
 * Run: npx --yes tsx src/lib/integration/investigation.selfcheck.ts
 */

import { ApiError } from "@/lib/api/errors";
import type { CampaignSupervisorReport } from "@/lib/api/types/business-campaigns";
import type { MarketingSkillRun } from "@/lib/api/types/marketing-skills";
import {
  AGENT_RUN_INCLUSION_RULES,
} from "@/lib/integration/investigation-adapter";
import {
  mapSupervisorReportToQualitySignals,
  qualitySignalsAreNotEvidence,
} from "@/lib/integration/evidence-adapter";
import {
  normalizeInvestigationError,
  partialIntegrationNotice,
} from "@/lib/integration/investigation-errors";
import {
  mapCampaignHealthToViewStatus,
  mockOnlyViewStatus,
} from "@/lib/integration/investigation-status-adapter";
import {
  INVESTIGATION_RELATED_SKILL_TYPES,
  isInvestigationRelatedSkillRun,
  mapSkillRunsToResearchArtifacts,
  mapSkillTypeToStageHint,
} from "@/lib/integration/source-adapter";
import { DOMAIN_MAPPINGS } from "@/lib/integration/domain-mapping";
import { buildPartialIntegrationWorkspace } from "@/lib/investigation/partial-integration-workspace";
import { evaluateVerdictReadiness } from "@/lib/investigation/verdict-readiness";

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}

{
  assert(qualitySignalsAreNotEvidence() === true, "firewall constant");
  const report: CampaignSupervisorReport = {
    campaign_id: "c1",
    health_score: 40,
    findings: [
      {
        severity: "critical",
        category: "brief",
        title: "Missing audience",
        description: "Brief incomplete",
        safe_metadata: {},
      },
    ],
    missing_inputs: ["audience"],
    contradictions: ["offer vs budget"],
    risks: ["weak demand signal"],
    recommended_next_actions: [],
  };
  const signals = mapSupervisorReportToQualitySignals(report);
  assert(signals.length >= 4, "quality signals mapped");
  assert(
    signals.every((s) => s.role !== ("evidence" as string)),
    "no evidence role",
  );
  assert(
    signals.every((s) => s.disclaimer.toLowerCase().includes("не") || s.disclaimer.includes("not") || s.disclaimer.includes("Не")),
    "disclaimer present",
  );
  // Explicit: do not build EvidenceItem
  assert(!("supportingSourceIds" in signals[0]!), "not EvidenceItem shape");
}

{
  const offerRun: MarketingSkillRun = {
    id: "r-offer",
    owner_id: "o",
    project_id: "p",
    skill_type: "offer_packaging",
    status: "succeeded",
    input_payload: {},
    used_tool_call_ids: [],
    safe_metadata: {},
    created_at: "2026-01-01T00:00:00Z",
  };
  const segRun: MarketingSkillRun = {
    ...offerRun,
    id: "r-seg",
    skill_type: "segment_research",
  };
  assert(!isInvestigationRelatedSkillRun(offerRun), "exclude offer_packaging");
  assert(isInvestigationRelatedSkillRun(segRun), "include segment_research");
  const arts = mapSkillRunsToResearchArtifacts([offerRun, segRun]);
  assert(arts.length === 1, "only related skills");
  assert(arts[0]!.role === "research_artifact_candidate", "candidate role");
  assert(arts[0]!.disclaimer.includes("not InvestigationSource") || arts[0]!.disclaimer.includes("Evidence"), "not source claim");
  assert(mapSkillTypeToStageHint("wordstat_research") === "demand_signals", "stage hint");
  assert(INVESTIGATION_RELATED_SKILL_TYPES.includes("metrica_analysis"), "metrica allowed");
}

{
  const blocked = mapCampaignHealthToViewStatus("blocked");
  assert(blocked.viewStatus === "blocked", "blocked health");
  assert(blocked.origin === "derived", "derived not invented lifecycle");
  assert(mockOnlyViewStatus().origin === "mock", "mock origin");
}

{
  assert(normalizeInvestigationError(new ApiError("x", 401, null)).kind === "unauthorized", "401");
  assert(normalizeInvestigationError(new ApiError("x", 404, null)).kind === "project_not_found", "404");
  assert(partialIntegrationNotice().kind === "partial_integration", "partial");
  assert(AGENT_RUN_INCLUSION_RULES.exclude.some((e) => e.includes("LLM")), "exclude LLM");
}

{
  const shell = buildPartialIntegrationWorkspace({
    projectId: "11111111-1111-1111-1111-111111111111",
    projectName: "Real Project",
    stages: [
      {
        id: "project_context",
        label: "Project Context",
        order: 1,
        state: "completed",
      },
      {
        id: "evidence_review",
        label: "Evidence Review",
        order: 8,
        state: "blocked",
      },
    ],
  });
  assert(shell.evidence.length === 0, "backend shell has no mock evidence");
  assert(shell.sources.length === 0, "backend shell has no mock sources");
  assert(shell.verdictReadiness?.notABusinessVerdict === true, "not a verdict");
  const ready = evaluateVerdictReadiness({
    evidence: shell.evidence,
    missingData: shell.missingData,
    contradictions: shell.contradictions,
  });
  assert(ready.status === "not_ready", "empty evidence => not_ready");
  assert(ready.notABusinessVerdict === true, "readiness ≠ business verdict");
}

{
  const inv = DOMAIN_MAPPINGS.find((d) => d.model === "InvestigationWorkspace");
  assert(inv?.classification === "B_partial_adapter", "I3 classification");
  assert(
    Boolean(inv?.notes.toLowerCase().includes("evidence")),
    "notes mention evidence firewall",
  );
}

console.log("investigation.selfcheck.ts: OK");
