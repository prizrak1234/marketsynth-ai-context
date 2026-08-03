/** Canonical commercial route constants — safe for server redirect pages. */

export const CANONICAL_COMMERCIAL_ROUTES = {
  landing: "/",
  login: "/login",
  workspaceHome: "/workspace",
  intakeStart: "/workspace/projects/new",
  intakeReview: "/workspace/projects/new/review",
  projectsList: "/workspace/projects",
  settings: "/workspace/settings",
} as const;

export function canonicalIntakeHref(): string {
  return CANONICAL_COMMERCIAL_ROUTES.intakeStart;
}

export function workspaceProjectHref(projectId: string): string {
  const params = new URLSearchParams({ project: projectId });
  return `${CANONICAL_COMMERCIAL_ROUTES.workspaceHome}?${params.toString()}`;
}

export function loginNextHref(path: string): string {
  const params = new URLSearchParams({ next: path });
  return `${CANONICAL_COMMERCIAL_ROUTES.login}?${params.toString()}`;
}
