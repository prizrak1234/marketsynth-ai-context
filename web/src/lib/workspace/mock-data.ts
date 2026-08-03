/**
 * Product Alpha Phase A1 — mock workspace data only.
 * Temporary until backend Investigation / Verdict / Agency Run APIs exist.
 */

import type {
  AgencySpecialistStatus,
  PipelineStage,
  RecentVerdict,
  WorkspaceProject,
  WorkspaceSnapshot,
} from "@/lib/workspace/types";

export const WORKSPACE_PIPELINE: PipelineStage[] = [
  { id: "idea", label: "Idea" },
  { id: "research", label: "Research" },
  { id: "competitors", label: "Competitors" },
  { id: "audience", label: "Audience" },
  { id: "risks", label: "Risks" },
  { id: "viability", label: "Viability" },
  { id: "verdict", label: "Verdict" },
  { id: "strategy", label: "Strategy" },
  { id: "execution", label: "Execution" },
];

export const MOCK_PROJECTS: WorkspaceProject[] = [
  {
    id: "proj_alpha",
    name: "Dental clinic lead gen",
    status: "investigation",
    statusLabel: "Investigation",
    stageLabel: "Audience research",
    lastAction: "Competitor Analyst uploaded landscape brief",
    updatedAtLabel: "12 мин назад",
    pipelineStage: "audience",
  },
  {
    id: "proj_beta",
    name: "B2B SaaS expansion RU",
    status: "verdict_pending",
    statusLabel: "Verdict pending",
    stageLabel: "Viability",
    lastAction: "Risk Officer flagged CAC assumptions",
    updatedAtLabel: "1 ч назад",
    pipelineStage: "viability",
  },
  {
    id: "proj_gamma",
    name: "Local services franchise",
    status: "paused",
    statusLabel: "Paused",
    stageLabel: "Research",
    lastAction: "Waiting for owner materials",
    updatedAtLabel: "вчера",
    pipelineStage: "research",
  },
];

/** Agency Runtime Monitor — demo showcase state (static mock, not animation). */
export const MOCK_AGENCY_SPECIALISTS: AgencySpecialistStatus[] = [
  {
    id: "ceo",
    role: "CEO",
    state: "completed",
    progress: 100,
    detail: "Одобрил запуск исследования",
  },
  {
    id: "research_director",
    role: "Research Director",
    state: "running",
    progress: 88,
    detail: "Исследует рынок…",
  },
  {
    id: "competitor_analyst",
    role: "Competitor Analyst",
    state: "running",
    progress: 62,
    detail: "Найдено 47 конкурентов",
  },
  {
    id: "audience_analyst",
    role: "Audience Analyst",
    state: "running",
    progress: 74,
    detail: "Формирует сегменты",
  },
  {
    id: "risk_officer",
    role: "Risk Officer",
    state: "running",
    progress: 35,
    detail: "Оценивает риски",
  },
  {
    id: "cms",
    role: "Chief Marketing Strategist",
    state: "waiting",
    progress: 0,
    detail: "Ожидает результаты…",
  },
];

export const MOCK_VERDICTS: RecentVerdict[] = [
  {
    id: "v_1",
    projectName: "Pet subscription box",
    kind: "CONDITIONAL_GO",
    summary: "Ниша жива при удержании CAC < 18% LTV и узком geo-фокусе.",
    updatedAtLabel: "2 дня назад",
  },
  {
    id: "v_2",
    projectName: "EdTech micro-courses",
    kind: "NO_GO",
    summary: "Перенасыщение + слабая дифференциация оффера.",
    updatedAtLabel: "5 дней назад",
  },
  {
    id: "v_3",
    projectName: "Clinic diagnostics upsell",
    kind: "INSUFFICIENT_DATA",
    summary: "Нет подтверждённых unit-экономики и канальных бенчмарков.",
    updatedAtLabel: "неделю назад",
  },
];

/** Toggle for empty-state hero preview without backend. Temporary. */
export const MOCK_WORKSPACE_SHOW_EMPTY = false;

export function getMockWorkspaceSnapshot(): WorkspaceSnapshot {
  const projects = MOCK_WORKSPACE_SHOW_EMPTY ? [] : MOCK_PROJECTS;
  const current = projects[0] ?? null;

  return {
    currentProject: current,
    projects,
    specialists: MOCK_AGENCY_SPECIALISTS,
    pipeline: WORKSPACE_PIPELINE,
    activePipelineStage: current?.pipelineStage ?? "idea",
    verdicts: MOCK_WORKSPACE_SHOW_EMPTY ? [] : MOCK_VERDICTS,
    user: {
      displayName: "Owner",
      roleLabel: "Project owner",
    },
  };
}
