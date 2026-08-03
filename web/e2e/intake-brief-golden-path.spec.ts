import { expect, test } from "@playwright/test";

import { assertBackendMode } from "./helpers/cph2";

import {

  provisionBivE2eRun,

  cleanupBivE2eRun,

} from "./helpers/biv-e2e-isolation";

import {

  stubAsyncResearchRun,

  waitForAsyncRunPost,

  createRunRequestTracker,

  bivLogin,

  loadBivContext,

} from "./helpers/biv-golden-path";



function minimalIntakeDraft(options?: { staleProjectId?: string }) {

  const now = new Date().toISOString();

  const draftId = `draft_e2e_${Date.now()}`;

  return {

    id: draftId,

    projectBasics: {

      name: "E2E Golden Path SaaS",

      ideaDescription:

        "SaaS для автоматизации отчётности малого бизнеса с подпиской от 990 ₽/мес",

      businessType: "saas",

      projectStage: "validating_demand",

      geography: "Россия, онлайн",

      interfaceLanguage: "ru",

    },

    product: {

      whatIsSold: "Подписка на сервис отчётности для малого бизнеса",

      primaryProblem: "Ручная отчётность отнимает время у предпринимателей",

      valueProposition: "Автоматизация отчётности за 990 ₽/мес",

      price: { mode: "unknown" },

      deliveryModel: "",

      differentiators: "",

      knownLimitations: "",

      priceUnknown: true,

      deliveryUnknown: true,

    },

    market: {

      targetMarket: "Малый бизнес и стартапы",

      geography: "Россия",

      knownCompetitors: "",

      competitorUrls: "",

      marketAssumptions: "",

      demandEvidence: "",

      seasonality: "",

      restrictions: "",

      competitorsUnknown: true,

      demandUnavailable: false,

      marketSizeUnknown: true,

    },

    audience: {

      customerModel: "b2b",

      segments: [{ id: "seg1", label: "Малый бизнес и стартапы", notes: "" }],

      decisionMaker: "",

      buyerUserDistinction: "",

      customerLocation: "",

      expectedPains: "",

      expectedObjections: "",

      currentResearch: "",

    },

    economics: {

      launchBudget: { mode: "unknown" },

      monthlyMarketingBudget: { mode: "unknown" },

      targetRevenue: { mode: "unknown" },

      paybackPeriod: "",

      paybackUnknown: true,

      averageOrderValue: { mode: "unknown" },

      grossMargin: "",

      grossMarginUnknown: true,

      teamSize: "",

      teamSizeUnknown: true,

      internalResources: "",

      launchDeadline: "",

      launchDeadlineUnknown: true,

      criticalConstraints: "",

    },

    materials: { websiteUrl: "", socialProfiles: "", items: [] },

    assumptions: [],

    missingData: [],

    readiness: null,

    currentStep: "review",

    updatedAt: now,

    backendSync: {

      backendProjectId: options?.staleProjectId ?? null,

      backendSyncState: options?.staleProjectId ? "partially_synced" : "local_only",

      backendSyncedAt: options?.staleProjectId ? now : null,

      backendUpdatedAt: options?.staleProjectId ? now : null,

      lastSyncError: options?.staleProjectId

        ? "Проект не найден на backend."

        : null,

      submissionFingerprint: null,

      localDraftVersion: now,

    },

  };

}



test.describe("PRODUCT-01.3B RUNTIME-01B async golden path", () => {

  test.describe.configure({ mode: "serial", timeout: 240_000 });



  let ctx: ReturnType<typeof loadBivContext>;



  test.beforeAll(() => {

    const runId = process.env.BIV_STABILIZATION_RUN_ID || `intake-gp-${Date.now()}`;

    process.env.BIV_STABILIZATION_RUN_ID = runId;

    process.env.CPH3_RUN_ID = runId;

    const provision = provisionBivE2eRun(runId);

    process.env.CPH3_E2E_EMAIL = provision.email;

    process.env.CPH3_E2E_PASSWORD = provision.password ?? "";

    ctx = loadBivContext();

  });



  test.afterAll(() => {

    if (!ctx) return;

    cleanupBivE2eRun(ctx.runId, { dryRun: false });

  });



  test.beforeEach(async ({ page }) => {

    await assertBackendMode(page, "backend");

    await page.addInitScript(() => {

      window.localStorage.setItem("marketsynth.ui.locale.v1", "ru");

      window.localStorage.setItem("marketsynth.integration.mode.v1", "backend");

    });

    await bivLogin(page, ctx);

  });



  test("async intake navigates to workspace before terminal and shows progress", async ({

    page,

  }) => {

    const { runId } = stubAsyncResearchRun(page);

    const tracker = createRunRequestTracker();

    tracker.attach(page);



    const draft = minimalIntakeDraft();

    await page.addInitScript((draftJson: string) => {

      window.localStorage.setItem("marketsynth.product_alpha.intake_draft.v1", draftJson);

    }, JSON.stringify(draft));



    const navigationStarted = Date.now();

    await page.goto("/workspace/projects/new/review");

    await expect(page.getByRole("heading", { name: "Обзор и готовность" })).toBeVisible({

      timeout: 20_000,

    });



    await page.getByTestId("intake-golden-path-submit").click();



    await page.waitForURL(/\/workspace\?project=/, { timeout: 10_000 });

    expect(Date.now() - navigationStarted).toBeLessThan(10_000);



    await expect(page.getByTestId("workspace-home")).toBeVisible({ timeout: 15_000 });

    await expect(page.getByTestId("biv-research-progress")).toBeVisible({ timeout: 15_000 });

    await expect(page.getByTestId("agency-analysis-stages")).toBeVisible({ timeout: 15_000 });



    await waitForAsyncRunPost(tracker);

    expect(tracker.asyncPosts.length).toBeGreaterThanOrEqual(1);

    expect(tracker.posts.length).toBe(0);



    await page.reload();

    await expect(page.getByTestId("workspace-home")).toBeVisible({ timeout: 30_000 });

    await expect(page.getByTestId("biv-research-progress")).toBeVisible({ timeout: 15_000 });



    await expect

      .poll(async () => {

        const sessionRaw = await page.evaluate(() =>

          window.sessionStorage.getItem("ms_active_biv_research"),

        );

        if (!sessionRaw) return null;

        const session = JSON.parse(sessionRaw) as { runId?: string };

        return session.runId ?? null;

      })

      .toBe(runId);

  });



  test("stale backendProjectId recovers and uses async /runs", async ({ page }) => {

    stubAsyncResearchRun(page);

    const tracker = createRunRequestTracker();

    tracker.attach(page);



    const staleId = "00000000-0000-4000-8000-000000000099";

    const draft = minimalIntakeDraft({ staleProjectId: staleId });

    await page.addInitScript((draftJson: string) => {

      window.localStorage.setItem("marketsynth.product_alpha.intake_draft.v1", draftJson);

    }, JSON.stringify(draft));



    await page.goto("/workspace/projects/new/review");

    await page.getByTestId("intake-golden-path-submit").click();



    await page.waitForURL(/\/workspace\?project=/, { timeout: 10_000 });

    await expect(page.getByText("Проект не найден")).toHaveCount(0);



    const projectId = new URL(page.url()).searchParams.get("project");

    expect(projectId).toBeTruthy();

    expect(projectId).not.toBe(staleId);



    await waitForAsyncRunPost(tracker);

  });

});

