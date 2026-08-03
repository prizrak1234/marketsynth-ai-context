import { expect, test } from "@playwright/test";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import path from "node:path";
import { assertBackendMode } from "./helpers/cph2";

const MASTER = path.resolve(
  __dirname,
  "../public/brand/marketsynth-logo-master.png",
);
const MASTER_SHA =
  "233FC4CCC844A700D4944FC6FA30BBA3017C39A6B5343D4122FD18DEA568DF37";

test("master logo hash unchanged", () => {
  const buf = readFileSync(MASTER);
  const hash = createHash("sha256").update(buf).digest("hex").toUpperCase();
  expect(hash).toBe(MASTER_SHA);
});

test("workspace IA: logo, frozen public nav, canonical entry", async ({ page }) => {
  await assertBackendMode(page, "backend");
  await page.addInitScript(() => {
    window.localStorage.setItem("marketsynth.integration.mode.v1", "backend");
  });

  const email = `e2e.ia.${Date.now()}@marketsynth.local`;
  const password = "e2e-ia-pass-12xx";
  await page.goto("/register");
  await expect(page.getByTestId("register-form")).toBeVisible({ timeout: 20_000 });
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-display-name").fill("IA User");
  await page.getByTestId("register-password").fill(password);
  await page.getByTestId("register-password-confirm").fill(password);
  await page.getByTestId("register-notice").check();
  await page.getByTestId("register-submit").click();
  await page.waitForURL(/\/workspace\/?$/, { timeout: 30_000 });

  await expect(page.getByTestId("home-brand-block").getByTestId("brand-logo-symbol")).toBeVisible();
  await expect(page.getByTestId("nav-workspace-projects")).toBeVisible();
  await expect(page.getByTestId("nav-workspace-assistant")).toHaveCount(0);
  await expect(page.getByText("Product Alpha")).toHaveCount(0);
  await expect(page.getByTestId("canonical-commercial-entry")).toBeVisible();

  await page.getByTestId("nav-workspace-projects").click();
  await expect(page.getByTestId("projects-empty")).toBeVisible({ timeout: 15_000 });

  await page.goto("/workspace/research");
  await page.waitForURL(/\/workspace\/?$/, { timeout: 15_000 });

  await page.goto("/workspace/settings");
  await expect(page.getByTestId("workspace-settings-page")).toBeVisible({ timeout: 20_000 });

  const fav = await page.locator('link[rel="icon"]').count();
  expect(fav).toBeGreaterThan(0);
});
