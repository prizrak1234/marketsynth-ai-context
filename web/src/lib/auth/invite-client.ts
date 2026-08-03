/** Pilot invite activation client — cookie session only. */

import { getApiBaseUrl } from "@/lib/api/config";
import {
  clearLegacyApiKeyStorage,
} from "@/lib/auth/auth-client";
import type { AuthUser, LoginResult } from "@/lib/auth/session";

export type InvitePublicState =
  | "valid"
  | "expired"
  | "revoked"
  | "already_used"
  | "invalid"
  | "account_exists"
  | "backend_unavailable";

export type InviteStatus = {
  state: InvitePublicState;
  email: string | null;
  expires_at: string | null;
};

type ErrorBody = {
  detail?: unknown;
  error_code?: unknown;
  safe_message?: unknown;
};

function browserOriginHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  return { Origin: window.location.origin };
}

async function parseDetail(res: Response): Promise<string | undefined> {
  try {
    const body = (await res.json()) as ErrorBody;
    const detail = typeof body.detail === "string" ? body.detail : undefined;
    const safe =
      typeof body.safe_message === "string" ? body.safe_message : undefined;
    const code = typeof body.error_code === "string" ? body.error_code : undefined;
    return detail || safe || code;
  } catch {
    return undefined;
  }
}

export async function fetchInviteStatus(
  token: string,
): Promise<{ ok: true; status: InviteStatus } | { ok: false; state: InvitePublicState }> {
  try {
    const res = await fetch(
      `${getApiBaseUrl()}/auth/invitations/${encodeURIComponent(token)}/status`,
      {
        method: "GET",
        credentials: "include",
        headers: { ...browserOriginHeaders() },
      },
    );
    if (!res.ok) {
      if (res.status === 0 || res.status >= 500) {
        return { ok: false, state: "backend_unavailable" };
      }
      return { ok: false, state: "invalid" };
    }
    const body = (await res.json()) as {
      state: InvitePublicState;
      email?: string | null;
      expires_at?: string | null;
    };
    return {
      ok: true,
      status: {
        state: body.state,
        email: body.email ?? null,
        expires_at: body.expires_at ?? null,
      },
    };
  } catch {
    return { ok: false, state: "backend_unavailable" };
  }
}

export type AcceptInviteInput = {
  token: string;
  displayName: string;
  password: string;
  passwordConfirm: string;
  acceptPilotNotice: boolean;
};

export type AcceptInviteError = {
  code: string;
  message: string;
};

export async function acceptInvite(
  input: AcceptInviteInput,
): Promise<
  | { ok: true; result: LoginResult }
  | { ok: false; error: AcceptInviteError }
> {
  clearLegacyApiKeyStorage();
  try {
    const res = await fetch(
      `${getApiBaseUrl()}/auth/invitations/${encodeURIComponent(input.token)}/accept`,
      {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...browserOriginHeaders(),
        },
        body: JSON.stringify({
          display_name: input.displayName,
          password: input.password,
          password_confirm: input.passwordConfirm,
          accept_pilot_notice: input.acceptPilotNotice,
        }),
      },
    );
    if (!res.ok) {
      const detail = (await parseDetail(res)) || "activation_failed";
      return { ok: false, error: mapAcceptError(detail, res.status) };
    }
    const result = (await res.json()) as LoginResult;
    if (!result?.user?.id) {
      return {
        ok: false,
        error: {
          code: "session_cookie_failed",
          message: "Не удалось создать сессию после активации.",
        },
      };
    }
    return { ok: true, result };
  } catch {
    return {
      ok: false,
      error: {
        code: "backend_unavailable",
        message: "Сервер недоступен. Проверьте API и повторите.",
      },
    };
  }
}

function mapAcceptError(detail: string, status: number): AcceptInviteError {
  const d = detail.toLowerCase();
  if (status === 0 || status >= 500 || d.includes("backend")) {
    return { code: "backend_unavailable", message: "Сервис временно недоступен." };
  }
  if (d.includes("account_exists")) {
    return {
      code: "account_exists",
      message: "Аккаунт для этого email уже существует. Войдите со своим паролем.",
    };
  }
  if (d.includes("invite_expired") || d === "expired") {
    return { code: "invite_expired", message: "Срок действия приглашения истёк." };
  }
  if (d.includes("invite_revoked") || d === "revoked") {
    return { code: "invite_revoked", message: "Приглашение отозвано." };
  }
  if (d.includes("invite_used") || d.includes("already")) {
    return {
      code: "invite_used",
      message: "Приглашение уже использовано. Войдите, если аккаунт создан.",
    };
  }
  if (d.includes("password_mismatch")) {
    return { code: "password_mismatch", message: "Пароли не совпадают." };
  }
  if (d.includes("password_too_short") || d.includes("password_too_weak")) {
    return {
      code: "password_invalid",
      message: "Пароль слишком короткий или слабый (минимум 10 символов).",
    };
  }
  if (d.includes("notice_required")) {
    return {
      code: "notice_required",
      message: "Нужно принять уведомление об обработке данных пилота.",
    };
  }
  if (d.includes("csrf")) {
    return {
      code: "csrf_failed",
      message: "Запрос отклонён (CSRF). Откройте localhost:3000.",
    };
  }
  if (d.includes("rate_limited") || status === 429) {
    return { code: "rate_limited", message: "Слишком много попыток. Подождите и повторите." };
  }
  return { code: "invalid_token", message: "Приглашение недействительно." };
}

export type { AuthUser };
