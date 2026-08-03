import type { PlanPayload } from "@/lib/api/types/plan-drafts";
import { optionalLocalDatetimeToUtcIso } from "@/lib/datetime";

export type ContentItemFormState = {
  title: string;
  channel: string;
  format: "text" | "photo";
  scheduledAtLocal: string;
  notes: string;
};

export function emptyContentItem(): ContentItemFormState {
  return {
    title: "",
    channel: "telegram",
    format: "text",
    scheduledAtLocal: "",
    notes: "",
  };
}

export function buildPlanPayloadFromForm(input: {
  goal: string;
  targetAudience: string;
  keyMessage: string;
  contentItems: ContentItemFormState[];
}): PlanPayload {
  const content_items = input.contentItems
    .filter((item) => item.title.trim().length > 0)
    .map((item) => ({
      title: item.title.trim(),
      channel: item.channel.trim() || "telegram",
      format: item.format,
      scheduled_at: item.scheduledAtLocal.trim()
        ? optionalLocalDatetimeToUtcIso(item.scheduledAtLocal)
        : null,
      notes: item.notes.trim() ? item.notes.trim() : null,
    }));

  if (content_items.length === 0) {
    throw new Error("Add at least one content item with a title");
  }

  return {
    goal: input.goal.trim(),
    target_audience: input.targetAudience.trim(),
    key_message: input.keyMessage.trim(),
    content_items,
  };
}
