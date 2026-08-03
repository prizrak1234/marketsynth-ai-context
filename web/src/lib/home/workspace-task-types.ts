/** Workspace Task projection — read model over conversational routes + optional sources. */

import type { IntentCategory } from "@/lib/home/intent-routing";

export type WorkspaceTaskStatus =
  | "draft"
  | "needs_clarification"
  | "routed"
  | "ready_for_draft"
  | "in_progress"
  | "done"
  | "cancelled";

export type WorkspaceTaskKind =
  | "user_request"
  | "specialist_task"
  | "project_linked"
  | "generic_task";

export type WorkspaceTaskAuthority = "local_draft" | "backend" | "hybrid_labelled";

export type WorkspaceTaskItem = {
  id: string;
  title: string;
  request_text: string;
  task_kind: WorkspaceTaskKind;
  route_category: IntentCategory | "general";
  origin: string;
  project_id: string | null;
  specialist_role: string | null;
  status: WorkspaceTaskStatus;
  next_action: string;
  result_summary: string | null;
  created_at: string;
  updated_at: string;
  source_domain: string;
  source_id: string;
  authority: WorkspaceTaskAuthority;
  next_href: string | null;
  skill_code?: string | null;
  skill_version?: string | null;
  execution_readiness?: string | null;
  missing_inputs?: string[];
  approved_knowledge_count?: number;
  knowledge_snapshot_hash?: string | null;
};
