import * as fs from "node:fs";
import * as path from "node:path";
import { expect, type Page } from "@playwright/test";
import {
  apiJson,
  assertBackendMode,
  loadE2EContext,
  loginViaUi,
  type E2ERunContext,
} from "./cph2";

export type BivArtifact = {
  scenario: string;
  run_id?: string;
  status?: number;
  screenshot?: string;
  trace?: string;
  payload?: Record<string, unknown>;
};

export function loadBivContext(): E2ERunContext & { artifactDir: string } {
  const runId = process.env.BIV_STABILIZATION_RUN_ID || `biv-${Date.now()}`;
  const base = loadE2EContext();
  const artifactDir = path.join(process.cwd(), "test-results", "biv-stabilization", runId);
  fs.mkdirSync(artifactDir, { recursive: true });
  return { ...base, runId, artifactDir };
}

export async function bivLogin(page: Page, ctx: E2ERunContext): Promise<void> {
  await assertBackendMode(page, "backend");
  await page.addInitScript(() => {
    window.localStorage.setItem("marketsynth.ui.locale.v1", "ru");
    window.localStorage.setItem("marketsynth.integration.mode.v1", "backend");
  });
  await loginViaUi(page, ctx);
}

export async function fillMinimalIntake(page: Page, idea: string): Promise<void> {
  await page.goto("/workspace");
  const intentCard = page.getByTestId("intent-card-validate-idea");
  if (await intentCard.isVisible()) {
    await intentCard.click();
  }
  await expect(page.getByTestId("analysis-intake-panel")).toBeVisible({ timeout: 20_000 });

  async function ensureFieldReady(fieldTestId: string, unknownTestId: string): Promise<void> {
    const field = page.getByTestId(fieldTestId);
    if (await field.isDisabled()) {
      await page.getByTestId(unknownTestId).setChecked(false, { force: true });
    }
    await expect(field).toBeEnabled({ timeout: 5_000 });
  }

  await ensureFieldReady("intake-audience", "intake-audience-unknown");
  await ensureFieldReady("intake-geography", "intake-geography-unknown");

  await page.getByTestId("intake-idea-description").fill(idea);
  await page.getByTestId("intake-product").fill(idea);
  await page.getByTestId("intake-audience").fill("Малый бизнес и стартапы");
  await page.getByTestId("intake-geography").fill("Россия, онлайн");
  await page.getByTestId("intake-goal").fill("Проверить коммерческую жизнеспособность");

  await expect(page.getByTestId("intake-product")).toHaveValue(idea);
  await expect(page.getByTestId("intake-confirm-button")).toBeEnabled({ timeout: 10_000 });
}

export async function confirmAndStartResearch(page: Page): Promise<void> {
  const confirm = page.getByTestId("intake-confirm-button");
  await expect(confirm).toBeEnabled({ timeout: 10_000 });
  await confirm.click();
  await expect(page.getByTestId("biv-research-progress")).toBeVisible({ timeout: 30_000 });
}

export async function assertBudgetFieldAutofillSemantics(page: Page): Promise<void> {
  const budget = page.getByTestId("intake-budget");
  await expect(budget).toHaveAttribute("id", "project-budget");
  await expect(budget).toHaveAttribute("name", "project_budget");
  await expect(budget).toHaveAttribute("autocomplete", "off");
  await expect(budget).toHaveAttribute("inputmode", "decimal");
  await expect(budget).not.toHaveAttribute("type", "email");
}

export async function waitForReport(page: Page, timeoutMs = 240_000): Promise<void> {
  await expect(page.getByTestId("business-validation-result-card")).toBeVisible({
    timeout: timeoutMs,
  });
  await expect(page.getByText(/research_idempotency|response\.detail|InvalidStateError/i)).toHaveCount(
    0,
  );
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

export async function exportReport(page: Page): Promise<string> {
  const downloadPromise = page.waitForEvent("download", { timeout: 60_000 });
  await page.getByTestId("agency-action-download").click();
  const download = await downloadPromise;
  const filePath = path.join(process.cwd(), "test-results", download.suggestedFilename());
  await download.saveAs(filePath);
  return fs.readFileSync(filePath, "utf8");
}

export async function getLatestBivRun(
  page: Page,
  ctx: E2ERunContext,
  userRequestId: string,
): Promise<{ run_id: string; status: string; progress?: { progress_percent: number } }> {
  return apiJson(page, ctx, "GET", `/user-requests/${userRequestId}/business-idea-validation`);
}

export async function getBivProgress(
  page: Page,
  ctx: E2ERunContext,
  userRequestId: string,
): Promise<{ progress_percent: number; current_stage: string; state: string }> {
  return apiJson(
    page,
    ctx,
    "GET",
    `/user-requests/${userRequestId}/business-idea-validation/progress`,
  );
}
