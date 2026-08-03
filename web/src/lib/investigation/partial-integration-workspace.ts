/**
 * Skeleton Investigation workspace for backend/hybrid integration shell.
 * Empty evidence/source arrays — never invent confirmed research facts.
 */

import { evaluateVerdictReadiness } from "@/lib/investigation/verdict-readiness";
import type {
  InvestigationStage,
  InvestigationWorkspace,
} from "@/lib/investigation/types";

export function buildPartialIntegrationWorkspace(input: {
  projectId: string;
  projectName: string;
  stages: InvestigationStage[];
  intakeReadinessLabel?: string;
}): InvestigationWorkspace {
  const evidence: InvestigationWorkspace["evidence"] = [];
  const missingData: InvestigationWorkspace["missingData"] = [];
  const contradictions: InvestigationWorkspace["contradictions"] = [];
  const verdictReadiness = evaluateVerdictReadiness({
    evidence,
    missingData,
    contradictions,
  });

  return {
    projectId: input.projectId,
    scenarioId: "not_ready",
    projectName: input.projectName,
    projectStageLabel: "Partial integration (I3)",
    intakeReadinessLabel: input.intakeReadinessLabel ?? "local draft / project core",
    status: "collecting_context",
    lastUpdateLabel: "Backend projection · no Investigation aggregate",
    brief: {
      idea: input.projectName,
      product: "—",
      geography: "—",
      audienceHypotheses: [],
      budgetState: "unknown",
      keyConstraints: "Full intake may remain local (I2)",
      assumptions: [
        "Investigation Evidence domain отсутствует на backend",
        "Campaign Supervisor signals ≠ confirmed evidence",
      ],
    },
    stages: input.stages,
    sources: [],
    evidence,
    findings: [],
    missingData,
    risks: [],
    opportunities: [],
    contradictions,
    specialists: [],
    assumptionsAcknowledged: false,
    verdictReadiness,
    updatedAt: new Date().toISOString(),
  };
}
