/**
 * Post-auth commercial entry: own Project Command Center when possible.
 * WORKSPACE-BOOT-RECOVERY-02: shares routing table with workspace-boot.
 */

import {
  CANONICAL_COMMERCIAL_ROUTES,
  workspaceProjectHref,
} from "@/lib/routes/commercial-routes";
import {
  loadWorkspaceBootDestination,
  workspaceBootFromProjects,
} from "@/lib/workspace/workspace-boot";

export type WorkspaceEntryProject = { id: string };

/** Pure routing for tests and callers with a known project list. */
export function workspaceEntryHrefFromProjects(
  projects: ReadonlyArray<WorkspaceEntryProject>,
): string {
  const boot = workspaceBootFromProjects(projects);
  return boot.href;
}

/**
 * Resolve where the user should land after login/register.
 * Uses timed projects fetch; on error returns projects list (picker recovery).
 */
export async function resolveWorkspaceEntryHref(): Promise<string> {
  const result = await loadWorkspaceBootDestination();
  if (result.status === "error") {
    if (result.kind === "unauthorized") {
      return CANONICAL_COMMERCIAL_ROUTES.login;
    }
    return CANONICAL_COMMERCIAL_ROUTES.projectsList;
  }
  return result.href;
}

/** Prefer explicit `next` deep link; otherwise resolve commercial entry. */
export async function resolvePostAuthHref(nextParam: string | null): Promise<string> {
  if (nextParam && nextParam.startsWith("/") && !nextParam.startsWith("//")) {
    if (nextParam === "/workspace" || nextParam === "/workspace/") {
      return resolveWorkspaceEntryHref();
    }
    return nextParam;
  }
  return resolveWorkspaceEntryHref();
}

export { workspaceProjectHref };
