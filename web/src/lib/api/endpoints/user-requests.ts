import { apiJson } from "@/lib/api/client";
import type {
  BackendUserRequestDto,
  ContentDraftReviewAction,
} from "@/lib/api/types/user-requests";

export function createUserRequest(body: {
  text: string;
  selected_scenario?: string | null;
  source?: string;
  skill_inputs?: Record<string, string> | null;
  client_message_id?: string;
  idempotency_key?: string;
  conversation_id?: string;
}) {
  return apiJson<BackendUserRequestDto>("/user-requests", {
    method: "POST",
    body: {
      text: body.text,
      selected_scenario: body.selected_scenario ?? null,
      source: body.source ?? "home_conversation",
      skill_inputs: body.skill_inputs ?? null,
      client_message_id: body.client_message_id ?? null,
      idempotency_key: body.idempotency_key ?? null,
      conversation_id: body.conversation_id ?? null,
    },
  });
}

export function listUserRequests(limit = 100) {
  return apiJson<BackendUserRequestDto[]>(`/user-requests?limit=${limit}`);
}

export function clarifyUserRequest(
  requestId: string,
  answer: string,
  skillInputs?: Record<string, string>,
) {
  return apiJson<BackendUserRequestDto>(`/user-requests/${requestId}/clarify`, {
    method: "POST",
    body: {
      answer,
      skill_inputs: skillInputs ?? null,
    },
  });
}

export function reviewContentDraft(
  requestId: string,
  action: ContentDraftReviewAction,
  note?: string,
) {
  return apiJson<BackendUserRequestDto>(
    `/user-requests/${requestId}/content-draft/review`,
    {
      method: "POST",
      body: { action, note: note ?? null },
    },
  );
}
