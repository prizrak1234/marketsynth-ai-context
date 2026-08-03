/** Cross-project ImplementationPlan index (Realization). */

import { fetchProjects } from "@/lib/api/endpoints/projects";
import { fetchImplementationPlans } from "@/lib/api/endpoints/implementation-plans";
import { fetchMarketingPlans } from "@/lib/api/endpoints/marketing-plans";
import type { BackendImplementationPlanDto } from "@/lib/api/types/implementation-plans";
import { getIntegrationMode } from "@/lib/integration/mode";

export type ImplementationIndexItem = {
  id: string;
  projectId: string;
  projectName: string;
  strategyVersion: number;
  planVersion: number;
  lifecycleStatus: string;
  readiness: string;
  workstreamCount: number;
  blockerCount: number;
  handoffStatus: string | null;
  marketingPlanHint: string | null;
  href: string;
};

export type ImplementationIndexResult = {
  state: "success" | "empty" | "error" | "unauthorized" | "mock_notice";
  items: ImplementationIndexItem[];
  message: string | null;
};

function mapItem(
  projectId: string,
  projectName: string,
  plan: BackendImplementationPlanDto,
  marketingPlanHint: string | null,
): ImplementationIndexItem {
  return {
    id: plan.id,
    projectId,
    projectName,
    strategyVersion: plan.marketing_strategy_version,
    planVersion: plan.version,
    lifecycleStatus: plan.lifecycle_status,
    readiness: plan.readiness_status,
    workstreamCount: plan.workstreams?.length || 0,
    blockerCount: (plan.conditions?.length || 0) + (plan.implementation_risks?.length || 0),
    handoffStatus: null,
    marketingPlanHint,
    href: `/workspace/projects/${projectId}/implementation`,
  };
}

export async function loadImplementationIndex(): Promise<ImplementationIndexResult> {
  const mode = getIntegrationMode();
  if (mode === "mock") {
    return {
      state: "mock_notice",
      items: [],
      message: "Mock-режим: планы реализации не подставляются из фикстур.",
    };
  }
  try {
    const projects = await fetchProjects();
    const items: ImplementationIndexItem[] = [];
    for (const p of projects) {
      let planHint: string | null = null;
      try {
        const mps = await fetchMarketingPlans(p.id);
        if (mps[0]) {
          planHint = `${mps[0].id.slice(0, 8)}… / ${String((mps[0] as { status?: string }).status ?? "—")}`;
        }
      } catch {
        planHint = null;
      }
      try {
        const list = await fetchImplementationPlans(p.id, { limit: 20 });
        for (const plan of list) items.push(mapItem(p.id, p.name, plan, planHint));
      } catch {
        /* skip */
      }
    }
    if (!items.length) {
      return {
        state: "empty",
        items: [],
        message: "Пока нет планов реализации.",
      };
    }
    return { state: "success", items, message: null };
  } catch (err) {
    const msg = err instanceof Error ? err.message : "";
    if (/401|403|unauthorized/i.test(msg)) {
      return {
        state: "unauthorized",
        items: [],
        message: "Нет доступа к планам реализации.",
      };
    }
    return {
      state: "error",
      items: [],
      message: "Сервис реализации временно недоступен.",
    };
  }
}
