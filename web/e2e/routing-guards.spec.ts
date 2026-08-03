import { expect, test } from "@playwright/test";
import { assertBackendMode, loadE2EContext, loginViaUi } from "./helpers/cph2";

test("strategy route without approved verdict is guarded", async ({ page }) => {
  const ctx = loadE2EContext();
  await assertBackendMode(page, "backend");
  await loginViaUi(page, ctx);
  await page.goto("/workspace/projects/00000000-0000-4000-8000-000000000099/strategy");
  await expect(
    page.getByText(/blocked|недоступ|Verdict|Strategy|404|Not found|нет|Mock не подставляется/i).first(),
  ).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(/fake Strategy success/i)).toHaveCount(0);
});

test("implementation route without strategy remains honest", async ({ page }) => {
  const ctx = loadE2EContext();
  await assertBackendMode(page, "backend");
  await loginViaUi(page, ctx);
  await page.goto("/workspace/projects/00000000-0000-4000-8000-000000000099/implementation");
  await expect(
    page.getByText(/Implementation|Plan|handoff|Mock не подставляется|недоступ|blocked/i).first(),
  ).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(/mock specialist progress/i)).toHaveCount(0);
});

test("backend mode does not claim mock success on landing CTA path", async ({ page }) => {
  loadE2EContext();
  await assertBackendMode(page, "backend");
  await page.goto("/");
  await expect(page.getByRole("link", { name: "Проверить мою идею" })).toBeVisible();
  await expect(page.getByText(/Integration: mock/i)).toHaveCount(0);
});
