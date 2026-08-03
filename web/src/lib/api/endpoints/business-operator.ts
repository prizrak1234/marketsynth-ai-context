import { apiJson } from "@/lib/api/client";
import type {
  BusinessOperatorAnalyzeResponse,
  BusinessOperatorBriefConfirmInput,
  BusinessOperatorBriefConfirmResponse,
  BusinessOperatorBriefInput,
  BusinessOperatorBriefResponse,
  BusinessOperatorClarifyInput,
  BusinessOperatorClarifyResponse,
  BusinessOperatorCreateCampaignInput,
  BusinessOperatorCreateCampaignResponse,
  BusinessOperatorMessageInput,
} from "@/lib/api/types/business-operator";

export function analyzeBusinessIntent(
  projectId: string,
  body: BusinessOperatorMessageInput,
): Promise<BusinessOperatorAnalyzeResponse> {
  return apiJson<BusinessOperatorAnalyzeResponse>(
    `/projects/${projectId}/business-operator/analyze`,
    {
      method: "POST",
      body: JSON.stringify(body),
    },
  );
}

export function clarifyBusinessIntent(
  projectId: string,
  body: BusinessOperatorClarifyInput,
): Promise<BusinessOperatorClarifyResponse> {
  return apiJson<BusinessOperatorClarifyResponse>(
    `/projects/${projectId}/business-operator/clarify`,
    {
      method: "POST",
      body: JSON.stringify(body),
    },
  );
}

export function completeBusinessBrief(
  projectId: string,
  body: BusinessOperatorBriefInput,
): Promise<BusinessOperatorBriefResponse> {
  return apiJson<BusinessOperatorBriefResponse>(
    `/projects/${projectId}/business-operator/brief/complete`,
    {
      method: "POST",
      body: JSON.stringify(body),
    },
  );
}

export function confirmBusinessBrief(
  projectId: string,
  body: BusinessOperatorBriefConfirmInput,
): Promise<BusinessOperatorBriefConfirmResponse> {
  return apiJson<BusinessOperatorBriefConfirmResponse>(
    `/projects/${projectId}/business-operator/brief/confirm`,
    {
      method: "POST",
      body: JSON.stringify(body),
    },
  );
}

export function createCampaignFromBusinessOperator(
  projectId: string,
  body: BusinessOperatorCreateCampaignInput,
): Promise<BusinessOperatorCreateCampaignResponse> {
  return apiJson<BusinessOperatorCreateCampaignResponse>(
    `/projects/${projectId}/business-operator/create-campaign`,
    {
      method: "POST",
      body: JSON.stringify(body),
    },
  );
}
