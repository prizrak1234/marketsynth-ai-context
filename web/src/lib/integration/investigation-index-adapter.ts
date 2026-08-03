/** Cross-project Investigation index — aggregates existing per-project lists. */

import { fetchProjects } from "@/lib/api/endpoints/projects";
import { fetchInvestigations } from "@/lib/api/endpoints/investigations";
import type { InvestigationDto } from "@/lib/api/types/investigations";
import { getIntegrationMode } from "@/lib/integration/mode";

export type InvestigationIndexItem = {
  id: string;
  projectId: string;
  projectName: string;
  status: string;
  readiness: string | null;
  currentStage: string | null;
  sourceCount: number | null;
  evidenceCount: number | null;
  unresolvedContradictions: number | null;
  missingDataCount: number | null;
  updatedAt: string | null;
  nextAction: string;
  href: string;
};

export type InvestigationIndexResult = {
  state: "success" | "empty" | "error" | "unauthorized" | "mock_notice";
  items: InvestigationIndexItem[];
  message: string | null;
  nPlusOneNote: string;
};

function mapItem(
  projectId: string,
  projectName: string,
  inv: InvestigationDto,
): InvestigationIndexItem {
  const meta = inv.metadata || {};
  const num = (k: string): number | null =>
    typeof meta[k] === "number" ? (meta[k] as number) : null;
  return {
    id: inv.id,
    projectId,
    projectName,
    status: String(inv.status ?? "unknown"),
    readiness: inv.readiness_status != null ? String(inv.readiness_status) : null,
    currentStage: inv.current_stage != null ? String(inv.current_stage) : null,
    sourceCount: num("source_count"),
    evidenceCount: num("evidence_count"),
    unresolvedContradictions: num("unresolved_contradiction_count"),
    missingDataCount: num("missing_data_count"),
    updatedAt: inv.updated_at ?? null,
    nextAction: "Открыть Investigation Workspace",
    href: `/workspace/projects/${projectId}/investigation`,
  };
}

export async function loadInvestigationIndex(): Promise<InvestigationIndexResult> {
  const mode = getIntegrationMode();
  const nPlusOneNote =
    "N+1: GET /projects затем GET /projects/{id}/investigations на каждый проект (bounded). Глобальный aggregate endpoint не добавлен.";

  if (mode === "mock") {
    return {
      state: "mock_notice",
      items: [],
      message:
        "Mock-режим: список исследований не заполняется фикстурами. Используйте backend.",
      nPlusOneNote,
    };
  }

  try {
    const projects = await fetchProjects();
    const items: InvestigationIndexItem[] = [];
    for (const p of projects) {
      try {
        const list = await fetchInvestigations(p.id, { limit: 50 });
        for (const inv of list) {
          items.push(mapItem(p.id, p.name, inv));
        }
      } catch {
        /* skip project on list failure */
      }
    }
    items.sort((a, b) => Date.parse(b.updatedAt || "0") - Date.parse(a.updatedAt || "0"));
    if (items.length === 0) {
      return {
        state: "empty",
        items: [],
        message: "No investigations yet.",
        nPlusOneNote,
      };
    }
    return { state: "success", items, message: null, nPlusOneNote };
  } catch (err) {
    const msg = err instanceof Error ? err.message : "error";
    if (/401|403|unauthorized/i.test(msg)) {
      return {
        state: "unauthorized",
        items: [],
        message: "Нет доступа к исследованиям.",
        nPlusOneNote,
      };
    }
    return {
      state: "error",
      items: [],
      message: "Сервис исследований временно недоступен.",
      nPlusOneNote,
    };
  }
}
