/**
 * PRODUCT-01.4 Slice E owner visual pack — capture intake screenshots (no POST /runs).
 * Usage: node scripts/capture-slice-e-owner-visual.mjs --label before|after
 */
import { chromium, devices } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const label = process.argv.includes("--label")
  ? process.argv[process.argv.indexOf("--label") + 1]
  : "after";
const baseURL = process.env.OWNER_PREVIEW_URL || "http://localhost:3000";
const outRoot = path.resolve(
  process.cwd(),
  "e2e-artifacts/commercial-ux-slice-e-owner-visual",
  label,
);
const email = process.env.OWNER_PREVIEW_EMAIL;
const password = process.env.OWNER_PREVIEW_PASSWORD;
if (!email || !password) {
  console.error("OWNER_PREVIEW_EMAIL and OWNER_PREVIEW_PASSWORD are required.");
  process.exit(1);
}
const projectName = process.env.OWNER_PREVIEW_PROJECT || `OwnerVisual-${label}-${Date.now()}`;

fs.mkdirSync(outRoot, { recursive: true });

async function loginOrRegister(page) {
  await page.goto(`${baseURL}/login`, { waitUntil: "domcontentloaded" });
  if (/\/workspace/.test(page.url())) return;

  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Пароль").fill(password);
  await page.getByTestId("login-submit").click();
  try {
    await page.waitForURL(/\/workspace/, { timeout: 8_000 });
    return;
  } catch {
    // fall through to register
  }

  await page.goto(`${baseURL}/register`, { waitUntil: "domcontentloaded" });
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-display-name").fill("Owner Visual Review");
  await page.getByTestId("register-password").fill(password);
  await page.getByTestId("register-password-confirm").fill(password);
  await page.getByTestId("register-notice").check();
  await page.getByTestId("register-submit").click();
  await page.waitForURL(/\/workspace/, { timeout: 60_000 });
}

async function clickNext(page) {
  const byTestId = page.getByTestId("intake-next");
  if (await byTestId.count()) {
    await byTestId.click();
    return;
  }
  await page.getByRole("button", { name: /Далее/i }).click();
}

async function shot(page, name) {
  const file = path.join(outRoot, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  console.log("saved", file);
}

async function fillToReview(page) {
  await page.goto(`${baseURL}/workspace/projects/new`);
  await page.locator("#name").fill(projectName);
  await page.locator("#ideaDescription").fill("Локальная клиника: проверить спрос до запуска рекламы");
  await page.locator("#businessType").selectOption("local_business");
  await page.locator("#projectStage").selectOption("preparing_launch");
  await page.locator("#geography").fill("Москва");
  await shot(page, "step1-desktop");

  await page.setViewportSize({ width: 390, height: 844 });
  await shot(page, "step1-mobile");
  await page.setViewportSize(devices["Desktop Chrome"].viewport);

  await clickNext(page);
  await page.waitForURL(/\/idea/);
  await page.locator("#whatIsSold").fill("Стоматологические услуги");
  await page.locator("#primaryProblem").fill("Страх и цена откладывают лечение");
  await page.locator("#valueProposition").fill("Прозрачный прайс");
  await page.locator("#deliveryModel").fill("clinic");
  await clickNext(page);
  await page.waitForURL(/\/market/);
  await shot(page, "market-desktop");

  await page.locator("#targetMarket").fill("Взрослые пациенты в Москве");
  await page.locator("#competitorsUnknown").check();
  await clickNext(page);
  await page.waitForURL(/\/audience/);
  await page.locator('[id^="seg-label-"]').first().fill("Клиники 1–3 кресла");
  await clickNext(page);
  await page.waitForURL(/\/economics/);
  await clickNext(page);
  await page.waitForURL(/\/materials/);
  await shot(page, "materials-desktop");

  await clickNext(page);
  await page.waitForURL(/\/review/);
  await page.setViewportSize({ width: 1440, height: 900 });
  await shot(page, "review-desktop");
  await page.setViewportSize({ width: 390, height: 844 });
  await shot(page, "review-mobile");
}

const browser = await chromium.launch();
const context = await browser.newContext({
  baseURL,
  locale: "ru-RU",
  viewport: devices["Desktop Chrome"].viewport,
});
context.addInitScript(() => {
  window.localStorage.setItem("marketsynth.ui.locale.v1", "ru");
  window.localStorage.setItem("marketsynth.integration.mode.v1", "backend");
  window.localStorage.removeItem("marketsynth.home.developer_mode.v1");
});
const page = await context.newPage();
await loginOrRegister(page);
await fillToReview(page);
await browser.close();
console.log(`DONE label=${label} email=${email} password=${password}`);
