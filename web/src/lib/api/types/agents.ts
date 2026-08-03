export type AgentType =
  | "strategist"
  | "researcher"
  | "copywriter"
  | "content_planner"
  | "critic"
  | "analyst"
  | "orchestrator";

export type AgentStatus = "draft" | "active" | "paused" | "archived";

export type Agent = {
  id: string;
  project_id: string;
  owner_id: string;
  type: AgentType;
  name: string;
  status: AgentStatus;
};
