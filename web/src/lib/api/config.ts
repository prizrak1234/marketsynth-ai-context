/**
 * Frontend URL / API base helpers.
 *
 * Canonical local frontend: http://localhost:3000
 * API host is rewritten to match window.location.hostname when possible so
 * HttpOnly session cookies stay same-site (localhost↔127.0.0.1 are different sites).
 */

const DEFAULT_API_URL = "http://localhost:8000";

function readEnv(name: string): string | undefined {
  const raw = process.env[name]?.trim();
  return raw && raw.length > 0 ? raw : undefined;
}

function alignApiHostToPage(apiBase: string): string {
  if (typeof window === "undefined") return apiBase;
  try {
    const api = new URL(apiBase);
    // Only rewrite for local loopback pilots — never rewrite real domains.
    const pageHost = window.location.hostname;
    const apiIsLoopback = api.hostname === "localhost" || api.hostname === "127.0.0.1";
    const pageIsLoopback = pageHost === "localhost" || pageHost === "127.0.0.1";
    if (apiIsLoopback && pageIsLoopback && api.hostname !== pageHost) {
      api.hostname = pageHost;
    }
    return api.origin;
  } catch {
    return apiBase;
  }
}

export function getApiBaseUrl(): string {
  // Next.js only inlines *literal* `process.env.NEXT_PUBLIC_*` access into client bundles.
  // Dynamic `process.env[name]` stays undefined in the browser and silently falls back.
  const raw = (
    process.env.NEXT_PUBLIC_BOTFAZER_API_BASE_URL ??
    process.env.NEXT_PUBLIC_BOTFAZER_API_URL
  )?.trim();
  const base = raw && raw.length > 0 ? raw.replace(/\/$/, "") : DEFAULT_API_URL;
  return alignApiHostToPage(base);
}

/**
 * Optional Bearer for non-browser/service clients only.
 * CPH.3: do NOT read permanent keys from localStorage.
 * Browser pilot auth uses HttpOnly cookie sessions (`credentials: include`).
 */
export function getApiKey(): string | undefined {
  return readEnv("NEXT_PUBLIC_BOTFAZER_API_KEY");
}

export function getDefaultProjectId(): string | undefined {
  return readEnv("NEXT_PUBLIC_BOTFAZER_PROJECT_ID");
}

export function hasApiKey(): boolean {
  return getApiKey() !== undefined;
}

/**
 * CPH.3 — backend calls are allowed with cookie session (HttpOnly, not readable)
 * or optional Bearer env key. Do not gate commercial UI on hasApiKey alone.
 */
export function canUseBackendApi(): boolean {
  if (hasApiKey()) return true;
  return typeof window !== "undefined";
}

export function hasDefaultProjectId(): boolean {
  return getDefaultProjectId() !== undefined;
}
