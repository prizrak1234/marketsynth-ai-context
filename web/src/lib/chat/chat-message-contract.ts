/** Chat golden path — client-side message contract helpers. */

export type ChatSubmitState =
  | "idle"
  | "submitting"
  | "accepted"
  | "routing"
  | "generating"
  | "completed"
  | "failed"
  | "session_expired";

export function newClientMessageId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `cm-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export function newIdempotencyKey(clientMessageId: string): string {
  return `chat-${clientMessageId}`;
}

export function mergeConversationSnapshot<
  T extends { id: string; clientMessageId?: string; created_at: string },
>(serverMessages: T[], optimistic: T[]): T[] {
  const byClient = new Map<string, T>();
  for (const msg of serverMessages) {
    if (msg.clientMessageId) {
      byClient.set(msg.clientMessageId, msg);
    }
  }
  const serverIds = new Set(serverMessages.map((m) => m.id));
  const pending = optimistic.filter(
    (m) => m.clientMessageId && !byClient.has(m.clientMessageId) && !serverIds.has(m.id),
  );
  return [...serverMessages, ...pending].sort(
    (a, b) => Date.parse(a.created_at) - Date.parse(b.created_at),
  );
}
