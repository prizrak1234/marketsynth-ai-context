/**
 * Integration Mode — Product Alpha ↔ existing backend (Phase I1).
 *
 * MOCK: Product Alpha demos only (localStorage / fixtures) — development/demo
 * BACKEND: existing API only — honest empty/error/unavailable (pilot default)
 * HYBRID: backend where supported; labelled mock only for gaps
 */

export type IntegrationMode = "mock" | "backend" | "hybrid";

const MODE_KEY = "marketsynth.integration.mode.v1";
const ENV_MODE = "NEXT_PUBLIC_MARKETSYNTH_INTEGRATION_MODE";

function readEnvMode(): IntegrationMode | null {
  if (typeof process === "undefined") return null;
  const raw = process.env[ENV_MODE]?.trim().toLowerCase();
  if (raw === "mock" || raw === "backend" || raw === "hybrid") return raw;
  return null;
}

function readStoredMode(): IntegrationMode | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(MODE_KEY)?.trim().toLowerCase();
    if (raw === "mock" || raw === "backend" || raw === "hybrid") return raw;
  } catch {
    /* ignore */
  }
  return null;
}

/**
 * Default: backend for authenticated pilot (no silent mock as real data).
 * Env override wins; explicit localStorage only when set by admin/dev.
 */
export function getIntegrationMode(): IntegrationMode {
  return readEnvMode() ?? readStoredMode() ?? "backend";
}

export function setIntegrationMode(mode: IntegrationMode): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(MODE_KEY, mode);
}

export function integrationModeLabel(mode: IntegrationMode): string {
  switch (mode) {
    case "mock":
      return "Integration: mock";
    case "backend":
      return "Integration: backend";
    case "hybrid":
      return "Integration: hybrid";
    default:
      return "Integration: unknown";
  }
}

/** Mode switcher only for owner/admin in non-production browser. */
export function canShowIntegrationModeSwitcher(role: string | null | undefined): boolean {
  const r = (role || "").toLowerCase();
  if (r !== "owner" && r !== "admin") return false;
  if (typeof process !== "undefined" && process.env.NODE_ENV === "production") {
    // Still allow if explicitly forced mock via env for demos.
    return readEnvMode() === "mock" || readEnvMode() === "hybrid";
  }
  return true;
}

export const INTEGRATION_MODE_STORAGE_KEY = MODE_KEY;
export const INTEGRATION_MODE_ENV = ENV_MODE;
