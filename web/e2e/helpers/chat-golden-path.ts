import { expect, type Page } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";
import {
  apiJson,
  assertBackendMode,
  loadE2EContext,
  loginViaUi,
  type E2ERunContext,
} from "./cph2";

export type UserRequestRow = {
  id: string;
  text: string;
  status: string;
  client_message_id: string | null;
  idempotency_key: string | null;
  sequence_number: number | null;
  assistant_run_id: string | null;
  routing_decision_id: string | null;
  chat_route: string | null;
  assistant_message: string;
  skill_inputs?: Record<string, unknown>;
  execution_provider?: string | null;
};

export type ChatGoldenPathMetrics = {
  apiPostCount: number;
  userBubbleCount: number;
  assistantBubbleCount: number;
  userRequestRows: number;
  uniqueClientMessageIds: number;
  uniqueIdempotencyKeys: number;
  uniqueAssistantRunIds: number;
  uniqueRoutingDecisionIds: number;
  llmCallCount: number;
};

export function loadChatGoldenPathContext(): E2ERunContext {
  const ctx = loadE2EContext();
  const artifactDir = path.join(process.cwd(), "test-results", "chat-golden-path", ctx.runId);
  fs.mkdirSync(artifactDir, { recursive: true });
  return { ...ctx, artifactDir };
}

export async function setupChatGoldenPath(page: Page): Promise<E2ERunContext> {
  const ctx = loadChatGoldenPathContext();
  const proxyBackend = process.env.CHAT_E2E_BACKEND_PROXY_URL;
  if (proxyBackend) {
    const to = proxyBackend.replace(/\/$/, "");
    for (const from of [ctx.backendUrl, ctx.backendUrl.replace("localhost", "127.0.0.1")]) {
      const base = from.replace(/\/$/, "");
      await page.route(`${base}/**`, async (route) => {
        const url = route.request().url().replace(base, to);
        await route.continue({ url });
      });
    }
  }
  await assertBackendMode(page, "backend");
  await page.addInitScript(() => {
    window.localStorage.setItem("marketsynth.ui.locale.v1", "ru");
  });
  await loginViaUi(page, ctx);
  return ctx;
}

export async function fetchUserRequests(page: Page, ctx: E2ERunContext): Promise<UserRequestRow[]> {
  return apiJson<UserRequestRow[]>(page, ctx, "GET", "/user-requests?limit=200");
}

export async function assertDbGoldenPath(
  page: Page,
  ctx: E2ERunContext,
  opts: {
    expectedRows?: number;
    expectedLlmCalls?: number;
    clientMessageId?: string;
    idempotencyKey?: string;
  } = {},
): Promise<UserRequestRow[]> {
  const rows = await fetchUserRequests(page, ctx);
  const clientIds = rows.map((r) => r.client_message_id).filter(Boolean);
  const idemKeys = rows.map((r) => r.idempotency_key).filter(Boolean);
  const runIds = rows.map((r) => r.assistant_run_id).filter(Boolean);
  const routingIds = rows.map((r) => r.routing_decision_id).filter(Boolean);

  expect(new Set(clientIds).size).toBe(clientIds.length);
  expect(new Set(idemKeys).size).toBe(idemKeys.length);
  expect(new Set(runIds).size).toBe(runIds.length);
  expect(new Set(routingIds).size).toBe(routingIds.length);

  if (opts.clientMessageId) {
    const matches = rows.filter((r) => r.client_message_id === opts.clientMessageId);
    expect(matches).toHaveLength(1);
  }
  if (opts.idempotencyKey) {
    const matches = rows.filter((r) => r.idempotency_key === opts.idempotencyKey);
    expect(matches).toHaveLength(1);
  }
  if (opts.expectedRows !== undefined) {
    expect(rows.length).toBeGreaterThanOrEqual(opts.expectedRows);
  }
  if (opts.expectedLlmCalls !== undefined) {
    const gaRows = rows.filter((r) => r.chat_route === "general_answer");
    const llmTotal = gaRows.reduce(
      (sum, row) => sum + Number(row.skill_inputs?._llm_call_count ?? 0),
      0,
    );
    expect(llmTotal).toBeGreaterThanOrEqual(opts.expectedLlmCalls);
    if (opts.expectedLlmCalls > 0) {
      expect(gaRows.some((r) => r.execution_provider === "mock" || r.execution_provider)).toBeTruthy();
    }
  }
  return rows;
}

export async function waitForChatHydrated(page: Page): Promise<void> {
  await expect(page.getByTestId("home-execution-panel")).toBeVisible();
  await page.waitForResponse(
    (r) => r.url().includes("/user-requests") && r.request().method() === "GET" && r.ok(),
    { timeout: 30_000 },
  );
  await expect(page.getByTestId("home-execution-panel")).toHaveAttribute("data-hydrated", "1", {
    timeout: 30_000,
  });
}

export async function countVisibleMessages(page: Page): Promise<{
  user: number;
  assistant: number;
}> {
  const user = await page.getByTestId("home-message-user").count();
  const assistant = await page.getByTestId("home-message-assistant").count();
  return { user, assistant };
}

export async function submitChatMessage(
  page: Page,
  text: string,
  opts: { waitForResponse?: boolean } = {},
): Promise<{ postCount: number; lastPostBody?: UserRequestRow }> {
  let postCount = 0;
  let lastPostBody: UserRequestRow | undefined;
  const onRequest = (req: { url: () => string; method: () => string }) => {
    if (req.url().includes("/user-requests") && req.method() === "POST") {
      postCount += 1;
    }
  };
  page.on("request", onRequest);

  const input = page.getByTestId("home-intent-input");
  await input.fill(text);

  if (opts.waitForResponse !== false) {
    const responsePromise = page.waitForResponse(
      (r) => r.url().includes("/user-requests") && r.request().method() === "POST",
      { timeout: 60_000 },
    );
    await page.getByTestId("home-intent-submit").click();
    const response = await responsePromise;
    if (response.ok()) {
      lastPostBody = (await response.json()) as UserRequestRow;
    }
    const snippet = text.trim().slice(0, 40);
    const tail = text.trim().slice(-28);
    await expect(page.getByTestId("home-message-user").last()).toContainText(tail, {
      timeout: 30_000,
    });
    await expect(page.getByTestId("home-message-assistant").last()).toBeVisible({
      timeout: 30_000,
    });
    void snippet;
  } else {
    await page.getByTestId("home-intent-submit").click();
  }

  await expect(page.getByTestId("home-conversation")).toBeVisible({ timeout: 60_000 });
  page.off("request", onRequest);
  return { postCount, lastPostBody };
}

export async function screenshotArtifact(page: Page, ctx: E2ERunContext, name: string) {
  const filePath = path.join(ctx.artifactDir, `${name}.png`);
  await page.screenshot({ path: filePath, fullPage: true });
  return filePath;
}

export const ACCEPTANCE_TEXT =
  "Делаю SaaS проект. ИИ-маркетинговое агентство, которое заменяет реальное агентство. " +
  "Функционал — от идеи до полноценной рекламной кампании, а также создание контента для разных каналов.";

export const GENERAL_QUESTION =
  "Что такое unit-экономика SaaS и как её считать для подписной модели?";

export const BIV_REQUEST =
  "Хочу проверить бизнес-идею кофейни в центре города — аудитория офисные работники.";
