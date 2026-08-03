import * as fs from "node:fs";
import * as path from "node:path";
import { execSync } from "node:child_process";
import { expect, type BrowserContext, type Page } from "@playwright/test";

import { apiJson, fillIntakeWizard, type E2ERunContext } from "./cph2";
import {
  appendIsolationLog,
  cleanupBivE2eRun,
  openProjectWorkspace,
  provisionBivE2eRun,
} from "./biv-e2e-isolation";
import {
  bivLogin,
  createRunRequestTracker,
  loadBivContext,
  saveScenarioArtifact,
  waitForAsyncRunPost,
  type BivArtifact,
  type RunRequestTracker,
} from "./biv-golden-path";

export type E2eDeterministicOutcome = "verdict" | "partial" | "technical";

export type GoldenPathSession = {
  projectId: string;
  userRequestId: string;
  runId: string;
};

export type GoldenPathEvidence = {
  scenario: string;
  outcome: E2eDeterministicOutcome;
  projectId: string;
  userRequestId: string;
  runId: string;
  terminalStatus: string;
  endpoints: string[];
  syncRunCalls: number;
  asyncRunCalls: number;
  refreshVerified: boolean;
  restoreVerified: boolean;
  durationMs: number;
};

export function loadRuntime01fContext(): E2ERunContext & { artifactDir: string } {
  const runId =
    process.env.RUNTIME_01F_RUN_ID ||
    process.env.BIV_STABILIZATION_RUN_ID ||
    `runtime-01f-${Date.now()}`;
  process.env.RUNTIME_01F_RUN_ID = runId;
  process.env.BIV_STABILIZATION_RUN_ID = runId;
  process.env.CPH3_RUN_ID = runId;
  const provision = provisionBivE2eRun(runId);
  process.env.CPH3_E2E_EMAIL = provision.email;
  process.env.CPH3_E2E_PASSWORD = provision.password ?? "";
  const ctx = loadBivContext();
  appendIsolationLog(ctx.artifactDir, provision);
  return ctx;
}

export function cleanupRuntime01fContext(ctx: E2ERunContext & { artifactDir: string }): void {
  clearDeterministicFixture(ctx.runId);
  const cleanup = cleanupBivE2eRun(ctx.runId, { dryRun: false });
  appendIsolationLog(ctx.artifactDir, cleanup);
}

function repoRootFromWeb(): string {
  return path.join(process.cwd(), "..");
}

/** Bind server-side deterministic outcome before canonical POST /runs (no request mutation). */
export function bindDeterministicFixture(runId: string, outcome: E2eDeterministicOutcome): void {
  const repoRoot = repoRootFromWeb();
  execSync(
    `uv run python scripts/e2e_biv_set_fixture.py bind --run-id ${JSON.stringify(runId)} --outcome ${JSON.stringify(outcome)}`,
    {
      cwd: repoRoot,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
      env: {
        ...process.env,
        APP_ENV: "development",
        BIV_E2E_DETERMINISTIC_ENABLED: "true",
      },
    },
  );
}

export function clearDeterministicFixture(runId: string): void {
  const repoRoot = repoRootFromWeb();
  try {
    execSync(`uv run python scripts/e2e_biv_set_fixture.py clear --run-id ${JSON.stringify(runId)}`, {
      cwd: repoRoot,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
      env: {
        ...process.env,
        APP_ENV: "development",
        BIV_E2E_DETERMINISTIC_ENABLED: "true",
      },
    });
  } catch {
    // Best-effort cleanup when fixture was already cleared after terminal persistence.
  }
}

export function captureAsyncUserRequestId(tracker: RunRequestTracker): string | undefined {
  const post = tracker.asyncPosts[0];
  if (!post) return undefined;
  return post.url().match(/\/user-requests\/([^/]+)\/business-idea-validation\/runs/)?.[1];
}

export async function startCanonicalGoldenPathFromLanding(
  page: Page,
  ctx: E2ERunContext,
  projectName: string,
): Promise<void> {
  await page.goto("/");
  const cta = page.getByTestId("public-landing-cta");
  await expect(cta).toBeVisible();
  // Landing CTA uses login?next= for anonymous users (RUNTIME-01E). Authenticated E2E continues to intake.
  await page.goto("/workspace/projects/new");
  await page.waitForURL(/\/workspace\/projects\/new/, { timeout: 30_000 });
  await fillIntakeWizard(page, projectName);
}

export async function submitSevenStepIntake(page: Page): Promise<void> {
  await expect(page.getByTestId("intake-golden-path-submit")).toBeEnabled({ timeout: 30_000 });
  await page.getByTestId("intake-golden-path-submit").click();
  await page.waitForURL(/\/workspace\?project=/, { timeout: 60_000 });
}

export async function waitForTerminalUi(
  page: Page,
  outcome: E2eDeterministicOutcome,
  timeoutMs = 120_000,
): Promise<void> {
  if (outcome === "verdict") {
    await expect(page.getByTestId("business-validation-result-card")).toBeVisible({ timeout: timeoutMs });
    await expect(page.getByTestId("biv-report-hydrated")).toBeVisible({ timeout: 5_000 });
    await expect(page.getByTestId("biv-partial-research-panel")).toHaveCount(0);
    await expect(page.getByTestId("biv-research-failed")).toHaveCount(0);
    await expect(page.getByTestId("biv-research-progress")).toHaveCount(0);
    return;
  }
  if (outcome === "partial") {
    await expect(page.getByTestId("biv-partial-research-panel")).toBeVisible({ timeout: timeoutMs });
    await expect(page.getByTestId("biv-partial-stop-reason")).toBeVisible({ timeout: 5_000 });
    const findings = page.getByTestId("biv-partial-findings");
    const gaps = page.getByTestId("biv-partial-gaps");
    await expect(findings).toBeVisible({ timeout: 5_000 });
    await expect(gaps).toBeVisible({ timeout: 5_000 });
    await expect(page.getByTestId("business-validation-result-card")).toHaveCount(0);
    await expect(page.getByTestId("biv-research-failed")).toHaveCount(0);
    await expect(page.getByTestId("biv-research-progress")).toHaveCount(0);
    return;
  }
  await expect(page.getByTestId("biv-research-failed")).toBeVisible({ timeout: timeoutMs });
  await expect(page.getByTestId("biv-partial-research-panel")).toHaveCount(0);
  await expect(page.getByTestId("business-validation-result-card")).toHaveCount(0);
  // Technical failure panel is rendered inside the progress shell (see ResearchFailurePanel).
  await expect(page.getByTestId("biv-research-progress")).toBeVisible();
  await expect(page.getByTestId("biv-research-failed")).toBeVisible();
  const failureText = await page.getByTestId("biv-research-failed").innerText();
  expect(failureText.toLowerCase()).not.toMatch(/traceback|api_key|secret|password/);
}

export async function fetchGoldenPathSession(
  page: Page,
  ctx: E2ERunContext,
  tracker: RunRequestTracker,
): Promise<GoldenPathSession> {
  const projectId = new URL(page.url()).searchParams.get("project");
  expect(projectId).toBeTruthy();
  const userRequestId = captureAsyncUserRequestId(tracker);
  expect(userRequestId).toBeTruthy();

  const latest = await apiJson<{ run_id: string; status: string }>(
    page,
    ctx,
    "GET",
    `/user-requests/${userRequestId}/business-idea-validation`,
  );
  expect(latest.run_id).toBeTruthy();

  return {
    projectId: projectId!,
    userRequestId: userRequestId!,
    runId: latest.run_id,
  };
}

export async function assertBackendTerminal(
  page: Page,
  ctx: E2ERunContext,
  session: GoldenPathSession,
  outcome: E2eDeterministicOutcome,
): Promise<string> {
  const run = await apiJson<{
    status: string;
    output?: {
      result_kind?: string | null;
      customer_report?: unknown | null;
      commercial_verdict?: unknown | null;
      business_verdict_id?: string | null;
      research_terminal_state?: string | null;
    } | null;
    error_code?: string | null;
  }>(
    page,
    ctx,
    "GET",
    `/user-requests/${session.userRequestId}/business-idea-validation/runs/${session.runId}`,
  );

  if (outcome === "verdict") {
    expect(run.status).toBe("succeeded");
    expect(run.output?.result_kind).not.toBe("partial_research");
    expect(run.output?.customer_report).toBeTruthy();
    expect(run.output?.business_verdict_id ?? run.output?.commercial_verdict).toBeTruthy();
    return run.status;
  }
  if (outcome === "partial") {
    expect(run.status).toBe("failed");
    expect(run.error_code).toBe("high_impact_insufficient_sources");
    expect(run.output?.result_kind).toBe("partial_research");
    expect(run.output?.research_terminal_state).toBe("succeeded_insufficient");
    expect(run.output?.customer_report).toBeNull();
    expect(run.output?.commercial_verdict).toBeNull();
    return run.status;
  }
  expect(run.status).toBe("failed");
  expect(run.output).toBeNull();
  expect(run.error_code).toBe("pipeline_fetch_failed");
  return run.status;
}

export async function verifyRefreshPreservesTerminal(
  page: Page,
  ctx: E2ERunContext,
  session: GoldenPathSession,
  outcome: E2eDeterministicOutcome,
): Promise<void> {
  await page.reload();
  await openProjectWorkspace(page, session.projectId);
  await waitForTerminalUi(page, outcome);
  await assertBackendTerminal(page, ctx, session, outcome);
}

export async function verifyNewBrowserContextRestore(
  context: BrowserContext,
  ctx: E2ERunContext,
  session: GoldenPathSession,
  outcome: E2eDeterministicOutcome,
): Promise<void> {
  const restored = await context.newPage();
  await restored.addInitScript(() => {
    window.localStorage.removeItem("ms_terminal_partial_biv_research");
    window.sessionStorage.removeItem("ms_active_biv_research");
    window.localStorage.setItem("marketsynth.ui.locale.v1", "ru");
    window.localStorage.setItem("marketsynth.integration.mode.v1", "backend");
  });
  await bivLogin(restored, ctx);
  await openProjectWorkspace(restored, session.projectId);
  await waitForTerminalUi(restored, outcome);
  await restored.close();
}

export function assertNoSyncRunCalls(tracker: RunRequestTracker): void {
  expect(tracker.posts.length).toBe(0);
  expect(tracker.asyncPosts.length).toBeGreaterThan(0);
}

export async function saveGoldenPathEvidence(
  ctx: E2ERunContext & { artifactDir: string },
  page: Page,
  evidence: GoldenPathEvidence,
): Promise<void> {
  fs.mkdirSync(ctx.artifactDir, { recursive: true });
  const artifact: BivArtifact = {
    scenario: evidence.scenario,
    run_id: evidence.runId,
    user_request_id: evidence.userRequestId,
    payload: evidence as unknown as Record<string, unknown>,
  };
  await saveScenarioArtifact(ctx, artifact, page);
}

export async function runGoldenPathScenario(
  page: Page,
  ctx: E2ERunContext & { artifactDir: string },
  options: {
    scenario: string;
    outcome: E2eDeterministicOutcome;
    projectName: string;
    verifyRefresh?: boolean;
    verifyRestore?: boolean;
    verifyRunningRefresh?: boolean;
  },
): Promise<GoldenPathEvidence> {
  const started = Date.now();
  const tracker = createRunRequestTracker();
  tracker.attach(page);
  bindDeterministicFixture(ctx.runId, options.outcome);

  await startCanonicalGoldenPathFromLanding(page, ctx, options.projectName);
  await submitSevenStepIntake(page);
  await waitForAsyncRunPost(tracker, 120_000);
  assertNoSyncRunCalls(tracker);

  if (options.verifyRunningRefresh) {
    await expect(page.getByTestId("biv-research-progress")).toBeVisible({ timeout: 30_000 });
    const sessionDuring = await fetchGoldenPathSession(page, ctx, tracker);
    const postsBefore = tracker.asyncPosts.length;
    await page.reload();
    await expect(page.getByTestId("workspace-home")).toBeVisible({ timeout: 60_000 });
    expect(tracker.asyncPosts.length).toBe(postsBefore);
    await waitForTerminalUi(page, options.outcome);
    const terminalStatus = await assertBackendTerminal(page, ctx, sessionDuring, options.outcome);
    const evidence: GoldenPathEvidence = {
      scenario: options.scenario,
      outcome: options.outcome,
      projectId: sessionDuring.projectId,
      userRequestId: sessionDuring.userRequestId,
      runId: sessionDuring.runId,
      terminalStatus,
      endpoints: [
        "POST /user-requests/{id}/business-idea-validation/runs",
        "GET /user-requests/{id}/business-idea-validation/runs/{run_id}/progress",
        "GET /user-requests/{id}/business-idea-validation/runs/{run_id}",
        "GET /projects/{id}/business-idea-validation/latest",
      ],
      syncRunCalls: tracker.posts.length,
      asyncRunCalls: tracker.asyncPosts.length,
      refreshVerified: true,
      restoreVerified: false,
      durationMs: Date.now() - started,
    };
    await saveGoldenPathEvidence(ctx, page, evidence);
    return evidence;
  }

  await waitForTerminalUi(page, options.outcome);
  const session = await fetchGoldenPathSession(page, ctx, tracker);
  const terminalStatus = await assertBackendTerminal(page, ctx, session, options.outcome);

  let refreshVerified = false;
  if (options.verifyRefresh) {
    await verifyRefreshPreservesTerminal(page, ctx, session, options.outcome);
    refreshVerified = true;
  }

  let restoreVerified = false;
  if (options.verifyRestore) {
    await verifyNewBrowserContextRestore(page.context(), ctx, session, options.outcome);
    restoreVerified = true;
  }

  const evidence: GoldenPathEvidence = {
    scenario: options.scenario,
    outcome: options.outcome,
    projectId: session.projectId,
    userRequestId: session.userRequestId,
    runId: session.runId,
    terminalStatus,
    endpoints: [
      "POST /user-requests/{id}/business-idea-validation/runs",
      "GET /user-requests/{id}/business-idea-validation/runs/{run_id}/progress",
      "GET /user-requests/{id}/business-idea-validation/runs/{run_id}",
      "GET /projects/{id}/business-idea-validation/latest",
    ],
    syncRunCalls: tracker.posts.length,
    asyncRunCalls: tracker.asyncPosts.length,
    refreshVerified,
    restoreVerified,
    durationMs: Date.now() - started,
  };
  await saveGoldenPathEvidence(ctx, page, evidence);
  return evidence;
}

export async function runPartialRerunScenario(
  page: Page,
  ctx: E2ERunContext & { artifactDir: string },
  projectName: string,
): Promise<void> {
  const tracker = createRunRequestTracker();
  tracker.attach(page);
  bindDeterministicFixture(ctx.runId, "partial");

  await startCanonicalGoldenPathFromLanding(page, ctx, projectName);
  await submitSevenStepIntake(page);
  await waitForAsyncRunPost(tracker, 120_000);
  await waitForTerminalUi(page, "partial");
  const session = await fetchGoldenPathSession(page, ctx, tracker);
  const postsBefore = tracker.asyncPosts.length;

  bindDeterministicFixture(ctx.runId, "verdict");
  await page.getByTestId("biv-partial-rerun").click();
  await waitForAsyncRunPost(tracker, 120_000);
  expect(tracker.asyncPosts.length).toBe(postsBefore + 1);
  assertNoSyncRunCalls(tracker);
  await waitForTerminalUi(page, "verdict");

  const latest = await apiJson<{ run_id: string; status: string }>(
    page,
    ctx,
    "GET",
    `/user-requests/${session.userRequestId}/business-idea-validation`,
  );
  expect(latest.run_id).not.toBe(session.runId);
  expect(latest.status).toBe("succeeded");
}
