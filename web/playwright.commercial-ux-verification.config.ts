import path from "node:path";
import { defineConfig, devices } from "@playwright/test";

const productionPort = process.env.CPH2_PRODUCTION_PORT || "3000";
const productionBaseURL =
  process.env.CPH2_PRODUCTION_FRONTEND_URL || `http://localhost:${productionPort}`;
const reuseExistingServer = process.env.CPH2_PRODUCTION_REUSE_SERVER === "true";

process.env.CPH2_COMMERCIAL_UX_ARTIFACT_DIR = path.resolve(
  process.cwd(),
  "test-results",
  "commercial-ux-a-d-verification",
);
/** PRODUCT-01.4 — commercial UX A–D verification against production build. */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 420_000,
  expect: { timeout: 30_000 },
  reporter: [["list"]],
  outputDir: "test-results",
  use: {
    baseURL: productionBaseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    locale: "ru-RU",
  },
  webServer: reuseExistingServer
    ? undefined
    : {
        command: `npm run build && npx next start -p ${productionPort}`,
        url: productionBaseURL,
        reuseExistingServer: false,
        timeout: 600_000,
      },
  projects: [
    {
      name: "commercial-ux-a-d",
      testMatch: ["**/commercial-ux-slices-a-d-verification.spec.ts"],
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
