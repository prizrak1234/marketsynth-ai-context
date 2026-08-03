/**
 * P1.2 — lineage labels for MarketingPlan created via handoff.
 */

export type MarketingPlanLineageView = {
  sourceImplementationPlanId: string | null;
  sourceImplementationPlanVersion: number | null;
  sourceMarketingStrategyId: string | null;
  sourceBusinessVerdictId: string | null;
  handoffId: string | null;
  mappingVersion: string | null;
  mappingFingerprint: string | null;
  labelRu: string;
};

export function mapMarketingPlanLineageFromContext(
  projectContext: Record<string, unknown> | null | undefined,
): MarketingPlanLineageView {
  const ctx = projectContext || {};
  const handoffId = typeof ctx.handoff_id === "string" ? ctx.handoff_id : null;
  return {
    sourceImplementationPlanId:
      typeof ctx.source_implementation_plan_id === "string"
        ? ctx.source_implementation_plan_id
        : null,
    sourceImplementationPlanVersion:
      typeof ctx.source_implementation_plan_version === "number"
        ? ctx.source_implementation_plan_version
        : null,
    sourceMarketingStrategyId:
      typeof ctx.source_marketing_strategy_id === "string"
        ? ctx.source_marketing_strategy_id
        : null,
    sourceBusinessVerdictId:
      typeof ctx.source_business_verdict_id === "string"
        ? ctx.source_business_verdict_id
        : null,
    handoffId,
    mappingVersion:
      typeof ctx.mapping_version === "string" ? ctx.mapping_version : null,
    mappingFingerprint:
      typeof ctx.mapping_fingerprint === "string" ? ctx.mapping_fingerprint : null,
    labelRu: handoffId
      ? `Lineage: handoff ${handoffId.slice(0, 8)}… · draft only`
      : "Lineage: not from ImplementationPlan handoff",
  };
}
