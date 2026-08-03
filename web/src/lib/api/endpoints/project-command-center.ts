import { apiJson } from "@/lib/api/client";

export type PccCapabilityStatus =
  | "available"
  | "in_progress"
  | "requires_input"
  | "requires_approval"
  | "completed"
  | "paused"
  | "planned"
  | "unconfigured"
  | "blocked"
  | "coming_soon";

export type PccCapabilityCard = {
  capability_id: string;
  title: string;
  value_proposition: string;
  status: PccCapabilityStatus;
  status_label: string;
  last_result_summary: string | null;
  last_changed_at: string | null;
  primary_cta_label: string | null;
  primary_cta_href: string | null;
  secondary_cta_label: string | null;
  secondary_cta_href: string | null;
  cta_enabled: boolean;
  placeholder_note: string | null;
};

export type PccActivityItem = {
  id: string;
  title: string;
  kind: string;
  status: string;
  status_label: string;
  updated_at: string | null;
  open_href: string | null;
};

export type PccRecentResult = {
  id: string;
  title: string;
  kind: string;
  status: string;
  status_label: string;
  version: number | null;
  updated_at: string | null;
  open_href: string | null;
};

export type PccAttentionItem = {
  id: string;
  title: string;
  message: string;
  severity: string;
  cta_label: string | null;
  cta_href: string | null;
};

export type PccSkillChip = {
  skill_id: string;
  name: string;
  status: string;
  status_label: string;
};

export type ProjectCommandCenterSummary = {
  project_id: string;
  project_name: string;
  project_status: string;
  project_summary: string | null;
  last_changed_at: string | null;
  capabilities: PccCapabilityCard[];
  active_work: PccActivityItem[];
  recent_results: PccRecentResult[];
  attention: PccAttentionItem[];
  skills: PccSkillChip[];
};

export type PccGeneralMessage = {
  id: string;
  role: string;
  content: string;
  created_at: string;
  capability_id: string | null;
  skill_id: string | null;
  next_href: string | null;
  next_action_label: string | null;
  requires_paid: boolean;
  requires_external: boolean;
  requires_approval: boolean;
  status_notes: string | null;
};

export type PccGeneralConversation = {
  session_id: string;
  project_id: string;
  messages: PccGeneralMessage[];
};

export async function fetchProjectCommandCenter(
  projectId: string,
): Promise<ProjectCommandCenterSummary> {
  return apiJson<ProjectCommandCenterSummary>(
    `/projects/${encodeURIComponent(projectId)}/command-center`,
  );
}

export async function fetchProjectGeneral(
  projectId: string,
): Promise<PccGeneralConversation> {
  return apiJson<PccGeneralConversation>(
    `/projects/${encodeURIComponent(projectId)}/command-center/general`,
  );
}

export async function sendProjectGeneralMessage(
  projectId: string,
  message: string,
): Promise<{ conversation: PccGeneralConversation; assistant: PccGeneralMessage }> {
  return apiJson(
    `/projects/${encodeURIComponent(projectId)}/command-center/general/messages`,
    {
      method: "POST",
      body: { message },
    },
  );
}
