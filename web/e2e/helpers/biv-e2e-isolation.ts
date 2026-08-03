import { execSync } from "node:child_process";
import * as fs from "node:fs";
import * as path from "node:path";
import type { Page } from "@playwright/test";
import { apiJson, type E2ERunContext } from "./cph2";

export type E2EIsolationLog = {
  action: string;
  run_id: string;
  email: string;
  password?: string;
  dry_run?: boolean;
  projects_before?: number;
  projects_after?: number;
  projects_created?: number;
  projects_archived?: number;
  projects_deleted?: number;
  projects_skipped?: number;
};

const MARKER_PREFIX = "E2E-BIV-";

function repoRootFromWeb(): string {
  return path.join(process.cwd(), "..");
}

function runIsolationScript(command: "provision" | "cleanup", runId: string, dryRun = false): E2EIsolationLog {
  const repoRoot = repoRootFromWeb();
  const args = [`scripts/e2e_biv_isolation.py`, command, "--run-id", runId];
  if (dryRun) {
    args.push("--dry-run");
  }
  const output = execSync(`uv run python ${args.map((arg) => JSON.stringify(arg)).join(" ")}`, {
    cwd: repoRoot,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
  return JSON.parse(output.trim()) as E2EIsolationLog;
}

export function provisionBivE2eRun(runId: string): E2EIsolationLog {
  return runIsolationScript("provision", runId);
}

export function cleanupBivE2eRun(runId: string, options?: { dryRun?: boolean }): E2EIsolationLog {
  return runIsolationScript("cleanup", runId, options?.dryRun ?? false);
}

export function buildTestProjectName(runId: string, scenario: string): string {
  return `${MARKER_PREFIX}${runId}-${scenario}`;
}

export function buildTestProjectDescription(runId: string, scenario: string): string {
  return `test_project=true;e2e_run_id=${runId};e2e_scenario=${scenario}`;
}

export type IsolatedTestProject = {
  projectId: string;
  name: string;
  scenario: string;
};

export async function createIsolatedTestProject(
  page: Page,
  ctx: E2ERunContext,
  scenario: string,
): Promise<IsolatedTestProject> {
  const name = buildTestProjectName(ctx.runId, scenario);
  const description = buildTestProjectDescription(ctx.runId, scenario);
  const created = await apiJson<{ id: string; name: string }>(page, ctx, "POST", "/projects", {
    name,
    description,
  });
  await apiJson(page, ctx, "POST", `/projects/${created.id}/analysis-contexts/start-new`, {});
  return { projectId: created.id, name: created.name, scenario };
}

export async function openProjectWorkspace(page: Page, projectId: string): Promise<void> {
  await page.goto(`/workspace?project=${projectId}`);
  await page.getByTestId("workspace-home").waitFor({ state: "visible", timeout: 60_000 });
  await page.waitForLoadState("networkidle");
}

export async function countProjects(page: Page, ctx: E2ERunContext): Promise<number> {
  const projects = await apiJson<Array<{ id: string }>>(page, ctx, "GET", "/projects");
  return projects.length;
}

export function appendIsolationLog(artifactDir: string, entry: E2EIsolationLog): void {
  const file = path.join(artifactDir, "isolation-log.jsonl");
  fs.appendFileSync(file, `${JSON.stringify({ saved_at: new Date().toISOString(), ...entry })}\n`, "utf8");
}

export async function listTestProjects(
  page: Page,
  ctx: E2ERunContext,
): Promise<Array<{ id: string; name: string; description: string | null }>> {
  const projects = await apiJson<Array<{ id: string; name: string; description: string | null }>>(
    page,
    ctx,
    "GET",
    "/projects",
  );
  return projects.filter(
    (project) =>
      project.name.startsWith(`${MARKER_PREFIX}${ctx.runId}`) ||
      (project.description ?? "").includes(`e2e_run_id=${ctx.runId}`),
  );
}
