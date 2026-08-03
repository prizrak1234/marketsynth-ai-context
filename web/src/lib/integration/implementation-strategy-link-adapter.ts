/**
 * P1.1 — Strategy linkage labels for ImplementationPlan workspace.
 */

export function strategyLineageNotice(args: {
  strategyId: string | null;
  strategyVersion: number | null;
  verdictId: string | null;
}): string {
  if (!args.strategyId || !args.strategyVersion) {
    return "ImplementationPlan требует exact approved MarketingStrategy version.";
  }
  return `Linked Strategy ${args.strategyId} v${args.strategyVersion}${
    args.verdictId ? ` · Verdict ${args.verdictId}` : ""
  }`;
}

export function strategyEligibilityRequired(): true {
  return true;
}
