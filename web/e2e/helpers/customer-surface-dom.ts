import { expect, type Page } from "@playwright/test";

/** Patterns that must not appear in commercial customer DOM text. */
export const CUSTOMER_DOM_FORBIDDEN_PATTERNS: RegExp[] = [
  /Backend Project ID/i,
  /Brief fingerprint/i,
  /conditionally_ready/i,
  /partial_research/i,
  /result_kind/i,
  /business_verdict_id/i,
  /succeeded_insufficient/i,
  /pipeline_fetch_failed/i,
  /high_impact_insufficient/i,
  /internal_diagnostics/i,
  /BotFazer/i,
  /traceback/i,
  /api_key/i,
  /MCP search/i,
  /provider_circuit/i,
  /research_terminal_state/i,
  /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i,
];

export async function assertCustomerSafeDom(page: Page): Promise<void> {
  const body = await page.locator("body").innerText();
  for (const pattern of CUSTOMER_DOM_FORBIDDEN_PATTERNS) {
    expect(body, `Forbidden customer DOM leak: ${pattern}`).not.toMatch(pattern);
  }
  await expect(page.getByTestId("biv-developer-panel")).toHaveCount(0);
  await expect(page.getByTestId("intake-developer-diagnostics")).toHaveCount(0);
  await expect(page.getByTestId("biv-pipeline-metrics")).toHaveCount(0);
  await expect(page.getByTestId("biv-pipeline-failure")).toHaveCount(0);
}
