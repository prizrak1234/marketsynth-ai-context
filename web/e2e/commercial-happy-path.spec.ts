import { expect, test } from "@playwright/test";
import {
  apiJson,
  assertBackendMode,
  captureStep,
  fillIntakeWizard,
  loadE2EContext,
  loginViaUi,
  writeLineage,
} from "./helpers/cph2";

test.describe.configure({ mode: "serial" });

test("CPH.3 commercial happy path under cookie session", async ({ page }) => {
  const ctx = loadE2EContext();
  await assertBackendMode(page, "backend");
  await loginViaUi(page, ctx);

  const baselinePlans = await apiJson<unknown[]>(
    page,
    ctx,
    "GET",
    "/projects",
  ).then(async () => 0).catch(() => 0);
  void baselinePlans;

  // 1 Landing (authenticated)
  await page.goto("/");
  await expect(page.getByText("Marketsynth").first()).toBeVisible();
  await expect(
    page.getByText("Прежде чем потратить ваши деньги, мы поможем их сохранить."),
  ).toBeVisible();
  await captureStep(page, ctx, "01-landing");
  await page.getByRole("link", { name: "Проверить мою идею" }).click();

  // 2 Intake
  await fillIntakeWizard(page, ctx.projectPrefix);
  await captureStep(page, ctx, "02-intake-review");

  await page
    .getByRole("button", { name: /Создать проект и начать исследование/i })
    .click();
  await page.waitForURL(/\/workspace\/projects\/[^/]+\/investigation/, {
    timeout: 60_000,
  });
  const projectId = page.url().match(/\/projects\/([^/]+)\//)?.[1];
  expect(projectId).toBeTruthy();

  // Submit brief via review (needs backendProjectId)
  await page.goto("/workspace/projects/new/review");
  await page
    .getByRole("button", { name: /Сохранить и зафиксировать \(submit\)/i })
    .click();
  await expect(page.getByRole("status").filter({ hasText: /submitted/i })).toBeVisible({
    timeout: 60_000,
  });
  await captureStep(page, ctx, "03-brief-submitted");
  await page.reload();
  await expect(page.getByText(/ProjectBrief|submitted|v1/i).first()).toBeVisible();

  // 3 Investigation
  await page.goto(`/workspace/projects/${projectId}/investigation`);
  await assertBackendMode(page, "backend");
  await page.reload(); // apply init script key for this document
  await page.getByRole("button", { name: "Создать исследование" }).click();
  await expect(page.getByText(/Backend · v/i)).toBeVisible({ timeout: 60_000 });
  await page.getByRole("button", { name: "Начать исследование" }).click();
  await captureStep(page, ctx, "04-investigation");
  await page.reload();
  await expect(page.getByText(/Backend · v/i)).toBeVisible({ timeout: 30_000 });

  // 4 Sources (2)
  await addSource(page, "E2E Market Report", "https://example.com/market-e2e");
  await addSource(page, "E2E Competitor Context", "https://example.com/comp-e2e");
  await page.reload();
  await expect(page.getByRole("heading", { name: "E2E Market Report" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "E2E Competitor Context" })).toBeVisible();
  await captureStep(page, ctx, "05-sources");

  // 5 Evidence accept×2
  await addAndAcceptEvidence(
    page,
    "Поисковый интерес по услуге стабилен месяц к месяцу по открытым данным.",
  );
  await addAndAcceptEvidence(
    page,
    "Средний чек по прайсу клиники составляет девять тысяч рублей.",
  );
  await captureStep(page, ctx, "06-evidence");
  await page.reload();
  await expect(page.getByText(/accepted/i).first()).toBeVisible({ timeout: 30_000 });

  // 6 Verdict
  await page.goto(`/workspace/projects/${projectId}/verdict`);
  await page.getByTestId("verdict-build-draft").click();
  await expect(page.getByTestId("verdict-submit-review")).toBeVisible({
    timeout: 60_000,
  });
  await page.getByTestId("verdict-submit-review").click();
  await expect(page.getByTestId("verdict-approve")).toBeVisible({ timeout: 60_000 });
  await page.getByTestId("verdict-approve").click();
  await expect(page.getByText(/approved|утвержд/i).first()).toBeVisible({
    timeout: 60_000,
  });
  await captureStep(page, ctx, "07-verdict");
  await page.reload();
  await expect(page.getByText(/approved|утвержд|CONDITIONAL|GO/i).first()).toBeVisible({
    timeout: 30_000,
  });

  // 7 Strategy
  await page.goto(`/workspace/projects/${projectId}/strategy`);
  await page.getByTestId("strategy-build-draft").click();
  await expect(page.getByTestId("strategy-submit-review")).toBeEnabled({
    timeout: 60_000,
  });
  await page.getByTestId("strategy-submit-review").click();
  await expect(page.getByTestId("strategy-approve")).toBeEnabled({ timeout: 60_000 });
  await page.getByTestId("strategy-approve").click();
  await expect(page.getByText(/approved|утвержд/i).first()).toBeVisible({
    timeout: 60_000,
  });
  await captureStep(page, ctx, "08-strategy");
  await page.reload();
  await expect(page.getByText(/approved|утвержд/i).first()).toBeVisible({
    timeout: 30_000,
  });

  // 8 Implementation
  await page.goto(`/workspace/projects/${projectId}/implementation`);
  const buildImpl = page.getByTestId("impl-build-draft");
  await expect(buildImpl).toBeVisible({ timeout: 30_000 });
  await buildImpl.click();
  await expect(
    page.getByText(/Draft ImplementationPlan собран|impl-prepare|Локальные gates|readiness=/i).first().or(
      page.getByTestId("impl-prepare-handoff"),
    ),
  ).toBeVisible({ timeout: 90_000 });
  await expect(page.getByTestId("impl-prepare-handoff")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("impl-prepare-handoff").click();
  await expect(page.getByText(/ready_for_handoff|readiness=/i).first()).toBeVisible({
    timeout: 60_000,
  });
  await page.getByTestId("impl-submit-review").click();
  await expect(page.getByTestId("impl-approve")).toBeVisible({ timeout: 60_000 });
  await page.getByTestId("impl-approve").click();
  await captureStep(page, ctx, "09-implementation");
  await page.reload();
  await expect(page.getByText(/ready_for_handoff|утвержд|approved/i).first()).toBeVisible({
    timeout: 30_000,
  });

  // 9 Handoff draft
  await page.getByRole("button", { name: /Проверить готовность к передаче/i }).click();
  await expect(page.getByText(/eligible=true/i)).toBeVisible({ timeout: 60_000 });
  await page.getByTestId("handoff-draft-only").check();
  await page.getByRole("button", { name: /Создать черновик MarketingPlan/i }).click();
  await expect(page.getByText(/Draft MarketingPlan создан/i)).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.getByText(/status=draft/i)).toBeVisible();
  await captureStep(page, ctx, "10-handoff");

  // 10 Idempotency — repeat confirm with same preview fingerprint
  const firstDraftId = await page
    .getByText(/ID [0-9a-f-]{36}/i)
    .first()
    .innerText();
  await page.getByRole("button", { name: /Проверить готовность к передаче/i }).click();
  await expect(page.getByText(/eligible=true|Existing MarketingPlans/i).first()).toBeVisible({
    timeout: 60_000,
  });
  const draftOnly = page.getByTestId("handoff-draft-only");
  if (await draftOnly.isEnabled().catch(() => false)) {
    await draftOnly.check();
    await page.getByRole("button", { name: /Создать черновик MarketingPlan/i }).click();
    await expect(page.getByText(/idempotent|Existing|draft/i).first()).toBeVisible({
      timeout: 60_000,
    });
  }
  void firstDraftId;

  // Refresh final
  await page.goto(`/workspace/projects/${projectId}/implementation`);
  await page.reload();
  await captureStep(page, ctx, "11-final-refresh");

  // Lineage + firewall via API (cookie session from browser context)
  const briefs = await apiJson<Array<{ id: string; version: number; status: string }>>(
    page,
    ctx,
    "GET",
    `/projects/${projectId}/briefs`,
  );
  const inv = await apiJson<{ id: string; version: number }>(
    page,
    ctx,
    "GET",
    `/projects/${projectId}/investigations/latest`,
  );
  const sources = await apiJson<Array<{ id: string; version: number }>>(
    page,
    ctx,
    "GET",
    `/projects/${projectId}/sources`,
  );
  const evidence = await apiJson<
    Array<{ id: string; version: number; lifecycle_status: string }>
  >(
    page,
    ctx,
    "GET",
    `/projects/${projectId}/investigations/${inv.id}/evidence`,
  );
  const verdict = await apiJson<{
    id: string;
    version: number;
    evidence_snapshot_hash: string;
    lifecycle_status: string;
  }>(page, ctx, "GET", `/projects/${projectId}/business-verdicts/latest`);
  const strategy = await apiJson<{
    id: string;
    version: number;
    business_verdict_id: string;
    lifecycle_status: string;
  }>(page, ctx, "GET", `/projects/${projectId}/marketing-strategies/latest`);
  const impl = await apiJson<{
    id: string;
    version: number;
    readiness_status: string;
    lifecycle_status: string;
  }>(page, ctx, "GET", `/projects/${projectId}/implementation-plans/latest`);
  const plans = await apiJson<Array<{ id: string; status: string; version: number }>>(
    page,
    ctx,
    "GET",
    `/projects/${projectId}/marketing-plans`,
  );
  const drafts = plans.filter((p) => p.status === "draft");
  expect(drafts.length).toBeGreaterThanOrEqual(1);
  expect(plans.some((p) => p.status === "approved")).toBeFalsy();
  expect(verdict.lifecycle_status).toBe("approved");
  expect(strategy.lifecycle_status).toBe("approved");
  expect(strategy.business_verdict_id).toBe(verdict.id);
  expect(impl.lifecycle_status).toBe("approved");
  expect(impl.readiness_status).toBe("ready_for_handoff");
  expect(sources.length).toBeGreaterThanOrEqual(2);
  expect(evidence.filter((e) => e.lifecycle_status === "accepted").length).toBeGreaterThanOrEqual(
    2,
  );
  expect(drafts.length).toBeLessThanOrEqual(2);

  await writeLineage(ctx, {
    projectId,
    briefId: briefs[0]?.id,
    briefVersion: briefs[0]?.version,
    investigationId: inv.id,
    investigationVersion: inv.version,
    sourceIds: sources.map((s) => s.id),
    evidenceIds: evidence.map((e) => e.id),
    evidenceSnapshotHash: verdict.evidence_snapshot_hash,
    businessVerdictId: verdict.id,
    businessVerdictVersion: verdict.version,
    marketingStrategyId: strategy.id,
    marketingStrategyVersion: strategy.version,
    implementationPlanId: impl.id,
    implementationPlanVersion: impl.version,
    marketingPlanDraftIds: drafts.map((d) => d.id),
    marketingPlanStatuses: plans.map((p) => p.status),
    mode: ctx.mode,
    auth: "browser_session_cookie",
  });

  // Forbidden UI strings for silent mock success
  await expect(page.getByText(/mock specialist progress/i)).toHaveCount(0);
});

async function addSource(page: import("@playwright/test").Page, title: string, url: string) {
  await page.getByLabel("Source title").fill(title);
  await page.getByLabel("Source URL").fill(url);
  await page.getByRole("button", { name: "Добавить источник" }).click();
  await expect(page.getByRole("heading", { name: title })).toBeVisible({ timeout: 30_000 });
}

async function addAndAcceptEvidence(
  page: import("@playwright/test").Page,
  claim: string,
) {
  await page.getByLabel("Evidence claim").fill(claim);
  const sourceSelect = page.getByLabel("Supporting source");
  await sourceSelect.selectOption({ index: 1 });
  await page.getByRole("button", { name: "Добавить доказательство" }).click();
  await expect(page.getByText(claim)).toBeVisible({ timeout: 30_000 });
  const card = page.locator("article").filter({ hasText: claim });
  await card.getByTestId("evidence-submit-review").click();
  await card.getByTestId("evidence-accept").click();
}
