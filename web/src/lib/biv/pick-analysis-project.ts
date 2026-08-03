import type { AnalysisContextRecord } from "@/lib/api/endpoints/analysis-contexts";

export type ProjectContextSnapshot = {
  projectId: string;
  projectUpdatedAt: string;
  context: AnalysisContextRecord | null;
  hasCompletedAnalysis: boolean;
  completedRunId: string | null;
};

export type PickAnalysisProjectInput = {
  snapshots: ProjectContextSnapshot[];
  preferredProjectIds?: string[];
};

function contextScore(snapshot: ProjectContextSnapshot): number {
  const state = snapshot.context?.state ?? "empty";
  if (state === "analyzing") return 900;
  // Unconfirmed hydration must win over completed legacy projects (PRODUCT-01.3A cold load).
  if (state === "hydrated_unconfirmed") return 850;
  if (snapshot.hasCompletedAnalysis) return 800;
  if (state === "completed") return 750;
  if (snapshot.context?.confirmed_by_user && state === "confirmed") return 500;
  if (state === "draft_entered" || state === "editing") return 300;
  if (!snapshot.context || state === "empty") return 100;
  return 400;
}

/** Pick the best project snapshot for workspace hydration (backend is source of truth). */
export function pickAnalysisProjectSnapshot(
  input: PickAnalysisProjectInput,
): ProjectContextSnapshot | null {
  const { snapshots, preferredProjectIds = [] } = input;
  if (snapshots.length === 0) {
    return null;
  }

  const preferredRank = new Map(
    preferredProjectIds
      .filter(Boolean)
      .map((projectId, index) => [projectId, preferredProjectIds.length - index] as const),
  );

  return [...snapshots].sort((left, right) => {
    const preferredDiff =
      (preferredRank.get(right.projectId) ?? 0) - (preferredRank.get(left.projectId) ?? 0);
    if (preferredDiff !== 0) {
      return preferredDiff;
    }

    const scoreDiff = contextScore(right) - contextScore(left);
    if (scoreDiff !== 0) {
      return scoreDiff;
    }

    return (
      new Date(right.projectUpdatedAt).getTime() - new Date(left.projectUpdatedAt).getTime()
    );
  })[0];
}
