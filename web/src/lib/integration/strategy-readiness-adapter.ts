/** P0.6 — Strategy readiness view (≠ MarketingPlan readiness). */

import type { BackendMarketingStrategyDto } from "@/lib/api/types/marketing-strategies";

export type StrategyReadinessView = {
  status: string;
  isMarketingPlanReadiness: false;
  isExecutionReadiness: false;
  handoffStatus: string;
  note: string;
};

export function mapStrategyReadiness(
  dto: BackendMarketingStrategyDto,
): StrategyReadinessView {
  return {
    status: dto.readiness_status,
    isMarketingPlanReadiness: false,
    isExecutionReadiness: false,
    handoffStatus: dto.handoff_status,
    note: "Strategy readiness ≠ MarketingPlan readiness ≠ execution readiness.",
  };
}
