import { createCampaign, fetchCampaigns } from "@/lib/api/endpoints/campaigns";
import {
  createCampaignPlanDraft,
  generateAssetsFromPlanDraft,
} from "@/lib/api/endpoints/plan-drafts";
import type { PlanDraftGenerateAssetsResponse } from "@/lib/api/types/plan-drafts";
import {
  briefToPlanContentItems,
  type ContentFactoryBriefInput,
} from "@/lib/content-factory/brief-to-plan-items";

const CONTENT_FACTORY_CAMPAIGN_PREFIX = "Контент-завод:";

export type GenerateMaterialsFromBriefResult = PlanDraftGenerateAssetsResponse & {
  campaign_id: string;
  plan_draft_id: string;
};

async function resolveCampaignId(projectId: string, brief: ContentFactoryBriefInput): Promise<string> {
  const campaigns = await fetchCampaigns(projectId, { limit: 20 });
  const active = campaigns.find((row) => row.status !== "archived");
  if (active) {
    return active.id;
  }
  const created = await createCampaign(projectId, {
    title: `${CONTENT_FACTORY_CAMPAIGN_PREFIX} ${brief.topic.trim() || "проект"}`,
    description: "Контент-завод — автоматически созданная кампания для генерации материалов.",
    status: "active",
  });
  return created.id;
}

/** Foundation path: campaign plan draft → generate-assets (no demo metadata). */
export async function generateMaterialsFromBrief(
  projectId: string,
  brief: ContentFactoryBriefInput,
  minimumSlots: number,
): Promise<GenerateMaterialsFromBriefResult> {
  const campaignId = await resolveCampaignId(projectId, brief);
  const contentItems = briefToPlanContentItems(brief, minimumSlots);
  const draft = await createCampaignPlanDraft(projectId, campaignId, {
    title: `План: ${brief.topic.trim() || "контент"}`,
    plan_payload: {
      goal: brief.goal,
      target_audience: brief.audience,
      key_message: brief.topic,
      content_items: contentItems,
    },
  });
  const result = await generateAssetsFromPlanDraft(projectId, campaignId, draft.id);
  return {
    ...result,
    campaign_id: campaignId,
    plan_draft_id: draft.id,
  };
}
