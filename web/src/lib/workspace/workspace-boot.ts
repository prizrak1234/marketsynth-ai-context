/**
 * WORKSPACE-BOOT-RECOVERY-02 — deterministic bare-/workspace boot resolution.
 * Pure helpers + timed fetch. No hard navigation / navigation timers.
 */

import { ApiError } from "@/lib/api/errors";
import { fetchProjects, type Project } from "@/lib/api/endpoints/projects";
import {
  CANONICAL_COMMERCIAL_ROUTES,
  workspaceProjectHref,
} from "@/lib/routes/commercial-routes";

export const WORKSPACE_BOOT_PROJECTS_TIMEOUT_MS = 8_000;

export type WorkspaceBootOk =
  | { status: "single_project"; projectId: string; href: string }
  | { status: "multi_projects"; href: string }
  | { status: "no_projects"; href: string };

export type WorkspaceBootError = {
  status: "error";
  kind: "timeout" | "unauthorized" | "http" | "unknown";
  message: string;
  retryable: boolean;
};

export type WorkspaceBootResult = WorkspaceBootOk | WorkspaceBootError;

export type WorkspaceBootUiPhase =
  | "skip" // URL already has project or content_director view
  | "loading"
  | "error"
  | "navigating"
  | "ready_inline"; // single project bound locally while URL catches up

/** Compare path+search ignoring trailing slash on pathname. */
export function workspaceUrlsEquivalent(a: string, b: string): boolean {
  try {
    const base = "http://local.invalid";
    const ua = new URL(a, base);
    const ub = new URL(b, base);
    const pathA = ua.pathname.replace(/\/$/, "") || "/";
    const pathB = ub.pathname.replace(/\/$/, "") || "/";
    return pathA === pathB && ua.search === ub.search;
  } catch {
    return a === b;
  }
}

export function classifyProjectsFetchError(err: unknown): WorkspaceBootError {
  if (err instanceof DOMException && err.name === "AbortError") {
    return {
      status: "error",
      kind: "timeout",
      message: "projects_timeout",
      retryable: true,
    };
  }
  if (err instanceof ApiError) {
    if (err.status === 401 || err.status === 403) {
      return {
        status: "error",
        kind: "unauthorized",
        message: err.errorCode || "authentication_required",
        retryable: false,
      };
    }
    return {
      status: "error",
      kind: "http",
      message: err.errorCode || err.message || `http_${err.status}`,
      retryable: true,
    };
  }
  return {
    status: "error",
    kind: "unknown",
    message: err instanceof Error ? err.message : "unknown_error",
    retryable: true,
  };
}

export function workspaceBootFromProjects(
  projects: ReadonlyArray<{ id: string }>,
): WorkspaceBootOk {
  if (projects.length === 1) {
    const projectId = projects[0].id;
    return {
      status: "single_project",
      projectId,
      href: workspaceProjectHref(projectId),
    };
  }
  if (projects.length > 1) {
    return {
      status: "multi_projects",
      href: CANONICAL_COMMERCIAL_ROUTES.projectsList,
    };
  }
  return {
    status: "no_projects",
    href: CANONICAL_COMMERCIAL_ROUTES.intakeStart,
  };
}

/**
 * Load projects with AbortSignal timeout. Does not navigate.
 */
export async function loadWorkspaceBootDestination(options?: {
  timeoutMs?: number;
  fetchProjectsFn?: () => Promise<Project[]>;
  signal?: AbortSignal;
}): Promise<WorkspaceBootResult> {
  const timeoutMs = options?.timeoutMs ?? WORKSPACE_BOOT_PROJECTS_TIMEOUT_MS;
  const fetchFn = options?.fetchProjectsFn ?? fetchProjects;
  const controller = new AbortController();
  const onOuterAbort = () => controller.abort();
  if (options?.signal) {
    if (options.signal.aborted) {
      return {
        status: "error",
        kind: "timeout",
        message: "projects_timeout",
        retryable: true,
      };
    }
    options.signal.addEventListener("abort", onOuterAbort, { once: true });
  }
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    // fetchProjects does not accept signal yet — race abort against the promise.
    // If controller is already aborted, reject immediately (abort events do not re-fire).
    if (controller.signal.aborted) {
      throw new DOMException("projects_timeout", "AbortError");
    }
    const projects = await Promise.race([
      fetchFn(),
      new Promise<never>((_, reject) => {
        const rejectAbort = () =>
          reject(new DOMException("projects_timeout", "AbortError"));
        if (controller.signal.aborted) {
          rejectAbort();
          return;
        }
        controller.signal.addEventListener("abort", rejectAbort, { once: true });
      }),
    ]);
    return workspaceBootFromProjects(projects);
  } catch (err) {
    return classifyProjectsFetchError(err);
  } finally {
    clearTimeout(timer);
    options?.signal?.removeEventListener("abort", onOuterAbort);
  }
}

/** Same routing table as workspace-entry — keep boot module free of cycles. */
export function bootHrefFromProjects(
  projects: ReadonlyArray<{ id: string }>,
): string {
  return workspaceBootFromProjects(projects).href;
}
