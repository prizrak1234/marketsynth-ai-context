import { expect, test } from "@playwright/test";

import { assertBackendMode } from "./helpers/cph2";
import {
  cleanupRuntime01fContext,
  loadRuntime01fContext,
  runGoldenPathScenario,
  runPartialRerunScenario,
} from "./helpers/runtime-01f-golden-path";
import { bivLogin } from "./helpers/biv-golden-path";

/**
 * RUNTIME-01F — canonical 7-step golden path (async /runs, real backend + persistence).
 * Legacy sync /run coverage lives in biv-golden-path.spec.ts (legacy regression only).
 */
test.describe("RUNTIME-01F canonical golden path", () => {
  test.describe.configure({ mode: "serial", timeout: 360_000 });

  let ctx: ReturnType<typeof loadRuntime01fContext>;

  test.beforeAll(() => {
    try {
      ctx = loadRuntime01fContext();
    } catch {
      test.skip(true, "blocked_by_missing_e2e_credentials");
    }
  });

  test.afterAll(() => {
    if (!ctx) return;
    cleanupRuntime01fContext(ctx);
  });

  test.beforeEach(async ({ page }) => {
    if (!ctx) return;
    await assertBackendMode(page, "backend");
    await page.addInitScript(() => {
      window.localStorage.setItem("marketsynth.ui.locale.v1", "ru");
      window.localStorage.setItem("marketsynth.integration.mode.v1", "backend");
      window.localStorage.removeItem("marketsynth.home.developer_mode.v1");
    });
    await bivLogin(page, ctx);
  });

  test("A — verdict golden path with refresh and restore", async ({ page }) => {
    const evidence = await runGoldenPathScenario(page, ctx, {
      scenario: "A-verdict",
      outcome: "verdict",
      projectName: `E2E-01F-Verdict-${Date.now()}`,
      verifyRefresh: true,
      verifyRestore: true,
    });
    expect(evidence.syncRunCalls).toBe(0);
    expect(evidence.asyncRunCalls).toBeGreaterThan(0);
    expect(evidence.terminalStatus).toBe("succeeded");
  });

  test("B — partial research golden path with refresh", async ({ page }) => {
    const evidence = await runGoldenPathScenario(page, ctx, {
      scenario: "B-partial",
      outcome: "partial",
      projectName: `E2E-01F-Partial-${Date.now()}`,
      verifyRefresh: true,
    });
    expect(evidence.syncRunCalls).toBe(0);
    expect(evidence.terminalStatus).toBe("failed");
  });

  test("C — technical failure golden path with refresh", async ({ page }) => {
    const evidence = await runGoldenPathScenario(page, ctx, {
      scenario: "C-technical",
      outcome: "technical",
      projectName: `E2E-01F-Technical-${Date.now()}`,
      verifyRefresh: true,
    });
    expect(evidence.syncRunCalls).toBe(0);
    expect(evidence.terminalStatus).toBe("failed");
  });

  test("D — refresh during running resumes same async run", async ({ page }) => {
    const evidence = await runGoldenPathScenario(page, ctx, {
      scenario: "D-refresh-running",
      outcome: "verdict",
      projectName: `E2E-01F-RunningRefresh-${Date.now()}`,
      verifyRunningRefresh: true,
    });
    expect(evidence.syncRunCalls).toBe(0);
    expect(evidence.asyncRunCalls).toBe(1);
  });

  test("E — partial rerun creates new async run via POST /runs", async ({ page }) => {
    await runPartialRerunScenario(page, ctx, `E2E-01F-PartialRerun-${Date.now()}`);
  });

  test("F — cross-tenant project workspace is not readable", async ({ page, browser }) => {
    const ownerEvidence = await runGoldenPathScenario(page, ctx, {
      scenario: "F-cross-tenant-setup",
      outcome: "verdict",
      projectName: `E2E-01F-Tenant-${Date.now()}`,
    });

    const intruder = await browser.newPage();
    const intruderEmail = `e2e.intruder.${Date.now()}@marketsynth.local`;
    const intruderPassword = "e2e-intruder-pass12";
    await intruder.goto("/register");
    await intruder.getByTestId("register-email").fill(intruderEmail);
    await intruder.getByTestId("register-display-name").fill("Intruder");
    await intruder.getByTestId("register-password").fill(intruderPassword);
    await intruder.getByTestId("register-password-confirm").fill(intruderPassword);
    await intruder.getByTestId("register-notice").check();
    await intruder.getByTestId("register-submit").click();
    await intruder.waitForURL(/\/workspace\/?$/, { timeout: 30_000 });

    await intruder.addInitScript(() => {
      window.localStorage.setItem("marketsynth.integration.mode.v1", "backend");
    });

    const latestResp = await intruder.request.get(
      `${process.env.CPH2_API_URL || "http://127.0.0.1:8000"}/projects/${ownerEvidence.projectId}/business-idea-validation/latest`,
    );
    expect([401, 403, 404]).toContain(latestResp.status());

    await intruder.goto(`/workspace?project=${ownerEvidence.projectId}`);
    await expect(intruder.getByTestId("workspace-home")).toBeVisible({ timeout: 30_000 });
    await expect(intruder.getByTestId("business-validation-result-card")).toHaveCount(0);
    await expect(intruder.getByTestId("biv-partial-research-panel")).toHaveCount(0);
    await intruder.close();
  });

  test("G — unauthenticated API access to run is rejected", async ({ request }) => {
    const base = process.env.CPH2_API_URL || "http://127.0.0.1:8000";
    const resp = await request.get(`${base}/projects`);
    expect([401, 403]).toContain(resp.status());
  });
});
