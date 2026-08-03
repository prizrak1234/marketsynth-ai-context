/** Cross-project BusinessVerdict index. */

import { fetchProjects } from "@/lib/api/endpoints/projects";
import { fetchBusinessVerdicts } from "@/lib/api/endpoints/business-verdicts";
import type { BackendVerdictDto } from "@/lib/api/types/business-verdicts";
import { getIntegrationMode } from "@/lib/integration/mode";

export type VerdictIndexItem = {
  id: string;
  projectId: string;
  projectName: string;
  verdictType: string;
  version: number;
  lifecycleStatus: string;
  confidence: string;
  snapshotHashShort: string;
  reviewDate: string | null;
  strategyEligible: boolean;
  href: string;
};

export type VerdictIndexResult = {
  state: "success" | "empty" | "error" | "unauthorized" | "mock_notice";
  items: VerdictIndexItem[];
  message: string | null;
};

function mapItem(
  projectId: string,
  projectName: string,
  v: BackendVerdictDto,
): VerdictIndexItem {
  const hash = v.evidence_snapshot_hash || "";
  return {
    id: v.id,
    projectId,
    projectName,
    verdictType: v.verdict_type,
    version: v.version,
    lifecycleStatus: v.lifecycle_status,
    confidence: v.confidence_level,
    snapshotHashShort: hash ? `${hash.slice(0, 10)}…` : "—",
    reviewDate: v.approved_at || v.submitted_at || null,
    strategyEligible: Boolean(v.strategy_eligibility?.strategy_eligible),
    href: `/workspace/projects/${projectId}/verdict`,
  };
}

export async function loadVerdictIndex(): Promise<VerdictIndexResult> {
  const mode = getIntegrationMode();
  if (mode === "mock") {
    return {
      state: "mock_notice",
      items: [],
      message: "Mock-режим: вердикты не подставляются из фикстур.",
    };
  }
  try {
    const projects = await fetchProjects();
    const items: VerdictIndexItem[] = [];
    for (const p of projects) {
      try {
        const list = await fetchBusinessVerdicts(p.id);
        for (const v of list) items.push(mapItem(p.id, p.name, v));
      } catch {
        /* skip */
      }
    }
    items.sort((a, b) => Date.parse(b.reviewDate || "0") - Date.parse(a.reviewDate || "0"));
    if (!items.length) {
      return {
        state: "empty",
        items: [],
        message: "У вас пока нет вердиктов.",
      };
    }
    return { state: "success", items, message: null };
  } catch (err) {
    const msg = err instanceof Error ? err.message : "";
    if (/401|403|unauthorized/i.test(msg)) {
      return { state: "unauthorized", items: [], message: "Нет доступа к вердиктам." };
    }
    return {
      state: "error",
      items: [],
      message: "Сервис вердиктов временно недоступен.",
    };
  }
}
