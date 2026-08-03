/** Maps backend UserRequest → WorkspaceTaskItem + Home conversation messages. */

import type { BackendUserRequestDto } from "@/lib/api/types/user-requests";
import type { IntentCategory, IntentRouteResult } from "@/lib/home/intent-routing";
import type {
  HomeChatMessage,
  HomeConversationState,
} from "@/lib/home/user-intent-draft";
import type { WorkspaceTaskItem, WorkspaceTaskStatus } from "@/lib/home/workspace-task-types";

function asCategory(value: string): IntentCategory {
  return value as IntentCategory;
}

function mapStatus(status: string): WorkspaceTaskStatus {
  switch (status) {
    case "needs_clarification":
      return "needs_clarification";
    case "routed":
      return "routed";
    case "ready_for_draft":
      return "ready_for_draft";
    case "in_progress":
      return "in_progress";
    case "completed":
      return "done";
    case "cancelled":
      return "cancelled";
    case "failed":
      return "cancelled";
    case "submitted":
      return "draft";
    default:
      return "routed";
  }
}

export function userRequestToTaskItem(dto: BackendUserRequestDto): WorkspaceTaskItem {
  return {
    id: dto.id,
    title: dto.title || dto.text.slice(0, 80) || "Задача",
    request_text: dto.text,
    task_kind: dto.route_kind === "specialist_task" ? "specialist_task" : "user_request",
    route_category: asCategory(dto.route_category),
    origin: dto.source || "home_conversation",
    project_id: dto.project_id,
    specialist_role: dto.assigned_specialist,
    status: mapStatus(dto.status),
    next_action: dto.next_action_label || "",
    result_summary: null,
    created_at: dto.created_at,
    updated_at: dto.updated_at,
    source_domain: "user_request",
    source_id: dto.id,
    authority: "backend",
    next_href: dto.next_href,
    skill_code: dto.skill_code,
    skill_version: dto.skill_version,
    execution_readiness: dto.execution_readiness,
    missing_inputs: dto.missing_inputs || [],
    approved_knowledge_count: dto.approved_knowledge_count ?? 0,
    knowledge_snapshot_hash: dto.knowledge_snapshot_hash,
  };
}

export function userRequestToRoute(dto: BackendUserRequestDto): IntentRouteResult {
  return {
    category: asCategory(dto.route_category),
    kind:
      dto.route_kind === "project_intake"
        ? "project_intake"
        : dto.route_kind === "specialist_task"
          ? "specialist_task"
          : "clarify",
    label: dto.title || dto.route_category,
    clarificationQuestion: dto.clarification_question,
    nextActionLabel: dto.next_action_label || "",
    nextHref: dto.next_href,
    requiresProject: dto.requires_project,
    assistantMessage: dto.assistant_message,
    assignedSpecialist: dto.assigned_specialist,
    requestId: dto.id,
    status: dto.status,
  };
}

export function conversationFromUserRequests(
  requests: BackendUserRequestDto[],
): HomeConversationState {
  const seen = new Set<string>();
  const chronological = [...requests]
    .sort((a, b) => Date.parse(a.created_at) - Date.parse(b.created_at))
    .filter((dto) => {
      if (seen.has(dto.id)) return false;
      seen.add(dto.id);
      return true;
    });
  const messages: HomeChatMessage[] = [];
  for (const dto of chronological) {
    messages.push({
      id: `u-${dto.id}`,
      role: "user",
      text: dto.text,
      created_at: dto.created_at,
      clientMessageId: dto.client_message_id ?? undefined,
      requestId: dto.id,
    });
    const parts = [dto.assistant_message];
    if (dto.clarification_question) parts.push(dto.clarification_question);
    if (dto.clarification_answer) {
      messages.push({
        id: `c-${dto.id}`,
        role: "user",
        text: dto.clarification_answer,
        created_at: dto.updated_at,
      });
    }
    messages.push({
      id: `a-${dto.id}`,
      role: "assistant",
      text: parts.filter(Boolean).join("\n\n"),
      created_at: dto.updated_at || dto.created_at,
      route: userRequestToRoute(dto),
      skillCode: dto.skill_code,
      generatedVisualAssetIds: dto.generated_visual_asset_ids || [],
      generationStatus: dto.generation_status,
      generationWarnings: dto.generation_warnings || [],
      contentDraft: dto.content_draft ?? null,
      contentDraftReviewStatus: dto.content_draft_review_status ?? null,
      requestId: dto.id,
      assignedSpecialist: dto.assigned_specialist,
      promptPackageHash: dto.prompt_package_hash ?? null,
      executionProvider: dto.execution_provider ?? null,
      executionModel: dto.execution_model ?? null,
    });
  }
  const last = chronological[chronological.length - 1] ?? null;
  return {
    draftText: "",
    messages,
    lastDraft: last
      ? {
          id: last.id,
          text: last.text,
          selected_scenario: (last.selected_scenario as IntentCategory | null) ?? null,
          status:
            last.status === "needs_clarification"
              ? "needs_clarification"
              : last.status === "routed"
                ? "routed"
                : "submitted",
          created_at: last.created_at,
          route_result: userRequestToRoute(last),
        }
      : null,
  };
}
