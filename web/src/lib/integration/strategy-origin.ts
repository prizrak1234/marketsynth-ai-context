/**
 * I5 — Strategy section / plan authority origins.
 */

export type StrategySectionOrigin =
  | "backend_marketing_plan"
  | "backend_marketing_strategy"
  | "deterministic_local"
  | "derived"
  | "mock"
  | "imported"
  | "unsupported";

export type StrategyAuthorityLabel =
  | "strategy_local_preview"
  | "strategy_backend"
  | "ops_plan_backend"
  | "unsupported"
  | "mock_demo";

export type StrategyOriginMeta = {
  origin: StrategySectionOrigin;
  authority: StrategyAuthorityLabel;
  labelRu: string;
  persistedToBackend: boolean;
  isStrategySot: boolean;
  /** MarketingPlan is never claimed as Strategy SoT */
  marketingPlanIsNotStrategy: true;
};

export function mockStrategyOrigin(): StrategyOriginMeta {
  return {
    origin: "mock",
    authority: "mock_demo",
    labelRu: "Mock · Product Alpha Strategy",
    persistedToBackend: false,
    isStrategySot: true,
    marketingPlanIsNotStrategy: true,
  };
}

export function localStrategyPreviewOrigin(): StrategyOriginMeta {
  return {
    origin: "deterministic_local",
    authority: "strategy_local_preview",
    labelRu: "Локальный стратегический preview",
    persistedToBackend: false,
    isStrategySot: true,
    marketingPlanIsNotStrategy: true,
  };
}

export function backendOpsPlanContextOrigin(): StrategyOriginMeta {
  return {
    origin: "backend_marketing_plan",
    authority: "ops_plan_backend",
    labelRu: "Backend MarketingPlan (ops spine · не Strategy)",
    persistedToBackend: true,
    isStrategySot: false,
    marketingPlanIsNotStrategy: true,
  };
}

export function unsupportedStrategyBackendOrigin(): StrategyOriginMeta {
  return {
    origin: "unsupported",
    authority: "unsupported",
    labelRu: "Backend MarketingStrategy SoT отсутствует",
    persistedToBackend: false,
    isStrategySot: false,
    marketingPlanIsNotStrategy: true,
  };
}

export function durableBackendStrategyOrigin(approved: boolean): StrategyOriginMeta {
  return {
    origin: "backend_marketing_strategy",
    authority: "strategy_backend",
    labelRu: approved
      ? "Backend · утверждённая MarketingStrategy"
      : "Backend · draft MarketingStrategy",
    persistedToBackend: true,
    isStrategySot: true,
    marketingPlanIsNotStrategy: true,
  };
}
