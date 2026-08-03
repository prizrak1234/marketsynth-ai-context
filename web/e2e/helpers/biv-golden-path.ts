import * as fs from "node:fs";
import * as path from "node:path";
import { expect, type Page, type Request } from "@playwright/test";
import {
  apiJson,
  assertBackendMode,
  loadE2EContext,
  loginViaUi,
  type E2ERunContext,
} from "./cph2";
import { openProjectWorkspace } from "./biv-e2e-isolation";

export type BivArtifact = {
  scenario: string;
  run_id?: string;
  post_count?: number;
  idempotency_key?: string;
  user_request_id?: string;
  screenshot?: string;
  trace?: string;
  payload?: Record<string, unknown>;
};

export const INTAKE_FIELD_TEST_IDS = [
  "intake-idea-description",
  "intake-product",
  "intake-audience",
  "intake-geography",
  "intake-goal",
  "intake-pricing",
  "intake-competitors",
  "intake-stage",
  "intake-budget",
] as const;

export function loadBivContext(): E2ERunContext & { artifactDir: string } {
  const runId =
    process.env.BIV_STABILIZATION_RUN_ID ||
    process.env.CPH2_RUN_ID ||
    process.env.CPH3_RUN_ID ||
    `biv-${Date.now()}`;
  const base = loadE2EContext();
  const artifactDir = path.join(process.cwd(), "test-results", "biv-golden-path", runId);
  fs.mkdirSync(artifactDir, { recursive: true });
  return { ...base, runId, artifactDir };
}

export type ValidationRunMeta = {
  run_id: string;
  status: string;
  project_id?: string;
  output?: {
    customer_report?: Record<string, unknown> | null;
    run_id?: string | null;
  } | null;
};

export type CustomerReportWaitResult = {
  run_id: string;
  status: string;
  project_id?: string;
  backend_completed_at: string;
  customer_report_ready_at: string;
  ui_hydrated_at: string;
};

export async function bivLogin(page: Page, ctx: E2ERunContext): Promise<void> {
  await assertBackendMode(page, "backend");
  await page.addInitScript(() => {
    window.localStorage.setItem("marketsynth.ui.locale.v1", "ru");
    window.localStorage.setItem("marketsynth.integration.mode.v1", "backend");
  });
  await loginViaUi(page, ctx);
}

/** Open a marked test project workspace (requires prior createIsolatedTestProject). */
export async function prepareFreshBivIntake(
  page: Page,
  ctx: E2ERunContext,
  projectId: string,
): Promise<void> {
  await openProjectWorkspace(page, projectId);
}

export async function openIntakeFromIntent(page: Page): Promise<void> {
  const intake = page.getByTestId("analysis-intake-panel");
  const intentCard = page.getByTestId("intent-card-validate-idea");

  if (await intentCard.isVisible()) {
    await intentCard.click({ timeout: 15_000 });
    await expect(intake).toBeVisible({ timeout: 20_000 });
    return;
  }

  if (await intake.isVisible()) {
    return;
  }

  throw new Error("BIV intake entry not available: no intake panel or validate-idea intent card");
}

async function fillIntakeField(page: Page, fieldTestId: string, value: string): Promise<void> {
  const field = page.getByTestId(fieldTestId);
  for (let attempt = 0; attempt < 5; attempt += 1) {
    await field.click();
    await field.fill("");
    await field.fill(value);
    await field.dispatchEvent("input");
    await field.dispatchEvent("change");
    await field.blur();
    if ((await field.inputValue()) === value) {
      return;
    }
    await page.waitForTimeout(250);
  }
  await expect(field).toHaveValue(value, { timeout: 5_000 });
}

async function ensureIntakeFieldReady(
  page: Page,
  fieldTestId: string,
  unknownTestId: string,
): Promise<void> {
  const field = page.getByTestId(fieldTestId);
  if (await field.isDisabled()) {
    await page.getByTestId(unknownTestId).setChecked(false, { force: true });
  }
  await expect(field).toBeEnabled({ timeout: 5_000 });
}

export async function fillMinimalIntake(
  page: Page,
  idea: string,
  options?: { projectId?: string; ctx?: E2ERunContext },
): Promise<void> {
  if (options?.projectId) {
    await openProjectWorkspace(page, options.projectId);
  } else {
    await page.goto("/workspace");
    await expect(page.getByTestId("workspace-home")).toBeVisible({ timeout: 30_000 });
    await page.waitForLoadState("networkidle");
  }
  await openIntakeFromIntent(page);

  await ensureIntakeFieldReady(page, "intake-audience", "intake-audience-unknown");
  await ensureIntakeFieldReady(page, "intake-geography", "intake-geography-unknown");

  await fillIntakeField(page, "intake-idea-description", idea);
  await fillIntakeField(page, "intake-product", idea);
  await fillIntakeField(page, "intake-audience", "Малый бизнес и стартапы");
  await fillIntakeField(page, "intake-geography", "Россия, онлайн");
  await fillIntakeField(page, "intake-goal", "Проверить коммерческую жизнеспособность");

  const confirm = page.getByTestId("intake-confirm-button");
  if (!(await confirm.isEnabled())) {
    await openProjectWorkspace(page, options!.projectId!);
    await openIntakeFromIntent(page);
    await fillIntakeField(page, "intake-idea-description", idea);
    await fillIntakeField(page, "intake-product", idea);
    await fillIntakeField(page, "intake-audience", "Малый бизнес и стартапы");
    await fillIntakeField(page, "intake-geography", "Россия, онлайн");
    await fillIntakeField(page, "intake-goal", "Проверить коммерческую жизнеспособность");
  }

  await expect(confirm).toBeEnabled({ timeout: 15_000 });
}

export async function assertIntakeAutofillSemantics(page: Page): Promise<void> {
  const forbiddenNames = /email|password|username|login|address/i;
  for (const testId of INTAKE_FIELD_TEST_IDS) {
    const field = page.getByTestId(testId);
    await expect(field).toBeVisible();
    const name = await field.getAttribute("name");
    const autocomplete = await field.getAttribute("autocomplete");
    expect(name).toBeTruthy();
    expect(name).not.toMatch(forbiddenNames);
    expect(autocomplete).toBe("off");
    await expect(field).not.toHaveAttribute("type", "email");
  }
  const budget = page.getByTestId("intake-budget");
  await expect(budget).toHaveAttribute("id", "project-budget");
  await expect(budget).toHaveAttribute("name", "project_budget");
  await expect(budget).toHaveAttribute("inputmode", "decimal");
}

export type RunRequestTracker = {
  posts: Request[];
  asyncPosts: Request[];
  idempotencyKeys: string[];
  attach: (page: Page) => void;
};

export function createRunRequestTracker(): RunRequestTracker {
  const posts: Request[] = [];
  const asyncPosts: Request[] = [];
  const idempotencyKeys: string[] = [];
  return {
    posts,
    asyncPosts,
    idempotencyKeys,
    attach(page: Page) {
      page.on("request", (request) => {
        if (request.method() !== "POST") {
          return;
        }
        const url = request.url();
        if (url.includes("/business-idea-validation/runs")) {
          asyncPosts.push(request);
          try {
            const body = request.postDataJSON() as { idempotency_key?: string } | null;
            if (body?.idempotency_key) {
              idempotencyKeys.push(body.idempotency_key);
            }
          } catch {
            /* non-json body */
          }
          return;
        }
        if (url.includes("/business-idea-validation/run")) {
          posts.push(request);
          try {
            const body = request.postDataJSON() as { idempotency_key?: string } | null;
            if (body?.idempotency_key) {
              idempotencyKeys.push(body.idempotency_key);
            }
          } catch {
            /* non-json body */
          }
        }
      });
    },
  };
}

export async function confirmIntake(page: Page): Promise<void> {
  const confirm = page.getByTestId("intake-confirm-button");
  await expect(confirm).toBeEnabled({ timeout: 10_000 });
  await confirm.click();
  await expect(
    page
      .getByTestId("biv-research-progress")
      .or(page.getByTestId("business-validation-result-card"))
      .or(page.getByTestId("biv-research-failed")),
  ).toBeVisible({ timeout: 60_000 });
}

export async function waitForRunPost(tracker: RunRequestTracker, timeoutMs = 60_000): Promise<void> {
  const started = Date.now();
  while (tracker.asyncPosts.length + tracker.posts.length < 1) {
    if (Date.now() - started > timeoutMs) {
      throw new Error(
        `Expected one run POST within ${timeoutMs}ms, got async=${tracker.asyncPosts.length} sync=${tracker.posts.length}`,
      );
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
}

export async function waitForAsyncRunPost(
  tracker: RunRequestTracker,
  timeoutMs = 60_000,
): Promise<void> {
  const started = Date.now();
  while (tracker.asyncPosts.length < 1) {
    if (Date.now() - started > timeoutMs) {
      throw new Error(`Expected async /runs POST within ${timeoutMs}ms`);
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
}

const DEFAULT_STUB_RUN_ID = "00000000-0000-0000-0000-00000000a002";

/** Stub async POST /runs + poll endpoints for intake golden path E2E. */
export function stubAsyncResearchRun(page: Page, runId = DEFAULT_STUB_RUN_ID): { runId: string } {
  let pollCount = 0;
  let activeRunId = runId;

  page.route(/\/user-requests\/[^/]+\/business-idea-validation/, async (route) => {
    const request = route.request();
    const url = request.url();
    const method = request.method();

    if (method === "POST" && /\/business-idea-validation\/runs$/.test(url)) {
      const userRequestId = url.match(/user-requests\/([^/]+)\/business-idea-validation\/runs/)?.[1];
      let body: Record<string, unknown> = {};
      try {
        body = (request.postDataJSON() as Record<string, unknown> | null) ?? {};
      } catch {
        body = {};
      }
      await route.fulfill({
        status: 202,
        contentType: "application/json",
        body: JSON.stringify({
          run_id: activeRunId,
          user_request_id: userRequestId,
          project_id: "00000000-0000-4000-8000-000000000010",
          analysis_context_id: body.analysis_context_id ?? null,
          input_snapshot_hash: body.input_snapshot_hash ?? null,
          status: "queued",
          created_at: new Date().toISOString(),
          progress: {
            run_id: activeRunId,
            state: "queued",
            current_stage: "normalizing_input",
            completed_stages: [],
            started_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            progress_percent: 0,
            correlation_id: "e2e-stub",
          },
        }),
      });
      return;
    }

    const runIdFromUrl = url.match(/\/runs\/([^/]+)/)?.[1];

    if (method === "GET" && runIdFromUrl && url.includes("/progress")) {
      pollCount += 1;
      const running = pollCount < 4;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          run_id: runIdFromUrl,
          state: running ? "running" : "succeeded",
          current_stage: running ? "searching_direct" : "completed",
          completed_stages: running
            ? ["normalizing_input", "decomposing_queries"]
            : ["normalizing_input", "decomposing_queries", "completed"],
          started_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          progress_percent: running ? 35 : 100,
          correlation_id: "e2e-stub",
        }),
      });
      return;
    }

    if (
      method === "GET" &&
      runIdFromUrl &&
      /\/business-idea-validation\/runs\/[^/]+$/.test(url)
    ) {
      const running = pollCount < 4;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          run_id: runIdFromUrl,
          user_request_id: url.match(/user-requests\/([^/]+)\//)?.[1],
          status: running ? "running" : "succeeded",
          output: running
            ? null
            : {
                run_id: runIdFromUrl,
                research_terminal_state: "succeeded_complete",
                customer_report: null,
              },
        }),
      });
      return;
    }

    if (method === "GET" && /\/business-idea-validation$/.test(url)) {
      await route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ detail: "not found" }),
      });
      return;
    }

    await route.continue();
  });

  return { runId: activeRunId };
}

export function stubTerminalResearchRun(page: Page): void {
  page.route("**/business-idea-validation/run", async (route) => {
    if (route.request().method() !== "POST") {
      await route.continue();
      return;
    }
    const url = route.request().url();
    const userRequestId = url.match(/user-requests\/([^/]+)\/business-idea-validation\/run/)?.[1];
    let body: Record<string, unknown> = {};
    try {
      body = (route.request().postDataJSON() as Record<string, unknown> | null) ?? {};
    } catch {
      body = {};
    }
    const runId = "00000000-0000-0000-0000-00000000a001";
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        run_id: runId,
        user_request_id: userRequestId,
        status: "succeeded",
        output: {
          run_id: runId,
          analysis_context_id: body.analysis_context_id ?? null,
          input_snapshot_hash: body.input_snapshot_hash ?? null,
          research_terminal_state: "succeeded_complete",
          customer_report: null,
        },
      }),
    });
  });
}

export async function waitForRunSucceeded(
  page: Page,
  ctx: E2ERunContext,
  userRequestId: string,
  timeoutMs = 300_000,
): Promise<ValidationRunMeta> {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    try {
      const meta = await getValidationRunMeta(page, ctx, userRequestId);
      if (meta.status === "succeeded" || meta.status === "failed") {
        return meta;
      }
    } catch {
      /* run row not ready yet */
    }
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  throw new Error(`backend_completion_timeout: run ${userRequestId} did not complete within ${timeoutMs}ms`);
}

export async function waitForCustomerReportReady(
  page: Page,
  ctx: E2ERunContext,
  userRequestId: string,
  projectId: string,
  options?: {
    backendTimeoutMs?: number;
    reportTimeoutMs?: number;
    uiTimeoutMs?: number;
  },
): Promise<CustomerReportWaitResult> {
  const backendTimeoutMs = options?.backendTimeoutMs ?? 600_000;
  const reportTimeoutMs = options?.reportTimeoutMs ?? 60_000;
  const uiTimeoutMs = options?.uiTimeoutMs ?? 60_000;

  const completed = await waitForRunSucceeded(page, ctx, userRequestId, backendTimeoutMs);
  if (completed.status !== "succeeded") {
    throw new Error(`backend_completion_failed: status=${completed.status}`);
  }
  const backendCompletedAt = new Date().toISOString();

  const reportStarted = Date.now();
  let reportReadyAt = "";
  let latest = completed;
  while (Date.now() - reportStarted < reportTimeoutMs) {
    latest = await getValidationRunMeta(page, ctx, userRequestId);
    if (latest.output?.customer_report) {
      reportReadyAt = new Date().toISOString();
      break;
    }
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
  if (!reportReadyAt) {
    throw new Error(`report_assembly_timeout: customer_report missing after ${reportTimeoutMs}ms`);
  }

  await openProjectWorkspace(page, projectId);
  const uiStarted = Date.now();
  while (Date.now() - uiStarted < uiTimeoutMs) {
    const hydrated = await page.getByTestId("biv-report-hydrated").isVisible();
    const card = await page.getByTestId("business-validation-result-card").isVisible();
    if (hydrated && card) {
      return {
        run_id: latest.run_id,
        status: latest.status,
        project_id: latest.project_id ?? projectId,
        backend_completed_at: backendCompletedAt,
        customer_report_ready_at: reportReadyAt,
        ui_hydrated_at: new Date().toISOString(),
      };
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`ui_hydration_timeout: report card not visible after ${uiTimeoutMs}ms`);
}

export async function waitForReport(page: Page, timeoutMs = 180_000): Promise<void> {
  await expect(page.getByTestId("biv-report-hydrated")).toBeVisible({ timeout: timeoutMs });
  await expect(page.getByTestId("business-validation-result-card")).toBeVisible({ timeout: 5_000 });
  await expect(page.getByTestId("workspace-home")).toBeVisible();
}

export async function saveScenarioArtifact(
  ctx: E2ERunContext & { artifactDir: string },
  artifact: BivArtifact,
  page: Page,
): Promise<void> {
  const screenshot = path.join(ctx.artifactDir, `${artifact.scenario}.png`);
  await page.screenshot({ path: screenshot, fullPage: true });
  const file = path.join(ctx.artifactDir, `${artifact.scenario}.json`);
  fs.writeFileSync(
    file,
    JSON.stringify({ ...artifact, screenshot, saved_at: new Date().toISOString() }, null, 2),
    "utf8",
  );
}

export async function getValidationRunMeta(
  page: Page,
  ctx: E2ERunContext,
  userRequestId: string,
): Promise<ValidationRunMeta> {
  return apiJson(page, ctx, "GET", `/user-requests/${userRequestId}/business-idea-validation`);
}

export async function getLatestRunMeta(
  page: Page,
  ctx: E2ERunContext,
  userRequestId: string,
): Promise<{ run_id: string; status: string }> {
  const meta = await getValidationRunMeta(page, ctx, userRequestId);
  return { run_id: meta.run_id, status: meta.status };
}

export async function waitForRunMeta(
  page: Page,
  ctx: E2ERunContext,
  userRequestId: string,
  timeoutMs = 90_000,
): Promise<{ run_id: string; status: string }> {
  const started = Date.now();
  let lastError: unknown;
  while (Date.now() - started < timeoutMs) {
    try {
      return await getLatestRunMeta(page, ctx, userRequestId);
    } catch (err) {
      lastError = err;
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
  }
  throw lastError instanceof Error ? lastError : new Error("run meta unavailable");
}

export async function countRunRows(
  page: Page,
  ctx: E2ERunContext,
  userRequestId: string,
): Promise<number> {
  const diag = await apiJson<{ runs?: unknown[] }>(
    page,
    ctx,
    "GET",
    `/user-requests/${userRequestId}/business-idea-validation/diagnostics`,
  );
  if (Array.isArray(diag.runs)) {
    return diag.runs.length;
  }
  return 1;
}

export function captureUserRequestIdFromTracker(tracker: RunRequestTracker): string | undefined {
  const asyncPost = tracker.asyncPosts[0];
  if (asyncPost) {
    return asyncPost.url().match(/\/user-requests\/([^/]+)\/business-idea-validation\/runs/)?.[1];
  }
  const post = tracker.posts[0];
  if (!post) return undefined;
  return post.url().match(/\/user-requests\/([^/]+)\/business-idea-validation\/run/)?.[1];
}

export async function captureUserRequestId(
  page: Page,
  ctx: E2ERunContext,
  tracker?: RunRequestTracker,
): Promise<string | undefined> {
  const fromTracker = tracker ? captureUserRequestIdFromTracker(tracker) : undefined;
  if (fromTracker) return fromTracker;

  const projects = await apiJson<Array<{ id: string }>>(page, ctx, "GET", "/projects");
  for (const project of projects) {
    try {
      const journey = await apiJson<{ user_request_id: string }>(
        page,
        ctx,
        "GET",
        `/projects/${project.id}/launch-pack/journey`,
      );
      if (journey.user_request_id) {
        return journey.user_request_id;
      }
    } catch {
      continue;
    }
  }
  return undefined;
}
