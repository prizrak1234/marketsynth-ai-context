import { expect, test, type Page } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";
import { assertBackendMode } from "./helpers/cph2";

/**
 * DETERMINISTIC E2E ONLY — proves UI wiring + cold restore against fixture PNGs.
 * Requires API started with CONTENT_DIRECTOR_IMAGE_DETERMINISTIC=true.
 * Does NOT prove live openai_images commercial spend/path.
 */
const ARTIFACT_DIR = path.join(process.cwd(), "e2e-artifacts", "content-director-image");
const BACKEND_URL = (
  process.env.CPH2_BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://127.0.0.1:8001"
).replace(/\/$/, "");

async function assertDeterministicImageApi() {
  const health = await fetch(`${BACKEND_URL}/health`).catch(() => null);
  expect(health?.ok, `API must be up at ${BACKEND_URL}`).toBeTruthy();
  const flag = (process.env.CONTENT_DIRECTOR_IMAGE_DETERMINISTIC || "").toLowerCase();
  expect(
    flag === "true" || flag === "1" || process.env.CD_IMAGE_E2E_ALLOW_LIVE === "1",
    "Set CONTENT_DIRECTOR_IMAGE_DETERMINISTIC=true for this E2E (fixture PNG path). " +
      "Do not treat PASS as live openai_images proof. Set CD_IMAGE_E2E_ALLOW_LIVE=1 only for paid smoke.",
  ).toBeTruthy();
}

async function registerCommercialUser(page: Page, prefix: string) {
  const email = `${prefix}.${Date.now()}@marketsynth.local`;
  const password = "e2e-cd-image-pass1";
  await page.goto("/register");
  await expect(page.getByTestId("register-email")).toBeVisible({ timeout: 45_000 });
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-display-name").fill("Content Director Image User");
  await page.getByTestId("register-password").fill(password);
  await page.getByTestId("register-password-confirm").fill(password);
  await page.getByTestId("register-notice").check();
  await page.getByTestId("register-submit").click();
  await page.waitForURL(/\/workspace(\/projects\/new|\/?(\?|$))/, { timeout: 45_000 });
  return { email, password };
}

async function createProject(page: Page): Promise<string> {
  const res = await page.request.fetch(`${BACKEND_URL}/projects`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Origin: process.env.CPH2_FRONTEND_URL || "http://localhost:3000",
    },
    data: { name: `CD Image GP ${Date.now()}` },
  });
  expect(res.ok(), await res.text()).toBeTruthy();
  const body = (await res.json()) as { id: string };
  return body.id;
}

async function shot(page: Page, name: string) {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
  await page.screenshot({
    path: path.join(ARTIFACT_DIR, `${name}.png`),
    fullPage: true,
  });
}

test.describe("Content Director image golden path (deterministic)", () => {
  test("A–O create → generate → approve → cold restore", async ({ page }) => {
    await assertBackendMode(page, "backend");
    await assertDeterministicImageApi();
    await registerCommercialUser(page, "cd.image");
    const projectId = await createProject(page);

    await page.goto(
      `/workspace?project=${encodeURIComponent(projectId)}&view=content_director`,
    );
    await expect(page.getByTestId("content-director-panel")).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.getByTestId("content-director-panel")).not.toContainText(
      "owner_preview",
    );
    await expect(page.url()).not.toContain("owner_preview");

    await page.getByTestId("content-director-mode-image").click();
    await expect(page.getByTestId("visual-director-panel")).toBeVisible();
    await shot(page, "01-empty-image-form");

    await page.getByTestId("visual-director-field-title").fill("Launch visual");
    await page.getByTestId("visual-director-field-objective").fill("Announce product");
    await page
      .getByTestId("visual-director-field-scene_description")
      .fill("Founder with laptop at bright desk");
    await page.getByTestId("visual-director-field-subject").fill("Laptop");
    await page.getByTestId("visual-director-field-audience").fill("Founders");
    await page.getByTestId("visual-director-save").click();
    await expect(page.getByTestId("visual-director-error")).toHaveCount(0);
    await shot(page, "02-request-saved");

    await page.getByTestId("visual-director-generate").click();
    await expect(page.getByTestId("visual-director-candidates")).toBeVisible({
      timeout: 90_000,
    });
    const candidateLocator = page.locator("[data-testid^=visual-director-candidate-]");
    const firstCount = await candidateLocator.count();
    await page.getByTestId("visual-director-generate").click({ force: true }).catch(() => {});
    await page.waitForTimeout(500);
    expect(await candidateLocator.count()).toBe(firstCount);
    await expect(page.getByTestId("visual-director-error")).toHaveCount(0);
    await shot(page, "03-candidates");

    await page.reload();
    await page.getByTestId("content-director-mode-image").click();
    await expect(page.getByTestId("visual-director-candidates")).toBeVisible({
      timeout: 30_000,
    });
    await shot(page, "04-after-refresh");

    await page.getByTestId("visual-director-candidate-1").click();
    await expect(page.getByTestId("visual-director-preview")).toBeVisible({
      timeout: 30_000,
    });
    await page.getByTestId("visual-director-approve").click();
    await expect(page.getByTestId("visual-director-approved")).toBeVisible({
      timeout: 30_000,
    });
    await shot(page, "05-approved");

    await page.reload();
    await page.getByTestId("content-director-mode-image").click();
    await expect(page.getByTestId("visual-director-approved")).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.getByTestId("visual-director-preview")).toBeVisible();
    await expect(page.getByTestId("content-director-panel")).not.toContainText(
      "stack trace",
    );
    await shot(page, "06-cold-restore");
  });
});
