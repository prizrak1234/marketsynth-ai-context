import type { PlanContentItem } from "@/lib/api/types/plan-drafts";
import { backendChannelForProduct, type ContentFactoryProductChannelId } from "@/lib/content-factory/labels";

export type ContentFactoryBriefInput = {
  channel: ContentFactoryProductChannelId;
  topic: string;
  goal: string;
  audience: string;
  period: string;
  frequency: string;
  format: string;
  sourceMaterials: string;
};

function slotNotes(brief: ContentFactoryBriefInput, index: number, total: number): string {
  const lines = [
    `Тема: ${brief.topic}`,
    `Цель: ${brief.goal}`,
    `Аудитория: ${brief.audience}`,
  ];
  if (brief.period.trim()) {
    lines.push(`Период: ${brief.period}`);
  }
  if (brief.frequency.trim()) {
    lines.push(`Частота: ${brief.frequency}`);
  }
  if (brief.sourceMaterials.trim()) {
    lines.push(`Исходные материалы: ${brief.sourceMaterials}`);
  }
  lines.push(`Слот ${index} из ${total} — черновик контент-завода.`);
  return lines.join("\n\n");
}

/** Map owner brief into mechanical plan slots for foundation generate-assets. */
export function briefToPlanContentItems(
  brief: ContentFactoryBriefInput,
  minimumSlots: number,
): PlanContentItem[] {
  const backendChannel = backendChannelForProduct(brief.channel);
  const format = brief.format.trim() || "text";
  const count = Math.max(minimumSlots, 3);

  return Array.from({ length: count }, (_, offset) => {
    const index = offset + 1;
    const titleBase = brief.topic.trim() || "Материал";
    return {
      title: `${titleBase} — ${index}`,
      channel: backendChannel,
      format,
      notes: slotNotes(brief, index, count),
    };
  });
}
