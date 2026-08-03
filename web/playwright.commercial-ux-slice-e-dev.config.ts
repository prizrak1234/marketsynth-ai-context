import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

const devPort = process.env.CPH2_DEV_PORT || "3001";
const devBaseURL = process.env.CPH2_DEV_FRONTEND_URL || `http://localhost:${devPort}`;

process.env.CPH2_COMMERCIAL_UX_ARTIFACT_DIR = path.resolve(
  process.cwd(),
  "e2e-artifacts",
  "commercial-ux-slice-e-verification",
);

/** Development server — dev diagnostics screenshot only (non-production bundle). */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 180_000,
  expect: { timeout: 30_000 },
  reporter: [["list"]],
  use: {
    baseURL: devBaseURL,
    trace: "retain-on-failure",
    locale: "ru-RU",
  },
  webServer: {
    command: `npm run dev -- -p ${devPort}`,
    url: devBaseURL,
    reuseExistingServer: false,
    timeout: 300_000,
  },
  projects: [
    {
      name: "commercial-ux-slice-e-dev",
      testMatch: ["**/commercial-ux-slice-e-dev-diagnostics.spec.ts"],
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
