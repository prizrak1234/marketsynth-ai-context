import * as fs from "node:fs";
import * as path from "node:path";
import { expect, type Page } from "@playwright/test";

function resolveArtifactDir(): string {
  if (process.env.CPH2_COMMERCIAL_UX_ARTIFACT_DIR?.trim()) {
    return process.env.CPH2_COMMERCIAL_UX_ARTIFACT_DIR.trim();
  }
  return path.resolve(process.cwd(), "test-results", "commercial-ux-a-d-verification");
}

export const COMMERCIAL_UX_ARTIFACT_DIR = resolveArtifactDir();

export const VIEWPORTS = {
  desktop: { width: 1440, height: 900, label: "1440x900" },
  laptop: { width: 1280, height: 800, label: "1280x800" },
  tablet: { width: 768, height: 1024, label: "768x1024" },
  mobile: { width: 390, height: 844, label: "390x844" },
} as const;

export type ViewportKey = keyof typeof VIEWPORTS;

export function ensureArtifactDir(): void {
  fs.mkdirSync(COMMERCIAL_UX_ARTIFACT_DIR, { recursive: true });
}

export function screenshotPath(name: string): string {
  return path.join(COMMERCIAL_UX_ARTIFACT_DIR, `${name}.png`);
}

export async function setViewport(
  page: Page,
  key: ViewportKey,
): Promise<void> {
  const vp = VIEWPORTS[key];
  await page.setViewportSize({ width: vp.width, height: vp.height });
}

export async function captureScreenshot(page: Page, name: string): Promise<string> {
  ensureArtifactDir();
  const filePath = screenshotPath(name);
  await page.screenshot({ path: filePath, fullPage: true });
  expect(fs.existsSync(filePath), `screenshot missing at ${filePath}`).toBeTruthy();
  return filePath;
}

export function attachConsoleCollector(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") {
      errors.push(msg.text());
    }
  });
  page.on("pageerror", (err) => {
    errors.push(err.message);
  });
  return errors;
}

export async function assertLayoutHealthy(page: Page): Promise<void> {
  const metrics = await page.evaluate(() => {
    const doc = document.documentElement;
    return {
      scrollWidth: doc.scrollWidth,
      clientWidth: doc.clientWidth,
    };
  });
  expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.clientWidth + 2);
}

export async function assertNoHydrationErrors(consoleErrors: string[]): Promise<void> {
  const hydration = consoleErrors.filter(
    (line) =>
      /hydration/i.test(line) ||
      /did not match/i.test(line) ||
      /Text content does not match/i.test(line),
  );
  expect(hydration, hydration.join("\n")).toHaveLength(0);
}

export async function openMobileNavIfNeeded(page: Page): Promise<void> {
  const drawer = page.getByTestId("workspace-nav-drawer");
  if (await drawer.isVisible()) {
    return;
  }
  const menu = page.getByTestId("workspace-nav-menu");
  if (await menu.isVisible()) {
    await menu.click();
    await expect(drawer).toBeVisible({ timeout: 5_000 });
  }
}
