/** Cross-project MarketingStrategy index. */

import { fetchProjects } from "@/lib/api/endpoints/projects";
import { fetchMarketingStrategies } from "@/lib/api/endpoints/marketing-strategies";
import type { BackendMarketingStrategyDto } from "@/lib/api/types/marketing-strategies";
import { getIntegrationMode } from "@/lib/integration/mode";

export type StrategyIndexItem = {
  id: string;
  projectId: string;
  projectName: string;
  verdictType: string;
  verdictVersion: number;
  strategyVersion: number;
  lifecycleStatus: string;
  readiness: string;
  origin: string;
  blockersCount: number;
  updatedAt: string | null;
  href: string;
};

export type StrategyIndexResult = {
  state: "success" | "empty" | "error" | "unauthorized" | "mock_notice";
  items: StrategyIndexItem[];
  message: string | null;
};

function mapItem(
  projectId: string,
  projectName: string,
  s: BackendMarketingStrategyDto,
): StrategyIndexItem {
  return {
    id: s.id,
    projectId,
    projectName,
    verdictType: s.business_verdict_type,
    verdictVersion: s.business_verdict_version,
    strategyVersion: s.version,
    lifecycleStatus: s.lifecycle_status,
    readiness: s.readiness_status,
    origin: s.strategy_origin,
    blockersCount: (s.verdict_conditions?.length || 0) + (s.strategic_risks?.length || 0),
    updatedAt: s.updated_at ?? null,
    href: `/workspace/projects/${projectId}/strategy`,
  };
}

export async function loadStrategyIndex(): Promise<StrategyIndexResult> {
  const mode = getIntegrationMode();
  if (mode === "mock") {
    return {
      state: "mock_notice",
      items: [],
      message: "Mock-режим: стратегии не подставляются из фикстур.",
    };
  }
  try {
    const projects = await fetchProjects();
    const items: StrategyIndexItem[] = [];
    for (const p of projects) {
      try {
        const list = await fetchMarketingStrategies(p.id);
        for (const s of list) items.push(mapItem(p.id, p.name, s));
      } catch {
        /* skip */
      }
    }
    items.sort((a, b) => Date.parse(b.updatedAt || "0") - Date.parse(a.updatedAt || "0"));
    if (!items.length) {
      return {
        state: "empty",
        items: [],
        message: null,
      };
    }
    return { state: "success", items, message: null };
  } catch (err) {
    const msg = err instanceof Error ? err.message : "";
    if (/401|403|unauthorized/i.test(msg)) {
      return { state: "unauthorized", items: [], message: "Нет доступа к стратегиям." };
    }
    return {
      state: "error",
      items: [],
      message: "Сервис стратегий временно недоступен.",
    };
  }
}
