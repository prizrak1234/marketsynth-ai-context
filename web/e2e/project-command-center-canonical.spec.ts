import { expect, test, type Page, type Request } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";
import { assertBackendMode } from "./helpers/cph2";

const ARTIFACT_DIR = path.join(
  process.cwd(),
  "e2e-artifacts",
  "project-command-center-canonical-01",
);
// Must match browser cookie host (frontend aligns loopback API to page hostname).
const BACKEND_URL = (
  process.env.CPH2_BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://localhost:8001"
).replace(/\/$/, "");

async function registerCommercialUser(page: Page) {
  const email = `pcc.canon.${Date.now()}@marketsynth.local`;
  const password = "e2e-pcc-canon-pass1";
  await page.goto("/register");
  await expect(page.getByTestId("register-email")).toBeVisible({ timeout: 45_000 });
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-display-name").fill("PCC Canon User");
  await page.getByTestId("register-password").fill(password);
  await page.getByTestId("register-password-confirm").fill(password);
  await page.getByTestId("register-notice").check();
  await page.getByTestId("register-submit").click();
  await page.waitForURL(/\/workspace(\/projects\/new|\/?(\?|$))/, { timeout: 45_000 });
}

async function createProject(page: Page): Promise<{ id: string; name: string }> {
  const name = `PCC Canon ${Date.now()}`;
  const res = await page.request.fetch(`${BACKEND_URL}/projects`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Origin: process.env.CPH2_FRONTEND_URL || "http://localhost:3000",
    },
    data: { name },
  });
  expect(res.ok(), await res.text()).toBeTruthy();
  return { id: ((await res.json()) as { id: string }).id, name };
}

async function shot(page: Page, name: string) {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
  await page.screenshot({
    path: path.join(ARTIFACT_DIR, `${name}.png`),
    fullPage: true,
  });
}

test.describe("PROJECT-COMMAND-CENTER-CANONICAL-01", () => {
  test("Home → PCC → General → Text/Image → back; no generation on nav", async ({
    page,
  }) => {
    await assertBackendMode(page, "backend");
    await registerCommercialUser(page);
    const { id: projectId, name: projectName } = await createProject(page);

    const genPosts: Request[] = [];
    page.on("request", (req) => {
      if (req.method() === "POST" && /generate|skills\/runs/i.test(req.url())) {
        genPosts.push(req);
      }
    });

    await page.goto("/workspace");
    await expect(page.getByTestId("workspace-home")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("home-creative-capability-teaser")).toBeVisible();
    await expect(page.getByText("Создать материалы")).toHaveCount(0);
    await shot(page, "01-home");

    await page.goto("/workspace/projects");
    await expect(page.getByTestId("workspace-projects-list")).toBeVisible({
      timeout: 30_000,
    });
    await shot(page, "02-projects");

    await page.getByTestId("projects-open-command-center").first().click();
    await expect(page.getByTestId("project-command-center")).toBeVisible({
      timeout: 45_000,
    });
    await expect(page.getByTestId("pcc-brand-name")).toBeVisible();
    await expect(page.getByTestId("pcc-project-name")).toContainText(projectName);
    await expect(page.getByTestId("project-general-chat")).toBeVisible();
    await expect(page.getByTestId("project-capability-grid")).toBeVisible();
    await expect(page.getByTestId("pcc-capability-project-content_director-text")).toBeVisible();
    await expect(page.getByTestId("pcc-capability-project-content_director-image")).toBeVisible();
    await expect(page.getByTestId("pcc-capability-launch-visuals")).toBeVisible();
    await expect(page.getByTestId("content-director-panel")).toHaveCount(0);
    expect(page.url()).not.toContain("view=content_director");
    await expect(page.url()).not.toContain("owner_preview");
    await shot(page, "03-project-command-center");
    await shot(page, "04-capability-grid");
    await shot(page, "05-general-empty");

    await page.getByTestId("project-general-quick-text").click();
    await expect(page.getByTestId("project-general-message-assistant").first()).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.getByTestId("project-general-route").first()).toBeVisible();
    await shot(page, "06-general-response");

    await page.getByTestId("pcc-capability-cta-project-content_director-text").click();
    await expect(page.getByTestId("content-director-panel")).toBeVisible({
      timeout: 30_000,
    });
    expect(page.url()).toContain("view=content_director");
    expect(page.url()).toContain(`project=${projectId}`);
    await shot(page, "07-content-director-text");

    await page.getByTestId("content-director-back-to-project").click();
    await expect(page.getByTestId("project-command-center")).toBeVisible({
      timeout: 30_000,
    });
    expect(page.url()).not.toContain("view=content_director");

    await page.getByTestId("pcc-capability-cta-project-content_director-image").click();
    await expect(page.getByTestId("visual-director-panel")).toBeVisible({
      timeout: 30_000,
    });
    expect(page.url()).toContain("mode=image");
    await shot(page, "08-content-director-image");

    await page.getByTestId("content-director-back-to-project").click();
    await expect(page.getByTestId("project-command-center")).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.getByTestId("pcc-capability-launch-visuals")).toContainText(/Скоро|Coming/i);
    await shot(page, "09-video-placeholder");
    await shot(page, "10-back-to-project");

    await page.reload();
    await expect(page.getByTestId("project-command-center")).toBeVisible({
      timeout: 45_000,
    });
    await expect(page.getByTestId("project-general-chat")).toBeVisible();

    expect(genPosts.length, "no generation POST during navigation").toBe(0);
  });
});
