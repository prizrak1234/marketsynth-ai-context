export type AgentRunStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled";

export type AgentRun = {
  id: string;
  owner_id: string;
  project_id: string;
  task_id: string | null;
  agent_id: string;
  parent_agent_run_id: string | null;
  status: AgentRunStatus;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
};
