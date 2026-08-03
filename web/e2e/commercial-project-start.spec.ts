import { expect, test, type Page, type Request } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";
import { assertBackendMode } from "./helpers/cph2";

const ARTIFACT_DIR = path.join(
  process.cwd(),
  "e2e-artifacts",
  "commercial-project-start-01",
);
const BACKEND_URL = (
  process.env.CPH2_BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://localhost:8001"
).replace(/\/$/, "");

async function registerCommercialUser(page: Page) {
  const email = `cps.${Date.now()}@marketsynth.local`;
  const password = "e2e-cps-start-pass1";
  await page.goto("/register");
  await expect(page.getByTestId("register-email")).toBeVisible({ timeout: 45_000 });
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-display-name").fill("CPS Start User");
  await page.getByTestId("register-password").fill(password);
  await page.getByTestId("register-password-confirm").fill(password);
  await page.getByTestId("register-notice").check();
  await page.getByTestId("register-submit").click();
  return { email, password };
}

async function createProject(page: Page, name: string): Promise<string> {
  const res = await page.request.fetch(`${BACKEND_URL}/projects`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Origin: process.env.CPH2_FRONTEND_URL || "http://localhost:3000",
    },
    data: { name },
  });
  expect(res.ok(), await res.text()).toBeTruthy();
  return ((await res.json()) as { id: string }).id;
}

async function shot(page: Page, name: string) {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
  await page.screenshot({
    path: path.join(ARTIFACT_DIR, `${name}.png`),
    fullPage: true,
  });
}

test.describe("COMMERCIAL-PROJECT-START-01", () => {
  test("register → create project → login lands on PCC with logo + General + menu", async ({
    page,
  }) => {
    await assertBackendMode(page, "backend");
    const { email, password } = await registerCommercialUser(page);

    // Fresh register with 0 projects → intake (per entry resolver)
    await page.waitForURL(/\/workspace\/projects\/new|\/workspace/, { timeout: 45_000 });
    await shot(page, "01-after-register");

    const projectName = `CPS ${Date.now()}`;
    const projectId = await createProject(page, projectName);

    // Simulate commercial re-entry via login (own account)
    await page.goto("/login");
    await page.getByTestId("login-email").fill(email);
    await page.locator("#login-password").fill(password);
    await page.getByTestId("login-submit").click();

    await expect(page.getByTestId("project-command-center")).toBeVisible({
      timeout: 45_000,
    });
    expect(page.url()).toContain(`project=${projectId}`);
    await expect(page.getByTestId("pcc-brand-logo")).toBeVisible();
    await expect(page.getByTestId("pcc-brand-name")).toContainText(/Marketsynth/i);
    await expect(page.getByTestId("pcc-project-name")).toContainText(projectName);
    await expect(page.getByTestId("project-general-chat")).toBeVisible();
    await expect(page.getByTestId("project-capability-grid")).toBeVisible();
    await expect(page.getByTestId("pcc-capability-project-content_director-text")).toBeVisible();
    await expect(page.getByTestId("pcc-capability-launch-visuals")).toBeVisible();
    await expect(page.getByTestId("pcc-capability-project-strategy")).toBeVisible();
    await expect(page.url()).not.toContain("owner_preview");
    await shot(page, "02-pcc-after-login");
    await shot(page, "03-logo-general-menu");

    const genPosts: Request[] = [];
    page.on("request", (req) => {
      if (req.method() === "POST" && /generate|skills\/runs/i.test(req.url())) {
        genPosts.push(req);
      }
    });
    await page.getByTestId("project-general-quick-text").click();
    await expect(page.getByTestId("project-general-message-assistant").first()).toBeVisible({
      timeout: 30_000,
    });
    expect(genPosts.length).toBe(0);

    await page.goto("/workspace");
    await expect(page.getByTestId("project-command-center")).toBeVisible({
      timeout: 45_000,
    });
    await expect(page.getByText("Проверить мою идею")).toHaveCount(0);
    await expect(page.getByTestId("canonical-commercial-entry")).toHaveCount(0);
    await expect(page.getByTestId("pcc-brand-logo")).toBeVisible();
    await expect(page.getByTestId("project-general-chat")).toBeVisible();
    await expect(page.getByTestId("project-capability-grid")).toBeVisible();
    await shot(page, "04-home-redirects-to-pcc");
  });
});
