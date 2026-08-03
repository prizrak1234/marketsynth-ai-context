import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

const productionPort = process.env.CPH2_PRODUCTION_PORT || "3000";
const productionBaseURL =
  process.env.CPH2_PRODUCTION_FRONTEND_URL || `http://localhost:${productionPort}`;
const reuseExistingServer = process.env.CPH2_PRODUCTION_REUSE_SERVER === "true";

process.env.CPH2_COMMERCIAL_UX_ARTIFACT_DIR = path.resolve(
  process.cwd(),
  "e2e-artifacts",
  "commercial-ux-slice-e-verification",
);

/** PRODUCT-01.4 Slice E — intake commercial unification screenshots. */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 180_000,
  expect: { timeout: 30_000 },
  reporter: [["list"]],
  outputDir: "test-results",
  use: {
    baseURL: productionBaseURL,
    trace: "retain-on-failure",
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
      name: "commercial-ux-slice-e",
      testMatch: ["**/commercial-ux-slice-e-verification.spec.ts"],
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
