/**
 * P0.2 Investigation domain selfcheck.
 * Run: npx --yes tsx src/lib/integration/investigation-p0-2.selfcheck.ts
 */

import {
  createTriggersAgentRun,
  createTriggersLlm,
  mapLifecycleToViewStatus,
  mapInvestigationDtoToLifecycleView,
  pageLoadCreatesInvestigation,
} from "@/lib/integration/investigation-api-adapter";
import { normalizeInvestigationDomainError } from "@/lib/integration/investigation-domain-errors";
import { reconcileInvestigationLifecycle } from "@/lib/integration/investigation-reconciliation";
import type { InvestigationDto } from "@/lib/api/types/investigations";
import { ApiError } from "@/lib/api/errors";

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}

{
  assert(pageLoadCreatesInvestigation() === false, "no page-load create");
  assert(createTriggersAgentRun() === false, "no agent run");
  assert(createTriggersLlm() === false, "no llm");
}

{
  const dto: InvestigationDto = {
    id: "inv-1",
    owner_id: "o",
    project_id: "p",
    project_brief_id: "b",
    project_brief_version: 1,
    input_fingerprint: "abc",
    version: 1,
    status: "draft",
    current_stage: "project_context",
    stages: [
      { stage_id: "project_context", status: "not_started" },
      { stage_id: "market_research", status: "not_started" },
    ],
    readiness_status: "not_ready",
    readiness_reasons: ["source_coverage_pending_p0_3"],
    started_at: null,
    completed_at: null,
    blocked_reason: null,
    supersedes_investigation_id: null,
    metadata: { source_evidence: "unavailable_until_p0_3_p0_4" },
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
  const view = mapInvestigationDtoToLifecycleView(dto);
  assert(view.origin === "backend", "origin");
  assert(view.autoResearchConnected === false, "no auto research");
  assert(view.sourceDomain === "unavailable_until_p0_3", "source gap");
  assert(view.evidenceDomain === "unavailable_until_p0_4", "evidence gap");
  assert(mapLifecycleToViewStatus("active") === "researching", "status map");
  assert(view.notice.includes("не подключён"), "notice copy");
}

{
  const err = normalizeInvestigationDomainError(
    new ApiError("conflict", 409, { safe_message: "brief_not_submitted" }),
  );
  assert(err.kind === "brief_not_submitted", "brief_not_submitted kind");
}

{
  const r = reconcileInvestigationLifecycle({
    local: null,
    backend: null,
  });
  assert(r.backendWinsLifecycle === true, "backend wins");
  assert(r.localArtifactsSeparate === true, "artifacts separate");
}

console.log("investigation-p0-2.selfcheck: OK");
