/** Password reset API — never stores token in localStorage. */

import { getApiBaseUrl } from "@/lib/api/config";

export type ResetTokenState =
  | "valid"
  | "invalid"
  | "expired"
  | "used"
  | "revoked"
  | "backend_unavailable";

type ErrorBody = { detail?: unknown };

function browserOriginHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  return { Origin: window.location.origin };
}

async function parseDetail(res: Response): Promise<string | undefined> {
  try {
    const body = (await res.json()) as ErrorBody;
    return typeof body.detail === "string" ? body.detail : undefined;
  } catch {
    return undefined;
  }
}

const GENERIC_OK =
  "If an account exists, password reset instructions have been created.";

export async function requestPasswordReset(
  email: string,
): Promise<{ ok: true; message: string } | { ok: false; code: string }> {
  try {
    const res = await fetch(`${getApiBaseUrl()}/auth/password-reset/request`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...browserOriginHeaders(),
      },
      body: JSON.stringify({ email }),
    });
    if (res.status === 429) {
      return { ok: false, code: "rate_limited" };
    }
    if (!res.ok) {
      if (res.status >= 500 || res.status === 0) {
        return { ok: false, code: "backend_unavailable" };
      }
      return { ok: false, code: (await parseDetail(res)) || "request_failed" };
    }
    const body = (await res.json()) as { message?: string };
    return { ok: true, message: body.message || GENERIC_OK };
  } catch {
    return { ok: false, code: "backend_unavailable" };
  }
}

export async function fetchResetStatus(
  token: string,
): Promise<ResetTokenState> {
  try {
    const encoded = encodeURIComponent(token);
    const res = await fetch(
      `${getApiBaseUrl()}/auth/password-reset/${encoded}/status`,
      {
        method: "GET",
        credentials: "include",
        cache: "no-store",
      },
    );
    if (!res.ok) {
      if (res.status >= 500) return "backend_unavailable";
      return "invalid";
    }
    const body = (await res.json()) as { state?: string };
    const state = (body.state || "invalid") as ResetTokenState;
    return state;
  } catch {
    return "backend_unavailable";
  }
}

export async function completePasswordReset(
  token: string,
  password: string,
  passwordConfirmation: string,
): Promise<{ ok: true } | { ok: false; code: string }> {
  try {
    const encoded = encodeURIComponent(token);
    const res = await fetch(
      `${getApiBaseUrl()}/auth/password-reset/${encoded}/complete`,
      {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...browserOriginHeaders(),
        },
        body: JSON.stringify({
          password,
          password_confirmation: passwordConfirmation,
        }),
      },
    );
    if (!res.ok) {
      if (res.status === 0 || res.status >= 500) {
        return { ok: false, code: "backend_unavailable" };
      }
      if (res.status === 429) return { ok: false, code: "rate_limited" };
      return { ok: false, code: (await parseDetail(res)) || "complete_failed" };
    }
    return { ok: true };
  } catch {
    return { ok: false, code: "backend_unavailable" };
  }
}
