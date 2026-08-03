import { execSync } from "node:child_process";
import * as fs from "node:fs";
import * as path from "node:path";
import { expect, type BrowserContext, type Page } from "@playwright/test";

import { buildResearchIdempotencyKey } from "../../src/lib/api/endpoints/business-idea-validation";
import { bivLifecycleStatusLabel } from "../../src/lib/biv/biv-lifecycle-labels";
import { apiJson, type E2ERunContext } from "./cph2";
import {
  appendIsolationLog,
  cleanupBivE2eRun,
  createIsolatedTestProject,
  openProjectWorkspace,
  provisionBivE2eRun,
} from "./biv-e2e-isolation";
import {
  bivLogin,
  confirmIntake,
  createRunRequestTracker,
  fillMinimalIntake,
  type RunRequestTracker,
  waitForAsyncRunPost,
} from "./biv-golden-path";
import {
  bindDeterministicFixture,
  cleanupRuntime01fContext,
  clearDeterministicFixture,
  loadRuntime01fContext,
  waitForTerminalUi,
  type E2eDeterministicOutcome,
} from "./runtime-01f-golden-path";

export type LatestRunSummary = {
  project_id: string;
  run_id: string;
  user_request_id: string;
  status: string;
  progress?: { state?: string } | null;
  result_kind?: string | null;
  safe_error_code?: string | null;
  safe_message?: string | null;
  has_output?: boolean;
  analysis_context_id?: string | null;
  input_snapshot_hash?: string | null;
};

export type DbActiveRunSnapshot = {
  active_run_count: number;
};

export type DbInvestigationSnapshot = {
  investigation_id?: string;
  status?: string;
  superseded?: boolean;
};

export type DbRunSnapshot = {
  run_id?: string;
  project_id?: string;
  status?: string;
  error_code?: string | null;
  has_output?: boolean;
  progress_state?: string | null;
  investigation_id?: string | null;
};

export type ScenarioEvidence = {
  scenario: string;
  project_id: string;
  user_request_id?: string;
  run_id?: string;
  post_runs_count: number;
  latest_run?: LatestRunSummary | null;
  active_run_count?: number;
  investigation?: DbInvestigationSnapshot;
  run_snapshot?: DbRunSnapshot;
  recent_project_label?: string | null;
  progress_state?: string | null;
  has_output?: boolean;
};

const ARTIFACT_DIR = "e2e-artifacts/runtime-01g-concurrent-run-recovery";

function repoRootFromWeb(): string {
  return path.join(process.cwd(), "..");
}

function runDbAssert(command: string, args: Record<string, string>): unknown {
  const parts = [`scripts/e2e_biv_runtime_01g_assert.py`, command];
  for (const [key, value] of Object.entries(args)) {
    parts.push(key, value);
  }
  const output = execSync(`uv run python ${parts.map((part) => JSON.stringify(part)).join(" ")}`, {
    cwd: repoRootFromWeb(),
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
  return JSON.parse(output.trim()) as unknown;
}

export function loadRuntime01gContext(): E2ERunContext & { artifactDir: string } {
  const ctx = loadRuntime01fContext();
  fs.mkdirSync(path.join(process.cwd(), ARTIFACT_DIR), { recursive: true });
  return ctx;
}

export function cleanupRuntime01gContext(ctx: E2ERunContext & { artifactDir: string }): void {
  cleanupRuntime01fContext(ctx);
  const cleanup = cleanupBivE2eRun(ctx.runId, { dryRun: false });
  appendIsolationLog(ctx.artifactDir, cleanup);
}

export async function apiFetch<T>(
  page: Page,
  ctx: E2ERunContext,
  method: string,
  urlPath: string,
  body?: unknown,
): Promise<{ status: number; body: T | null; raw: string }> {
  const backendUrl = ctx.backendUrl.replace(/\/$/, "");
  let aligned = backendUrl;
  try {
    const front = new URL(ctx.frontendUrl);
    const back = new URL(backendUrl);
    const loopback = (h: string) => h === "localhost" || h === "127.0.0.1";
    if (loopback(front.hostname) && loopback(back.hostname) && front.hostname !== back.hostname) {
      back.hostname = front.hostname;
      aligned = back.origin;
    }
  } catch {
    /* keep backendUrl */
  }
  const res = await page.request.fetch(`${aligned}${urlPath}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      Origin: ctx.frontendUrl,
    },
    data: body,
  });
  const raw = await res.text();
  let parsed: T | null = null;
  if (raw) {
    try {
      parsed = JSON.parse(raw) as T;
    } catch {
      parsed = null;
    }
  }
  return { status: res.status(), body: parsed, raw };
}

export async function fetchLatestRun(
  page: Page,
  ctx: E2ERunContext,
  projectId: string,
): Promise<LatestRunSummary | null> {
  const res = await apiFetch<LatestRunSummary>(
    page,
    ctx,
    "GET",
    `/projects/${projectId}/business-idea-validation/latest-run`,
  );
  if (res.status === 404) {
    return null;
  }
  expect(res.status, res.raw).toBe(200);
  return res.body;
}

export function queryActiveRunCount(projectId: string): number {
  const payload = runDbAssert("active-run-count", { "--project-id": projectId }) as DbActiveRunSnapshot;
  return payload.active_run_count;
}

export function queryInvestigation(runId: string): DbInvestigationSnapshot {
  return runDbAssert("investigation", { "--run-id": runId }) as DbInvestigationSnapshot;
}

export function queryRunSnapshot(runId: string): DbRunSnapshot {
  return runDbAssert("run-snapshot", { "--run-id": runId }) as DbRunSnapshot;
}

export async function prepareIsolatedProject(
  page: Page,
  ctx: E2ERunContext,
  scenario: string,
  options?: { seedDraft?: boolean },
): Promise<{ projectId: string; name: string }> {
  const project = await createIsolatedTestProject(page, ctx, scenario);
  if (options?.seedDraft !== false) {
    await apiJson(page, ctx, "POST", `/projects/${project.projectId}/analysis-contexts`, {
      idea_description: `E2E ${scenario} ${Date.now()}`,
      product_or_service: "SaaS для автоматизации отчётности",
      target_customer: "Малый бизнес и стартапы",
      geography: "Россия, онлайн",
      analysis_goal: "Проверить коммерческую жизнеспособность",
    });
  }
  await openProjectWorkspace(page, project.projectId);
  if (options?.seedDraft !== false) {
    await expect(page.getByTestId("analysis-intake-panel")).toBeVisible({ timeout: 60_000 });
  }
  return { projectId: project.projectId, name: project.name };
}

export async function confirmIntakeAndStartResearch(
  page: Page,
  idea: string,
  projectId: string,
): Promise<void> {
  await fillMinimalIntake(page, idea, { projectId });
  await confirmIntake(page);
}

export async function confirmIntakeDoubleClick(
  page: Page,
  idea: string,
  projectId: string,
): Promise<void> {
  await fillMinimalIntake(page, idea, { projectId });
  const confirm = page.getByTestId("intake-confirm-button");
  await expect(confirm).toBeEnabled({ timeout: 15_000 });
  await confirm.dblclick();
  await expect(
    page
      .getByTestId("biv-research-progress")
      .or(page.getByTestId("business-validation-result-card"))
      .or(page.getByTestId("biv-research-failed"))
      .or(page.getByTestId("biv-partial-research-panel")),
  ).toBeVisible({ timeout: 90_000 });
}

export async function clearBivStorageHints(page: Page): Promise<void> {
  await page.evaluate(() => {
    window.sessionStorage.removeItem("ms_active_biv_research");
    window.localStorage.removeItem("ms_terminal_partial_biv_research");
  });
}

export async function enqueueSecondRunSameProject(
  page: Page,
  ctx: E2ERunContext,
  projectId: string,
): Promise<{ run_id: string; lineage_reused?: boolean; user_request_id: string }> {
  const draft = await apiJson<{
    context_id: string;
    input_snapshot_hash: string;
  }>(page, ctx, "POST", `/projects/${projectId}/analysis-contexts`, {
    idea_description: "Повторная проверка спроса для E2E",
    product_or_service: "SaaS для строительного B2B",
    target_customer: "Коммерческие директора строительных компаний",
    geography: "Россия, B2B",
    analysis_goal: "Повторная проверка спроса",
  });
  const confirmed = await apiJson<{ context_id: string; input_snapshot_hash: string }>(
    page,
    ctx,
    "POST",
    `/projects/${projectId}/analysis-contexts/${draft.context_id}/confirm`,
    { input_snapshot_hash: draft.input_snapshot_hash },
  );
  const userRequest = await apiJson<{ id: string }>(page, ctx, "POST", "/user-requests", {
    text: "Повторная проверка идеи",
    selected_scenario: "idea_validation",
    skill_inputs: { home_agency_flow: "v2" },
  });
  const idempotencyKey = buildResearchIdempotencyKey(
    confirmed.context_id,
    confirmed.input_snapshot_hash,
  );
  const run = await apiJson<{ run_id: string; lineage_reused?: boolean }>(
    page,
    ctx,
    "POST",
    `/user-requests/${userRequest.id}/business-idea-validation/runs`,
    {
      idempotency_key: idempotencyKey,
      research_intent: true,
      analysis_context_id: confirmed.context_id,
      input_snapshot_hash: confirmed.input_snapshot_hash,
      idea: "Повторная проверка идеи",
    },
  );
  return {
    run_id: run.run_id,
    lineage_reused: run.lineage_reused,
    user_request_id: userRequest.id,
  };
}

export async function waitForLatestRunTerminal(
  page: Page,
  ctx: E2ERunContext,
  projectId: string,
  outcome: E2eDeterministicOutcome,
  timeoutMs = 180_000,
): Promise<LatestRunSummary> {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const latest = await fetchLatestRun(page, ctx, projectId);
    if (latest) {
      if (outcome === "verdict" && latest.status === "succeeded" && latest.has_output) {
        return latest;
      }
      if (
        outcome === "partial" &&
        latest.status === "failed" &&
        latest.result_kind === "partial_research"
      ) {
        return latest;
      }
      if (outcome === "technical" && latest.status === "failed" && !latest.has_output) {
        return latest;
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`latest-run terminal ${outcome} not reached within ${timeoutMs}ms`);
}

export async function assertWorkspaceTerminalUi(
  page: Page,
  outcome: E2eDeterministicOutcome,
  timeoutMs = 120_000,
): Promise<void> {
  await waitForTerminalUi(page, outcome, timeoutMs);
}

export async function resolveBivLifecycleLabel(
  page: Page,
  ctx: E2ERunContext,
  projectId: string,
  projectName?: string,
): Promise<string | null> {
  const latest = await fetchLatestRun(page, ctx, projectId);
  const fromRun = bivLifecycleStatusLabel(latest);
  if (fromRun) {
    return fromRun;
  }
  if (projectName && !projectName.startsWith("Новый проект")) {
    return "Ожидает проверки";
  }
  return null;
}

export async function readRecentProjectLabel(
  page: Page,
  ctx: E2ERunContext,
  projectId: string,
  projectName: string,
): Promise<string | null> {
  const apiLabel = await resolveBivLifecycleLabel(page, ctx, projectId, projectName);
  if (apiLabel) {
    return apiLabel;
  }

  return readRecentProjectDomLabel(page, projectName);
}

/** Commercial Home recent-project row — only rendered when workspace phase is `intake`. */
export async function readRecentProjectDomLabel(
  page: Page,
  projectName: string,
): Promise<string | null> {
  await page.goto("/workspace");
  await expect(page.getByTestId("workspace-home")).toBeVisible({ timeout: 60_000 });
  const list = page
    .getByTestId("home-recent-projects")
    .or(page.getByTestId("home-recent-projects-empty"));
  const visible = await list.isVisible().catch(() => false);
  if (!visible) {
    return null;
  }
  const row = page.getByTestId("home-recent-project").filter({ hasText: projectName });
  if ((await row.count()) === 0) {
    return null;
  }
  const statusSpan = row.first().locator("span.shrink-0");
  return (await statusSpan.textContent())?.trim() ?? null;
}

export async function assertRecentProjectDomLabel(
  page: Page,
  projectName: string,
  expectedLabel: string,
): Promise<void> {
  const domLabel = await readRecentProjectDomLabel(page, projectName);
  expect(domLabel).toBe(expectedLabel);
}

export async function saveScenarioEvidence(
  scenario: string,
  evidence: ScenarioEvidence,
  page?: Page,
): Promise<void> {
  const file = path.join(process.cwd(), ARTIFACT_DIR, `${scenario}.json`);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(
    file,
    JSON.stringify({ saved_at: new Date().toISOString(), ...evidence }, null, 2),
    "utf8",
  );
  if (page) {
    await page.screenshot({
      path: path.join(process.cwd(), ARTIFACT_DIR, `${scenario}.png`),
      fullPage: true,
    });
  }
}

export async function collectScenarioEvidence(
  scenario: string,
  page: Page,
  ctx: E2ERunContext,
  tracker: RunRequestTracker,
  projectId: string,
  options?: {
    runId?: string;
    userRequestId?: string;
    projectName?: string;
  },
): Promise<ScenarioEvidence> {
  const latest = await fetchLatestRun(page, ctx, projectId);
  const runId = options?.runId ?? latest?.run_id;
  const evidence: ScenarioEvidence = {
    scenario,
    project_id: projectId,
    user_request_id: options?.userRequestId ?? latest?.user_request_id,
    run_id: runId,
    post_runs_count: tracker.asyncPosts.length,
    latest_run: latest,
    active_run_count: queryActiveRunCount(projectId),
    progress_state: latest?.progress?.state ?? null,
    has_output: latest?.has_output ?? false,
  };
  if (runId) {
    evidence.investigation = queryInvestigation(runId);
    evidence.run_snapshot = queryRunSnapshot(runId);
  }
  if (options?.projectName) {
    evidence.recent_project_label = await resolveBivLifecycleLabel(
      page,
      ctx,
      projectId,
      options.projectName,
    );
  }
  await saveScenarioEvidence(scenario, evidence, page);
  return evidence;
}

export async function runTerminalRestoreScenario(
  page: Page,
  ctx: E2ERunContext,
  options: {
    scenario: string;
    outcome: E2eDeterministicOutcome;
    projectNameSuffix: string;
    expectedLabel: string;
    newContext?: boolean;
  },
): Promise<ScenarioEvidence> {
  bindDeterministicFixture(ctx.runId, options.outcome);
  const tracker = createRunRequestTracker();
  tracker.attach(page);
  const isolated = await prepareIsolatedProject(page, ctx, options.scenario);
  const idea = `E2E 01G ${options.projectNameSuffix} ${Date.now()}`;
  await confirmIntakeAndStartResearch(page, idea, isolated.projectId);
  await waitForAsyncRunPost(tracker, 120_000);
  const latest = await waitForLatestRunTerminal(page, ctx, isolated.projectId, options.outcome, 180_000);

  if (options.newContext) {
    const fresh = await page.context().browser()?.newContext();
    expect(fresh).toBeTruthy();
    const restored = await fresh!.newPage();
    await restored.addInitScript(() => {
      window.sessionStorage.clear();
      window.localStorage.removeItem("ms_active_biv_research");
      window.localStorage.removeItem("ms_terminal_partial_biv_research");
      window.localStorage.setItem("marketsynth.ui.locale.v1", "ru");
      window.localStorage.setItem("marketsynth.integration.mode.v1", "backend");
    });
    await bivLogin(restored, ctx);
    await openProjectWorkspace(restored, isolated.projectId);
    await waitForTerminalUi(restored, options.outcome, 90_000);
    await restored.close();
    await fresh!.close();
  }

  await openProjectWorkspace(page, isolated.projectId);
  await assertWorkspaceTerminalUi(page, options.outcome, 60_000);

  const evidence = await collectScenarioEvidence(
    options.scenario,
    page,
    ctx,
    tracker,
    isolated.projectId,
    {
      runId: latest.run_id,
      userRequestId: latest.user_request_id,
      projectName: isolated.name,
    },
  );
  expect(evidence.recent_project_label).toBe(options.expectedLabel);
  return evidence;
}

export async function verifyNewBrowserContextTechnicalFailure(
  context: BrowserContext,
  ctx: E2ERunContext,
  projectId: string,
): Promise<void> {
  const restored = await context.browser()?.newContext();
  expect(restored).toBeTruthy();
  const page = await restored!.newPage();
  const tracker = createRunRequestTracker();
  tracker.attach(page);
  await page.addInitScript(() => {
    window.sessionStorage.clear();
    window.localStorage.clear();
    window.localStorage.setItem("marketsynth.ui.locale.v1", "ru");
    window.localStorage.setItem("marketsynth.integration.mode.v1", "backend");
  });
  await bivLogin(page, ctx);
  await openProjectWorkspace(page, projectId);
  await expect(page.getByTestId("biv-research-failed")).toBeVisible({ timeout: 90_000 });
  const failureText = await page.getByTestId("biv-research-failed").innerText();
  expect(failureText.toLowerCase()).not.toMatch(/traceback|stack|api_key|investigation_immutable/);
  await page.waitForTimeout(2_000);
  expect(tracker.asyncPosts.length).toBe(0);
  await page.close();
  await restored!.close();
}

export { openProjectWorkspace };

export { bindDeterministicFixture, clearDeterministicFixture, waitForTerminalUi, waitForAsyncRunPost };
