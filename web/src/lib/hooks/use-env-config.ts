"use client";

import { getApiKey, getDefaultProjectId } from "@/lib/api/config";

export function useEnvConfig() {
  const apiKey = getApiKey();
  const projectId = getDefaultProjectId();

  return {
    apiKey,
    projectId,
    hasApiKey: Boolean(apiKey),
    hasProjectId: Boolean(projectId),
    isProjectScopeReady: Boolean(apiKey && projectId),
  };
}
