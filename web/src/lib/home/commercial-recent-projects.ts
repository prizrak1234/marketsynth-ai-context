/**
 * Commercial Home — recent projects presentation.
 * Filters placeholder backend rows and maps honest unavailable labels to user-facing copy.
 */

import {
  workspaceProjectLifecycleLabel,
} from "@/lib/biv/biv-lifecycle-labels";
import { unavailableLabel } from "@/lib/integration/errors";
import type { WorkspaceProjectViewModel } from "@/lib/integration/contracts";

export const DEFAULT_NEW_PROJECT_NAME = "Новый проект";

function isUnavailableLabel(value: string): boolean {
  return value === unavailableLabel();
}

/** Empty auto-created drafts with no campaign context — not useful on Commercial Home. */
export function isCommercialRecentProjectPlaceholder(
  project: WorkspaceProjectViewModel,
): boolean {
  if (project.origin === "mock") return false;
  const stageUnavailable = isUnavailableLabel(project.stageLabel);
  const noCampaignSignal =
    project.activeCampaignCount === null || project.activeCampaignCount === 0;
  const genericStatus =
    isUnavailableLabel(project.statusLabel) && !project.bivLifecycleLabel;
  const placeholderName = project.name === DEFAULT_NEW_PROJECT_NAME;
  return placeholderName && stageUnavailable && noCampaignSignal && genericStatus;
}

export function filterCommercialRecentProjects(
  projects: WorkspaceProjectViewModel[],
): WorkspaceProjectViewModel[] {
  const filtered = projects.filter((p) => !isCommercialRecentProjectPlaceholder(p));
  const seen = new Set<string>();
  const deduped: WorkspaceProjectViewModel[] = [];
  for (const project of filtered) {
    const key = `${project.name}::${project.updatedAtIso ?? project.id}`;
    if (seen.has(key)) continue;
    seen.add(key);
    deduped.push(project);
  }
  return deduped;
}

export function commercialRecentProjectStatusLabel(
  project: WorkspaceProjectViewModel,
): string {
  return workspaceProjectLifecycleLabel({
    bivLifecycleLabel: project.bivLifecycleLabel,
    bivHydrationError: project.bivHydrationError,
    projectName: project.name,
    statusLabel: project.statusLabel,
  });
}
