import { defineConfig, devices } from "@playwright/test";

const port = process.env.CAP_REGISTRY_PORT || "3000";
const baseURL = process.env.CAP_REGISTRY_FRONTEND_URL || `http://localhost:${port}`;
const reuseExistingServer = process.env.CAP_REGISTRY_REUSE_SERVER === "true";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 180_000,
  expect: { timeout: 20_000 },
  reporter: [["list"]],
  outputDir: "test-results/capability-registry-gate",
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    locale: "ru-RU",
  },
  webServer: reuseExistingServer
    ? undefined
    : {
        command: `npm run build && npx next start -p ${port}`,
        url: baseURL,
        reuseExistingServer: false,
        timeout: 600_000,
      },
  projects: [
    {
      name: "capability-registry",
      testMatch: ["**/capability-registry-navigation.spec.ts"],
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
