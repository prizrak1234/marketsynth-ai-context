/**
 * I6 — Implementation Plan section origins.
 */

export type ImplementationPlanOrigin =
  | "deterministic_local"
  | "mock"
  | "backend_marketing_plan"
  | "derived"
  | "unsupported";

export type ImplementationPlanOriginMeta = {
  origin: ImplementationPlanOrigin;
  labelRu: string;
  isImplementationSot: boolean;
  marketingPlanIsNotImplementationPlan: true;
};

export function mockImplementationOrigin(): ImplementationPlanOriginMeta {
  return {
    origin: "mock",
    labelRu: "Mock · Product Alpha Implementation Plan",
    isImplementationSot: true,
    marketingPlanIsNotImplementationPlan: true,
  };
}

export function localImplementationOrigin(): ImplementationPlanOriginMeta {
  return {
    origin: "deterministic_local",
    labelRu: "Локальный Implementation Plan preview",
    isImplementationSot: true,
    marketingPlanIsNotImplementationPlan: true,
  };
}

export function unsupportedImplementationBackendOrigin(): ImplementationPlanOriginMeta {
  return {
    origin: "unsupported",
    labelRu: "Backend ImplementationPlan недоступен / empty",
    isImplementationSot: false,
    marketingPlanIsNotImplementationPlan: true,
  };
}

export function durableBackendImplementationOrigin(
  hasPlan: boolean,
): ImplementationPlanOriginMeta {
  return {
    origin: hasPlan ? "derived" : "unsupported",
    labelRu: hasPlan
      ? "Backend ImplementationPlan (durable SoT · ≠ MarketingPlan)"
      : "Backend ImplementationPlan: empty — без mock fallback",
    isImplementationSot: hasPlan,
    marketingPlanIsNotImplementationPlan: true,
  };
}

export function opsPlanContextOrigin(): ImplementationPlanOriginMeta {
  return {
    origin: "backend_marketing_plan",
    labelRu: "Backend MarketingPlan (ops spine · не Implementation Plan)",
    isImplementationSot: false,
    marketingPlanIsNotImplementationPlan: true,
  };
}
