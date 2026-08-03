import { execSync } from "node:child_process";
import * as path from "node:path";
import { expect, test } from "@playwright/test";
import {
  ACCEPTANCE_TEXT,
  assertDbGoldenPath,
  BIV_REQUEST,
  countVisibleMessages,
  fetchUserRequests,
  GENERAL_QUESTION,
  loadChatGoldenPathContext,
  screenshotArtifact,
  setupChatGoldenPath,
  submitChatMessage,
  waitForChatHydrated,
} from "./helpers/chat-golden-path";

test.describe.configure({ mode: "serial" });

const REPO_ROOT = path.resolve(__dirname, "../..");

function purgeE2EHistory(): void {
  execSync("uv run python scripts/chat_golden_path_repair_e2e_history.py --purge", {
    cwd: REPO_ROOT,
    env: {
      ...process.env,
      DATABASE_URL:
        process.env.DATABASE_URL ||
        "postgresql+asyncpg://botfazer:botfazer@localhost:5432/botfazer_cph1",
    },
    stdio: "pipe",
  });
}

test.describe("Chat golden path E2E A–I", () => {
  test.beforeAll(() => {
    try {
      loadChatGoldenPathContext();
    } catch {
      return;
    }
    purgeE2EHistory();
  });

  test.beforeEach(async ({ page }) => {
    try {
      loadChatGoldenPathContext();
    } catch {
      test.skip(true, "blocked_by_missing_e2e_credentials");
    }
    await page.addInitScript(() => {
      window.localStorage.removeItem("marketsynth.home.conversation.v1");
      window.localStorage.removeItem("marketsynth.home.workspace.tasks.v1");
    });
  });

  test("A — general question → one pair, LLM general_answer", async ({ page }) => {
    const ctx = await setupChatGoldenPath(page);
    await page.goto("/workspace/assistant");
    await waitForChatHydrated(page);

    const before = await countVisibleMessages(page);
    const { postCount, lastPostBody } = await submitChatMessage(page, GENERAL_QUESTION);
    expect(postCount).toBe(1);
    expect(lastPostBody?.chat_route).toBe("general_answer");
    expect(lastPostBody?.status).toBe("routed");
    expect(lastPostBody?.execution_provider).toBeTruthy();
    expect(Number(lastPostBody?.skill_inputs?._llm_call_count ?? 0)).toBe(1);
    expect(lastPostBody?.assistant_message || "").toMatch(/Marketsynth|mock|unit/i);

    const visible = await countVisibleMessages(page);
    expect(visible.user).toBe(before.user + 1);
    expect(visible.assistant).toBe(before.assistant + 1);

    const assistantText = await page.getByTestId("home-message-assistant").first().innerText();
    expect(assistantText).not.toContain("жизнеспособность идеи");
    expect(assistantText.length).toBeGreaterThan(20);

    const ga = lastPostBody;
    expect(ga).toBeTruthy();

    await page.reload();
    await waitForChatHydrated(page);
    const afterRefresh = await countVisibleMessages(page);
    expect(afterRefresh.user).toBe(visible.user);
    expect(afterRefresh.assistant).toBe(visible.assistant);

    await screenshotArtifact(page, ctx, "A-general-question");
  });

  test("B — BIV request → business_idea_validation, no canned loop", async ({ page }) => {
    const ctx = await setupChatGoldenPath(page);
    await page.goto("/workspace/assistant");

    const { postCount } = await submitChatMessage(page, BIV_REQUEST);
    expect(postCount).toBe(1);

    const visible = await countVisibleMessages(page);
    expect(visible.user).toBeGreaterThanOrEqual(1);
    expect(visible.assistant).toBeGreaterThanOrEqual(1);

    const rows = await fetchUserRequests(page, ctx);
    const biv = rows.find((r) => r.text.includes("кофейни"));
    expect(biv?.chat_route).toBe("business_idea_validation");

    const assistantText = await page.getByTestId("home-message-assistant").first().innerText();
    expect(assistantText).not.toContain("Здесь лучше сначала проверить жизнеспособность идеи");
    await screenshotArtifact(page, ctx, "B-biv-request");
  });

  test("C — double click → one POST", async ({ page }) => {
    await setupChatGoldenPath(page);
    await page.goto("/workspace/assistant");
    await waitForChatHydrated(page);
    const before = await countVisibleMessages(page);

    const input = page.getByTestId("home-intent-input");
    await input.fill("Краткий тестовый вопрос: что такое CAC в маркетинге?");

    let postCount = 0;
    page.on("request", (req) => {
      if (req.url().includes("/user-requests") && req.method() === "POST") {
        postCount += 1;
      }
    });

    const submit = page.getByTestId("home-intent-submit");
    await submit.dblclick();
    await page.waitForTimeout(5000);

    expect(postCount).toBeLessThanOrEqual(1);
    const visible = await countVisibleMessages(page);
    expect(visible.user).toBeLessThanOrEqual(before.user + 1);
    expect(visible.assistant).toBeLessThanOrEqual(before.assistant + 1);
  });

  test("D — Enter + click race → one POST", async ({ page }) => {
    await setupChatGoldenPath(page);
    await page.goto("/workspace/assistant");

    let postCount = 0;
    page.on("request", (req) => {
      if (req.url().includes("/user-requests") && req.method() === "POST") {
        postCount += 1;
      }
    });

    const input = page.getByTestId("home-intent-input");
    await input.fill("Enter race: что такое LTV в SaaS?");
    await Promise.all([
      input.press("Enter"),
      page.getByTestId("home-intent-submit").click(),
    ]);
    await page.waitForTimeout(4000);

    expect(postCount).toBeLessThanOrEqual(1);
  });

  test("E — refresh during generation → no duplicate POST on remount", async ({ page }) => {
    const ctx = await setupChatGoldenPath(page);
    await page.goto("/workspace/assistant");

    const beforePosts = await countVisibleMessages(page);
    const { postCount } = await submitChatMessage(page, GENERAL_QUESTION);
    expect(postCount).toBe(1);

    await page.reload();
    await waitForChatHydrated(page);
    await expect(page.getByTestId("home-conversation")).toBeVisible({ timeout: 30_000 });

    let postAfterRefresh = 0;
    page.on("request", (req) => {
      if (req.url().includes("/user-requests") && req.method() === "POST") {
        postAfterRefresh += 1;
      }
    });
    await page.waitForTimeout(2000);
    expect(postAfterRefresh).toBe(0);

    const after = await countVisibleMessages(page);
    expect(after.user).toBeGreaterThanOrEqual(beforePosts.user + 1);
    expect(after.assistant).toBeGreaterThanOrEqual(beforePosts.assistant + 1);

    await page.reload();
    await waitForChatHydrated(page);
    const secondRefresh = await countVisibleMessages(page);
    expect(secondRefresh.user).toBe(after.user);
    expect(secondRefresh.assistant).toBe(after.assistant);

    await screenshotArtifact(page, ctx, "E-refresh-persistence");
  });

  test("F — session expiry → re-login, no orphan POST", async ({ page, context }) => {
    const ctx = await setupChatGoldenPath(page);
    await page.goto("/workspace/assistant");

    await context.clearCookies();
    await page.reload();
    await page.waitForURL(/\/login/, { timeout: 30_000 });

    let postCount = 0;
    page.on("request", (req) => {
      if (req.url().includes("/user-requests") && req.method() === "POST") {
        postCount += 1;
      }
    });
    expect(postCount).toBe(0);

    await page.getByLabel("Email").fill(ctx.email);
    await page.getByLabel("Пароль").fill(ctx.password);
    await page.getByTestId("login-submit").click();
    await page.waitForURL(/\/workspace/, { timeout: 60_000 });
    await page.goto("/workspace/assistant");
    await expect(page.getByTestId("home-execution-panel")).toBeVisible();
  });

  test("G — two tabs → hydrate shows same pair, no extra POST", async ({ browser }) => {
    const ctx = loadChatGoldenPathContext();
    const contextA = await browser.newContext();
    const contextB = await browser.newContext();
    const pageA = await contextA.newPage();
    const pageB = await contextB.newPage();

    await setupChatGoldenPath(pageA);
    await setupChatGoldenPath(pageB);

    await pageA.goto("/workspace/assistant");
    await waitForChatHydrated(pageA);
    const uniqueQuestion = "Two-tab hydrate marker-tab-g: что такое churn rate?";

    let postCount = 0;
    pageA.on("request", (req) => {
      if (req.url().includes("/user-requests") && req.method() === "POST") {
        postCount += 1;
      }
    });

    await submitChatMessage(pageA, uniqueQuestion);
    expect(postCount).toBe(1);

    let postCountB = 0;
    pageB.on("request", (req) => {
      if (req.url().includes("/user-requests") && req.method() === "POST") {
        postCountB += 1;
      }
    });

    await pageB.goto("/workspace/assistant");
    await waitForChatHydrated(pageB);
    await pageB.waitForTimeout(2000);
    expect(postCountB).toBe(0);

    const visibleB = await countVisibleMessages(pageB);
    expect(visibleB.user).toBeGreaterThanOrEqual(1);
    expect(visibleB.assistant).toBeGreaterThanOrEqual(1);

    const rows = await fetchUserRequests(pageA, ctx);
    const matches = rows.filter((r) => r.text.includes("marker-tab-g"));
    expect(matches.length).toBe(1);

    await contextA.close();
    await contextB.close();
  });

  test("H — network retry → same idempotency key, one LLM call", async ({ page }) => {
    const ctx = await setupChatGoldenPath(page);
    await page.goto("/workspace/assistant");

    let postAttempts = 0;
    await page.route("**/user-requests", async (route) => {
      if (route.request().method() === "POST") {
        postAttempts += 1;
        const response = await route.fetch();
        if (postAttempts === 1) {
          await route.fulfill({ status: 502, body: "gateway timeout — response lost" });
          return;
        }
        await route.fulfill({ response });
        return;
      }
      await route.continue();
    });

    const question = `Network retry marker-net-h: что такое MRR?`;
    const input = page.getByTestId("home-intent-input");
    await input.fill(question);
    await page.getByTestId("home-intent-submit").click();
    await page.waitForTimeout(1500);
    await page.getByTestId("home-intent-submit").click();
    await page.waitForResponse(
      (r) => r.url().includes("/user-requests") && r.request().method() === "POST" && r.status() === 201,
      { timeout: 60_000 },
    );

    expect(postAttempts).toBe(2);

    const rows = await fetchUserRequests(page, ctx);
    const matches = rows.filter((r) => r.text.includes("marker-net-h"));
    expect(matches.length).toBe(1);
    expect(Number(matches[0]?.skill_inputs?._llm_call_count ?? 0)).toBe(1);

    const visible = await countVisibleMessages(page);
    expect(visible.user).toBeGreaterThanOrEqual(1);
    expect(visible.assistant).toBeGreaterThanOrEqual(1);

    await screenshotArtifact(page, ctx, "H-network-retry");
  });

  test("I — exact acceptance case — live browser + DB", async ({ page }) => {
    const ctx = await setupChatGoldenPath(page);
    await page.goto("/workspace/assistant");

    let postCount = 0;
    page.on("request", (req) => {
      if (req.url().includes("/user-requests") && req.method() === "POST") {
        postCount += 1;
      }
    });

    const responsePromise = page.waitForResponse(
      (r) => r.url().includes("/user-requests") && r.request().method() === "POST",
    );
    await page.getByTestId("home-intent-input").fill(ACCEPTANCE_TEXT);
    await page.getByTestId("home-intent-submit").click();
    const response = await responsePromise;
    expect(response.status()).toBe(201);
    expect(postCount).toBe(1);

    const body = (await response.json()) as {
      chat_route: string;
      assistant_message: string;
      routing_decision_id: string;
      assistant_run_id: string;
    };
    expect(body.chat_route).toBe("project_action");
    expect(body.assistant_message).not.toContain("жизнеспособность идеи");
    expect(body.routing_decision_id).toBeTruthy();
    expect(body.assistant_run_id).toBeTruthy();

    const assistantSnippet = body.assistant_message.trim().slice(0, 36);
    const acceptanceUsers = page
      .getByTestId("home-message-user")
      .filter({ hasText: "ИИ-маркетинговое агентство" });
    const acceptanceAssistants = page
      .getByTestId("home-message-assistant")
      .filter({ hasText: assistantSnippet });

    await expect(acceptanceUsers).toHaveCount(1, { timeout: 30_000 });
    await expect(acceptanceAssistants).toHaveCount(1, { timeout: 30_000 });

    await page.reload();
    await waitForChatHydrated(page);
    await expect(acceptanceUsers).toHaveCount(1);
    await expect(acceptanceAssistants).toHaveCount(1);
    await page.reload();
    await waitForChatHydrated(page);
    await expect(acceptanceUsers).toHaveCount(1);
    await expect(acceptanceAssistants).toHaveCount(1);

    const rows = await fetchUserRequests(page, ctx);
    const acceptanceRows = rows.filter((r) => r.text.includes("ИИ-маркетинговое агентство"));
    expect(acceptanceRows).toHaveLength(1);
    expect(acceptanceRows[0]?.chat_route).toBe("project_action");
    expect(acceptanceRows[0]?.client_message_id).toBeTruthy();
    expect(acceptanceRows[0]?.idempotency_key).toBeTruthy();
    expect(acceptanceRows[0]?.routing_decision_id).toBeTruthy();
    expect(acceptanceRows[0]?.assistant_run_id).toBeTruthy();

    await assertDbGoldenPath(page, ctx);
    await screenshotArtifact(page, ctx, "acceptance-exact-case");
  });
});
