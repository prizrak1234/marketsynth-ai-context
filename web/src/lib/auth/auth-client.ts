/** Browser auth client — cookie session only (no API key in localStorage). */

import { getApiBaseUrl } from "@/lib/api/config";
import {
  mapAnonymousMeFailure,
  mapLoginFailure,
  type AuthError,
} from "@/lib/auth/auth-errors";
import type { AuthUser, LoginResult } from "@/lib/auth/session";

const LEGACY_E2E_KEY = "marketsynth.e2e.api_key.v1";

type ErrorBody = {
  detail?: unknown;
  error_code?: unknown;
  safe_message?: unknown;
};

async function parseAuthFailure(res: Response): Promise<string | undefined> {
  try {
    const body = (await res.json()) as ErrorBody;
    const detail = typeof body.detail === "string" ? body.detail : undefined;
    const safe =
      typeof body.safe_message === "string" ? body.safe_message : undefined;
    const code = typeof body.error_code === "string" ? body.error_code : undefined;
    for (const candidate of [detail, safe, code]) {
      if (
        candidate &&
        candidate !== "http_error" &&
        candidate !== "Request failed." &&
        candidate !== "Request failed"
      ) {
        return candidate;
      }
    }
    return detail || safe || code;
  } catch {
    return undefined;
  }
}

function browserOriginHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  return { Origin: window.location.origin };
}

/** Remove deprecated CPH.2 localStorage API-key shortcut if present. */
export function clearLegacyApiKeyStorage(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(LEGACY_E2E_KEY);
  } catch {
    /* ignore */
  }
}

export async function loginWithPassword(
  email: string,
  password: string,
): Promise<{ ok: true; result: LoginResult } | { ok: false; error: AuthError }> {
  clearLegacyApiKeyStorage();
  try {
    const res = await fetch(`${getApiBaseUrl()}/auth/login`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...browserOriginHeaders(),
      },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const detail = await parseAuthFailure(res);
      return { ok: false, error: mapLoginFailure(detail, res.status) };
    }
    const result = (await res.json()) as LoginResult;
    if (!result?.user?.id) {
      return {
        ok: false,
        error: mapLoginFailure("session_cookie_failed", 500),
      };
    }
    return { ok: true, result };
  } catch {
    return { ok: false, error: mapLoginFailure(undefined, 0) };
  }
}

export async function logoutSession(): Promise<void> {
  clearLegacyApiKeyStorage();
  try {
    await fetch(`${getApiBaseUrl()}/auth/logout`, {
      method: "POST",
      credentials: "include",
      headers: {
        ...browserOriginHeaders(),
      },
    });
  } catch {
    /* ignore network on logout */
  }
}

export async function fetchCurrentUser(): Promise<
  { ok: true; user: AuthUser } | { ok: false; error: AuthError }
> {
  clearLegacyApiKeyStorage();
  try {
    const res = await fetch(`${getApiBaseUrl()}/auth/me`, {
      method: "GET",
      credentials: "include",
      cache: "no-store",
    });
    if (!res.ok) {
      const detail = await parseAuthFailure(res);
      return { ok: false, error: mapAnonymousMeFailure(detail, res.status) };
    }
    const user = (await res.json()) as AuthUser;
    return { ok: true, user };
  } catch {
    return { ok: false, error: mapAnonymousMeFailure(undefined, 0) };
  }
}
