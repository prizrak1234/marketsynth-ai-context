/**
 * Shared BIV lifecycle enrichment for workspace project lists.
 * PRODUCT-01.3B — result delivery recovery.
 */

import {
  fetchProjectLatestBivRun,
  type ProjectLatestBivRunFetchResult,
} from "@/lib/api/endpoints/business-idea-validation";
import { bivLifecycleStatusLabel } from "@/lib/biv/biv-lifecycle-labels";
import type { WorkspaceProjectViewModel } from "@/lib/integration/contracts";

/** Cap sequential latest-run calls on project list surfaces. */
export const BIV_PROJECT_ENRICHMENT_LIMIT = 20;

export type BivProjectEnrichmentResult = {
  projects: WorkspaceProjectViewModel[];
  hydrationErrors: number;
  notFound: number;
};

export async function enrichWorkspaceProjectsWithBiv(
  projects: WorkspaceProjectViewModel[],
  options: { limit?: number } = {},
): Promise<BivProjectEnrichmentResult> {
  const limit = options.limit ?? BIV_PROJECT_ENRICHMENT_LIMIT;
  let hydrationErrors = 0;
  let notFound = 0;

  const enriched = await Promise.all(
    projects.map(async (project, index) => {
      if (project.origin !== "backend" || index >= limit) {
        return project;
      }
      const result: ProjectLatestBivRunFetchResult = await fetchProjectLatestBivRun(
        project.id,
      );
      if (result.kind === "found") {
        return {
          ...project,
          bivLifecycleLabel: bivLifecycleStatusLabel(result.summary),
        };
      }
      if (result.kind === "not_found") {
        notFound += 1;
        return project;
      }
      if (result.kind === "server_error") {
        hydrationErrors += 1;
        return {
          ...project,
          bivLifecycleLabel: null,
          bivHydrationError: true as const,
        };
      }
      return project;
    }),
  );

  return { projects: enriched, hydrationErrors, notFound };
}

export function workspaceProjectHref(projectId: string): string {
  return `/workspace?project=${encodeURIComponent(projectId)}`;
}
