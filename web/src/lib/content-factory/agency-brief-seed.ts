import type { ContentFactoryBriefSeed } from "@/lib/home/content-factory-owner-preview";
import type { BackendUserRequestDto } from "@/lib/api/types/user-requests";

/** Seed content factory brief from Commercial Home verdict context. */
export function buildBriefSeedFromAgencyContext(input: {
  taskText: string;
  dto: BackendUserRequestDto | null;
}): Partial<ContentFactoryBriefSeed> {
  const taskText = input.taskText.trim();
  const researchSummary = input.dto?.research_collection?.research_summary?.trim() ?? "";
  const assistant = input.dto?.assistant_message?.trim() ?? "";

  const firstLine = taskText.split(/\n/)[0]?.trim() ?? "";
  const topic = firstLine.slice(0, 200);

  const sourceParts = [researchSummary, assistant].filter(Boolean);
  const sourceMaterials = sourceParts.join("\n\n").slice(0, 4000);

  return {
    topic,
    goal: topic ? "Поддержать решение после вердикта и подготовить контент" : "",
    audience: "",
    sourceMaterials,
  };
}
