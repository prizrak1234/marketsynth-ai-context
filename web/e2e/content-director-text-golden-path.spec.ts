import { expect, test, type Page } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";
import { assertBackendMode } from "./helpers/cph2";

const ARTIFACT_DIR = path.join(process.cwd(), "e2e-artifacts", "content-director");
const BACKEND_URL = (
  process.env.CPH2_BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://localhost:8000"
).replace(/\/$/, "");

async function registerCommercialUser(page: Page, prefix: string) {
  const email = `${prefix}.${Date.now()}@marketsynth.local`;
  const password = "e2e-cd-text-pass1";
  await page.goto("/register");
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-display-name").fill("Content Director User");
  await page.getByTestId("register-password").fill(password);
  await page.getByTestId("register-password-confirm").fill(password);
  await page.getByTestId("register-notice").check();
  await page.getByTestId("register-submit").click();
  await page.waitForURL(/\/workspace(\/projects\/new|\/?(\?|$))/, { timeout: 30_000 });
  return { email, password };
}

async function createProject(page: Page): Promise<string> {
  const res = await page.request.fetch(`${BACKEND_URL}/projects`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Origin: process.env.CPH2_FRONTEND_URL || "http://localhost:3000",
    },
    data: { name: `CD Text GP ${Date.now()}` },
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

test.describe("Content Director text golden path", () => {
  test("A–N create → generate → edit → approve → cold restore", async ({ page }) => {
    await assertBackendMode(page, "backend");
    await registerCommercialUser(page, "cd.text");
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
    await page.getByTestId("content-director-mode-text").click();
    await expect(page.getByTestId("content-director-text-panel")).toBeVisible();
    await shot(page, "01-empty-form");

    await page.getByTestId("content-director-field-title").fill("Telegram launch");
    await page.getByTestId("content-director-field-objective").fill("Announce product");
    await page
      .getByTestId("content-director-field-audience_description")
      .fill("Founders");
    await page.getByTestId("content-director-field-key_message").fill("Ship faster");
    await page.getByTestId("content-director-field-cta").fill("Try now");
    await page.getByTestId("content-director-save").click();
    await expect(page.getByTestId("content-director-error")).toHaveCount(0);
    await shot(page, "02-request-saved");

    await page.getByTestId("content-director-generate").click();
    await expect(page.getByTestId("content-director-candidates")).toBeVisible({
      timeout: 60_000,
    });
    await expect(page.getByTestId("content-director-candidate-1")).toBeVisible();
    await shot(page, "03-candidates");

    await page.getByTestId("content-director-candidate-1").click();
    await page.getByTestId("content-director-editor").fill("Edited cold-restore body");
    await page.getByTestId("content-director-save-edit").click();
    await page.getByTestId("content-director-approve").click();
    await expect(page.getByTestId("content-director-approved")).toBeVisible({
      timeout: 30_000,
    });
    await shot(page, "04-approved");

    await page.reload();
    await expect(page.getByTestId("content-director-panel")).toBeVisible({
      timeout: 30_000,
    });
    await page.getByTestId("content-director-mode-text").click();
    await expect(page.getByTestId("content-director-approved")).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.getByTestId("content-director-editor")).toHaveValue(
      /Edited cold-restore body/,
    );
    await expect(page.url()).not.toContain("owner_preview");
    await shot(page, "05-cold-restore");
  });
});
