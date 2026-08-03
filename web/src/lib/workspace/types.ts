/**
 * Product Alpha — Workspace domain types (frontend-only, mock).
 * Not synced to backend contracts in Phase A1.
 */

export type ProjectStatus =
  | "intake"
  | "research"
  | "investigation"
  | "verdict_pending"
  | "strategy"
  | "execution"
  | "paused";

export type PipelineStageId =
  | "idea"
  | "research"
  | "competitors"
  | "audience"
  | "risks"
  | "viability"
  | "verdict"
  | "strategy"
  | "execution";

export type VerdictKindUi =
  | "GO"
  | "CONDITIONAL_GO"
  | "NO_GO"
  | "INSUFFICIENT_DATA";

export type SpecialistRunState = "completed" | "running" | "waiting" | "blocked";

export type WorkspaceProject = {
  id: string;
  name: string;
  status: ProjectStatus;
  statusLabel: string;
  stageLabel: string;
  lastAction: string;
  updatedAtLabel: string;
  pipelineStage: PipelineStageId;
};

export type AgencySpecialistStatus = {
  id: string;
  role: string;
  state: SpecialistRunState;
  /** 0–100 for running/completed progress bars; ignored when waiting */
  progress: number;
  detail: string;
};

export type PipelineStage = {
  id: PipelineStageId;
  label: string;
};

export type RecentVerdict = {
  id: string;
  projectName: string;
  kind: VerdictKindUi;
  summary: string;
  updatedAtLabel: string;
};

export type WorkspaceUser = {
  displayName: string;
  roleLabel: string;
};

export type WorkspaceSnapshot = {
  currentProject: WorkspaceProject | null;
  projects: WorkspaceProject[];
  specialists: AgencySpecialistStatus[];
  pipeline: PipelineStage[];
  activePipelineStage: PipelineStageId;
  verdicts: RecentVerdict[];
  user: WorkspaceUser;
};
