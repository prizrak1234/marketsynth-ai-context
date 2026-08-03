import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { assertBackendMode } from "./helpers/cph2";

const MASTER = path.resolve(
  __dirname,
  "../public/brand/marketsynth-logo-master.png",
);
const MASTER_SHA =
  "233FC4CCC844A700D4944FC6FA30BBA3017C39A6B5343D4122FD18DEA568DF37";
const ASPECT = 1024 / 579;

test("master logo hash unchanged", () => {
  const buf = readFileSync(MASTER);
  const hash = createHash("sha256").update(buf).digest("hex").toUpperCase();
  expect(hash).toBe(MASTER_SHA);
});

test("Home hero logo is brand anchor with one-shot entrance", async ({
  page,
}) => {
  await assertBackendMode(page, "backend");
  await page.addInitScript(() => {
    window.localStorage.setItem("marketsynth.integration.mode.v1", "backend");
  });

  const email = `e2e.logo.${Date.now()}@marketsynth.local`;
  const password = "e2e-logo-pass12";
  await page.goto("/register");
  await page.evaluate(() => {
    window.sessionStorage.removeItem("marketsynth.home.logo-entrance.v1");
  });
  await expect(page.getByTestId("register-form")).toBeVisible({ timeout: 20_000 });
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-display-name").fill("Logo User");
  await page.getByTestId("register-password").fill(password);
  await page.getByTestId("register-password-confirm").fill(password);
  await page.getByTestId("register-notice").check();
  await page.getByTestId("register-submit").click();
  await page.waitForURL(/\/workspace\/?$/, { timeout: 30_000 });

  await expect(page.getByTestId("home-hero")).toBeVisible();
  await expect(page.getByTestId("brand-logo-hero")).toBeVisible();
  await expect(page.getByTestId("brand-logo-hero")).toHaveAttribute(
    "alt",
    "Marketsynth",
  );
  await expect(page.getByText("AI MARKETING AGENCY")).toHaveCount(0);
  await expect(page.getByTestId("home-brand-caption")).toHaveCount(0);

  const logo = page.getByTestId("brand-logo-hero");
  const box = await logo.boundingBox();
  expect(box).toBeTruthy();
  expect(box!.height).toBeGreaterThanOrEqual(170);
  expect(box!.height).toBeLessThanOrEqual(240);
  const ratio = box!.width / box!.height;
  expect(Math.abs(ratio - ASPECT)).toBeLessThan(0.2);

  // One-shot entrance within first second of session
  await expect
    .poll(async () => page.getByTestId("brand-logo-hero-wrap").getAttribute("data-entrance"), {
      timeout: 3_000,
    })
    .toBe("1");

  const anim = await page.evaluate(() => {
    const el = document.querySelector(".ms-logo-hero--enter");
    if (!el) return null;
    const styles = getComputedStyle(el);
    return {
      name: styles.animationName,
      iteration: styles.animationIterationCount,
      duration: styles.animationDuration,
    };
  });
  expect(anim?.name).toContain("ms-logo-enter");
  expect(anim?.iteration).toBe("1");

  // Remount of same session: no second entrance
  await page.reload();
  await expect(page.getByTestId("brand-logo-hero")).toBeVisible();
  await expect(page.getByTestId("brand-logo-hero-wrap")).toHaveAttribute(
    "data-entrance",
    "0",
  );
  await expect(page.getByTestId("brand-logo-gleam")).toHaveCount(0);

  // Sidebar symbol stays compact (desktop aside)
  const symbol = page
    .getByTestId("workspace-nav")
    .getByTestId("brand-logo-symbol");
  await expect(symbol).toBeVisible();
  const symBox = await symbol.boundingBox();
  expect(symBox?.height ?? 0).toBeLessThanOrEqual(36);

  // Mobile: single column, logo still sizable (sidebar collapsed)
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByTestId("workspace-nav-mobile")).toBeVisible();
  await expect(page.getByTestId("workspace-nav")).toBeHidden();
  await expect(page.getByTestId("home-hero")).toBeVisible();

  const mobileBox = await logo.boundingBox();
  expect(mobileBox?.height ?? 0).toBeGreaterThanOrEqual(145);
  expect(mobileBox?.height ?? 0).toBeLessThanOrEqual(200);
});

test("Hero logo respects prefers-reduced-motion", async ({ page }) => {
  await assertBackendMode(page, "backend");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addInitScript(() => {
    window.localStorage.setItem("marketsynth.integration.mode.v1", "backend");
  });

  const email = `e2e.logo.rm.${Date.now()}@marketsynth.local`;
  const password = "e2e-logo-rm-12";
  await page.goto("/register");
  await page.evaluate(() => {
    window.sessionStorage.removeItem("marketsynth.home.logo-entrance.v1");
  });
  await expect(page.getByTestId("register-form")).toBeVisible({ timeout: 20_000 });
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-display-name").fill("RM User");
  await page.getByTestId("register-password").fill(password);
  await page.getByTestId("register-password-confirm").fill(password);
  await page.getByTestId("register-notice").check();
  await page.getByTestId("register-submit").click();
  await page.waitForURL(/\/workspace\/?$/, { timeout: 30_000 });

  await expect(page.getByTestId("brand-logo-hero")).toBeVisible();
  await expect(page.getByTestId("brand-logo-hero-wrap")).toHaveAttribute(
    "data-entrance",
    "0",
  );
  await expect(page.getByTestId("brand-logo-gleam")).toHaveCount(0);
});
