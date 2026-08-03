import { defineConfig, devices } from "@playwright/test";

const productionPort = process.env.CPH2_PRODUCTION_PORT || "3000";
// Production-boundary MUST use port 3000 unless backend CORS allowlist is extended.
// Stop `next dev` on this port before running (reuseExistingServer only skips build/start).
const productionBaseURL =
  process.env.CPH2_PRODUCTION_FRONTEND_URL || `http://localhost:${productionPort}`;
const reuseExistingServer = process.env.CPH2_PRODUCTION_REUSE_SERVER === "true";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 180_000,
  expect: { timeout: 20_000 },
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
      name: "production-boundary",
    testMatch: [
      "**/runtime-01e-production-boundary.spec.ts",
      "**/runtime-01g-findings-01b-landing-production.spec.ts",
      "**/runtime-01g-ux-correction-production.spec.ts",
    ],
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
