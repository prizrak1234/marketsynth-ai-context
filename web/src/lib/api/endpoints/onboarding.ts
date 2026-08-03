import { apiJson } from "@/lib/api/client";
import type { OnboardingStatus, OnboardingStep } from "@/lib/api/types/onboarding";

export function fetchOnboardingStatus(
  projectId?: string,
): Promise<OnboardingStatus> {
  const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  return apiJson<OnboardingStatus>(`/me/onboarding${query}`);
}

export function completeOnboardingStep(step: OnboardingStep): Promise<OnboardingStatus> {
  return apiJson<OnboardingStatus>("/me/onboarding/complete-step", {
    method: "POST",
    body: JSON.stringify({ step }),
  });
}
