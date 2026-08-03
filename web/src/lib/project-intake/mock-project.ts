/**
 * Create local mock investigation project from intake draft.
 */

import { evaluateIntakeReadiness } from "@/lib/project-intake/readiness";
import { saveMockProject } from "@/lib/project-intake/storage";
import type {
  MockInvestigationProject,
  ProjectIntakeDraft,
} from "@/lib/project-intake/types";
import type { AgencySpecialistStatus } from "@/lib/workspace/types";

export function createMockProjectFromDraft(
  draft: ProjectIntakeDraft,
): MockInvestigationProject {
  const readiness = evaluateIntakeReadiness(draft);
  const project: MockInvestigationProject = {
    id: `proj_${Math.random().toString(36).slice(2, 10)}`,
    name: draft.projectBasics.name.trim() || "Untitled project",
    status: "investigation_queued",
    statusLabel: "Investigation queued",
    createdAt: new Date().toISOString(),
    readiness,
    draftSnapshot: {
      ...draft,
      readiness,
      updatedAt: new Date().toISOString(),
    },
  };
  saveMockProject(project);
  return project;
}

/** Queued investigation specialists — static mock, not live execution */
export function queuedInvestigationSpecialists(): AgencySpecialistStatus[] {
  return [
    {
      id: "ceo",
      role: "CEO",
      state: "completed",
      progress: 100,
      detail: "Одобрил бриф и поставил исследование в очередь",
    },
    {
      id: "research_director",
      role: "Research Director",
      state: "waiting",
      progress: 0,
      detail: "Ожидает подключения backend execution (не запущено)",
    },
    {
      id: "competitor_analyst",
      role: "Competitor Analyst",
      state: "waiting",
      progress: 0,
      detail: "Очередь — реального анализа ещё нет",
    },
    {
      id: "audience_analyst",
      role: "Audience Analyst",
      state: "waiting",
      progress: 0,
      detail: "Очередь — сегменты не построены",
    },
    {
      id: "risk_officer",
      role: "Risk Officer",
      state: "waiting",
      progress: 0,
      detail: "Очередь — риски не оценены",
    },
    {
      id: "cms",
      role: "Chief Marketing Strategist",
      state: "waiting",
      progress: 0,
      detail: "Ожидает результаты исследования…",
    },
  ];
}
