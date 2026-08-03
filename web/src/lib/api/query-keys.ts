export const queryKeys = {
  health: ["health"] as const,
  projects: ["projects"] as const,
  ownerMetrics: ["me", "operational-metrics"] as const,
  projectMetrics: (projectId: string) =>
    ["projects", projectId, "operational-metrics"] as const,
  reviewQueue: (projectId: string) => ["projects", projectId, "review-queue"] as const,
  campaigns: (projectId: string) => ["projects", projectId, "campaigns"] as const,
  campaign: (projectId: string, campaignId: string) =>
    ["projects", projectId, "campaigns", campaignId] as const,
  campaignWorkflow: (projectId: string, campaignId: string) =>
    ["projects", projectId, "campaigns", campaignId, "workflow"] as const,
  campaignOverview: (projectId: string, campaignId: string) =>
    ["projects", projectId, "campaigns", campaignId, "overview"] as const,
  campaignAssets: (projectId: string, campaignId: string) =>
    ["projects", projectId, "campaigns", campaignId, "assets"] as const,
  publicationCalendar: (projectId: string, campaignId?: string) =>
    ["projects", projectId, "publication-calendar", campaignId ?? "all"] as const,
  publishingChannels: (projectId: string) =>
    ["projects", projectId, "publishing-channels"] as const,
  campaignPublicationJobs: (projectId: string, campaignId: string) =>
    ["projects", projectId, "campaigns", campaignId, "publication-jobs"] as const,
  campaignPlanDrafts: (projectId: string, campaignId: string) =>
    ["projects", projectId, "campaigns", campaignId, "plan-drafts"] as const,
  campaignPlanDraft: (projectId: string, campaignId: string, draftId: string) =>
    ["projects", projectId, "campaigns", campaignId, "plan-drafts", draftId] as const,
  contentAsset: (projectId: string, assetId: string) =>
    ["projects", projectId, "content-assets", assetId] as const,
  contentAssetVersions: (projectId: string, assetId: string) =>
    ["projects", projectId, "content-assets", assetId, "versions"] as const,
  contentAssetVersion: (
    projectId: string,
    assetId: string,
    versionNumber: number,
  ) =>
    [
      "projects",
      projectId,
      "content-assets",
      assetId,
      "versions",
      versionNumber,
    ] as const,
  agentChatSessions: (
    projectId: string,
    filters?: {
      agentId?: string;
      query?: string;
      domain?: string;
      status?: string;
    },
  ) =>
    [
      "projects",
      projectId,
      "agent-chat",
      "sessions",
      filters?.agentId ?? "all",
      filters?.query ?? "",
      filters?.domain ?? "",
      filters?.status ?? "active",
    ] as const,
  agentChatMessageSearch: (projectId: string, query: string, agentId?: string) =>
    ["projects", projectId, "agent-chat", "search-messages", query, agentId ?? "all"] as const,
  agentChatMetrics: (projectId: string) =>
    ["projects", projectId, "agent-chat", "metrics"] as const,
  agentChatAuditEvents: (projectId: string, sessionId?: string) =>
    ["projects", projectId, "agent-chat", "audit-events", sessionId ?? "all"] as const,
  agentChatMessages: (projectId: string, sessionId: string) =>
    ["projects", projectId, "agent-chat", "sessions", sessionId, "messages"] as const,
  agents: (projectId: string) => ["projects", projectId, "agents"] as const,
  agentRun: (runId: string) => ["agent-runs", runId] as const,
  demoFlowStatus: (projectId: string) =>
    ["projects", projectId, "demo-flow", "status"] as const,
  onboarding: (projectId: string) => ["me", "onboarding", projectId] as const,
  betaAdminDashboard: ["me", "beta-admin", "dashboard"] as const,
  betaAdminFeedback: ["me", "beta-admin", "feedback"] as const,
  betaQaExport: ["me", "beta-admin", "qa-export"] as const,
  myBetaFeedback: ["me", "beta-feedback"] as const,
  betaGuide: ["me", "beta-guide"] as const,
  betaAccess: ["me", "beta-access"] as const,
};
