/**
 * Integration I4 selfcheck — decision semantics + verdict ≠ approval/readiness.
 * Run: npx --yes tsx src/lib/integration/verdict.selfcheck.ts
 */

import { ApiError } from "@/lib/api/errors";
import {
  assertNeverUniversalDecision,
  categoryAuthorizesExecution,
  categoryIsBusinessVerdict,
  DECISION_SEMANTICS_MATRIX,
} from "@/lib/integration/decision-semantics";
import {
  readinessImpliesVerdictType,
  resolveStrategyEligibility,
  verdictApprovalCreatesExecutionApproval,
} from "@/lib/integration/strategy-eligibility";
import {
  canAutoUploadLocalVerdictToBackend,
  localVerdictReconciliationPolicy,
} from "@/lib/integration/verdict-adapter";
import {
  normalizeVerdictError,
  unsupportedVerdictCapability,
} from "@/lib/integration/verdict-errors";
import {
  deterministicLocalPreviewOrigin,
  durableBackendVerdictOrigin,
  mockVerdictOrigin,
  unsupportedBackendVerdictOrigin,
} from "@/lib/integration/verdict-origin";
import { DOMAIN_MAPPINGS } from "@/lib/integration/domain-mapping";

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}

{
  for (const row of DECISION_SEMANTICS_MATRIX) {
    assert(assertNeverUniversalDecision(row.category), `no universal: ${row.object}`);
  }
  const verdictRows = DECISION_SEMANTICS_MATRIX.filter((r) =>
    categoryIsBusinessVerdict(r.category),
  );
  assert(verdictRows.length >= 1, "has business verdict category");
  const cc = DECISION_SEMANTICS_MATRIX.find((r) =>
    r.object.includes("ControlCenter.next_action"),
  );
  assert(cc?.category === "control_center_next_action", "CC category");
  assert(cc?.businessVerdictRelation === "conflict_if_confused", "CC conflict if confused");
  const sup = DECISION_SEMANTICS_MATRIX.find((r) =>
    r.object.includes("CampaignSupervisorFinding"),
  );
  assert(sup?.businessVerdictRelation === "input_signal", "supervisor is input signal");
  assert(!categoryAuthorizesExecution("business_viability_verdict"), "verdict ≠ exec");
  assert(categoryAuthorizesExecution("execution_approval_decision"), "exec authorizes");
}

{
  assert(readinessImpliesVerdictType("ready_for_review") === null, "ready≠GO");
  assert(readinessImpliesVerdictType("conditionally_ready") === null, "cond_ready≠CONDITIONAL_GO");
  assert(readinessImpliesVerdictType("not_ready") === null, "not_ready≠INSUFFICIENT");
}

{
  const draft = resolveStrategyEligibility({
    verdictType: "GO",
    verdictStatus: "draft",
    origin: deterministicLocalPreviewOrigin(),
  });
  assert(draft.allow === false && draft.mode === "preview_only", "draft blocks strategy");

  const go = resolveStrategyEligibility({
    verdictType: "GO",
    verdictStatus: "approved",
    origin: mockVerdictOrigin(),
  });
  assert(go.allow === true && go.mode === "go", "approved GO allows");
  assert(go.createsExecutionApproval === false, "no exec approval");
  assert(go.generatesStrategyBackend === false, "no strategy backend");

  const cond = resolveStrategyEligibility({
    verdictType: "CONDITIONAL_GO",
    verdictStatus: "approved",
    origin: deterministicLocalPreviewOrigin(),
  });
  assert(cond.allow === true && cond.requiresVisibleConditions === true, "conditions visible");

  const noGo = resolveStrategyEligibility({
    verdictType: "NO_GO",
    verdictStatus: "approved",
    origin: mockVerdictOrigin(),
  });
  assert(noGo.allow === false && noGo.redirect === "pivot", "NO_GO → pivot");

  const insuf = resolveStrategyEligibility({
    verdictType: "INSUFFICIENT_DATA",
    verdictStatus: "approved",
    origin: mockVerdictOrigin(),
  });
  assert(insuf.redirect === "investigation", "INSUFFICIENT → investigation");
}

{
  assert(verdictApprovalCreatesExecutionApproval() === false, "firewall");
  assert(canAutoUploadLocalVerdictToBackend() === false, "no auto upload");
  assert(localVerdictReconciliationPolicy().autoUpload === false, "policy");
  assert(localVerdictReconciliationPolicy().deleteLocalInI4 === false, "keep local");
  const local = deterministicLocalPreviewOrigin();
  assert(local.evidenceVerified === false, "preview not evidence-verified");
  assert(local.persistedToBackend === false, "not persisted");
  assert(unsupportedBackendVerdictOrigin().authority === "unsupported", "legacy unsupported origin");
  assert(durableBackendVerdictOrigin(true).authority === "backend_approved", "durable approved");
  assert(durableBackendVerdictOrigin(true).evidenceVerified === true, "durable evidence basis");
  assert(unsupportedVerdictCapability().kind === "unsupported_capability", "error kind");
  assert(
    normalizeVerdictError(new ApiError("x", 404, null)).kind === "verdict_not_found" ||
      normalizeVerdictError(new ApiError("x", 404, null)).kind === "verdict_not_found",
    "404",
  );
}

{
  const bv = DOMAIN_MAPPINGS.find((d) => d.model === "BusinessVerdict");
  assert(bv?.classification === "A_backend_sot", "P0.5 backend SoT mapping");
  assert(Boolean(bv?.notes.includes("P0.5")), "notes P0.5");
}

console.log("verdict.selfcheck.ts: OK");
