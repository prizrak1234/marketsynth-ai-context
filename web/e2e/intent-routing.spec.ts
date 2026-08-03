import { expect, test } from "@playwright/test";
import {
  avoidsInvestigation,
  isAmbiguousRequest,
  routeUserIntent,
} from "../src/lib/home/intent-routing";

test.describe("intent routing (deterministic)", () => {
  test("content plan does not open Investigation", () => {
    const r = routeUserIntent("Сделай контент-план для Telegram на месяц.");
    expect(r.category).toBe("social_media");
    expect(r.kind).toBe("specialist_task");
    expect(r.requiresProject).toBe(false);
    expect(avoidsInvestigation(r.category)).toBe(true);
    expect(r.nextHref).toContain("/workspace/tasks");
    expect(r.nextHref).not.toContain("investigation");
  });

  test("business idea routes to Project Intake", () => {
    const r = routeUserIntent("Хочу открыть стоматологию.");
    expect(r.category).toBe("idea_validation");
    expect(r.kind).toBe("project_intake");
    expect(r.requiresProject).toBe(true);
    expect(r.nextHref).toContain("/workspace/projects/new");
  });

  test("telegram bot routes to specialist flow", () => {
    const r = routeUserIntent("Создай Telegram-бота для записи клиентов.");
    expect(r.category).toBe("telegram_bot");
    expect(r.kind).toBe("specialist_task");
    expect(avoidsInvestigation(r.category)).toBe(true);
    expect(r.nextHref).toContain("telegram_bot");
  });

  test("ambiguous advertising asks clarification", () => {
    expect(isAmbiguousRequest("Хочу рекламу")).toBe(true);
    const r = routeUserIntent("Хочу рекламу");
    expect(r.kind).toBe("clarify");
    expect(r.clarificationQuestion).toBeTruthy();
    expect(r.nextHref).toBeNull();
  });
});
