import { apiJson } from "@/lib/api/client";
import type {
  CreateMarketingSkillRunInput,
  MarketingSkillDefinition,
  MarketingSkillRun,
  MarketingSkillType,
} from "@/lib/api/types/marketing-skills";

export function fetchMarketingSkillDefinitions(
  projectId: string,
): Promise<MarketingSkillDefinition[]> {
  return apiJson<MarketingSkillDefinition[]>(
    `/projects/${projectId}/marketing-skills/definitions`,
  );
}

export function createMarketingSkillRun(
  projectId: string,
  skillType: MarketingSkillType,
  body: CreateMarketingSkillRunInput,
): Promise<MarketingSkillRun> {
  return apiJson<MarketingSkillRun>(
    `/projects/${projectId}/marketing-skills/${skillType}/runs`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export function fetchMarketingSkillRuns(
  projectId: string,
  params?: { campaign_id?: string; skill_type?: MarketingSkillType; limit?: number },
): Promise<MarketingSkillRun[]> {
  const search = new URLSearchParams();
  if (params?.campaign_id) search.set("campaign_id", params.campaign_id);
  if (params?.skill_type) search.set("skill_type", params.skill_type);
  if (params?.limit) search.set("limit", String(params.limit));
  const query = search.toString();
  return apiJson<MarketingSkillRun[]>(
    `/projects/${projectId}/marketing-skills/runs${query ? `?${query}` : ""}`,
  );
}

export function fetchMarketingSkillRun(
  projectId: string,
  runId: string,
): Promise<MarketingSkillRun> {
  return apiJson<MarketingSkillRun>(
    `/projects/${projectId}/marketing-skills/runs/${runId}`,
  );
}
