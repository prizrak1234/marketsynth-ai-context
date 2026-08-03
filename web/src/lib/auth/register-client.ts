/** Registration client — cookie session only. */

import { getApiBaseUrl } from "@/lib/api/config";
import { clearLegacyApiKeyStorage } from "@/lib/auth/auth-client";
import type { LoginResult } from "@/lib/auth/session";

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

export async function fetchSignupStatus(): Promise<{
  signupEnabled: boolean;
  inviteAvailable: boolean;
}> {
  try {
    const res = await fetch(`${getApiBaseUrl()}/auth/signup-status`, {
      method: "GET",
      credentials: "include",
      cache: "no-store",
    });
    if (!res.ok) {
      return { signupEnabled: false, inviteAvailable: true };
    }
    const body = (await res.json()) as {
      signup_enabled?: boolean;
      invite_activation_available?: boolean;
    };
    return {
      signupEnabled: Boolean(body.signup_enabled),
      inviteAvailable: body.invite_activation_available !== false,
    };
  } catch {
    return { signupEnabled: false, inviteAvailable: true };
  }
}

export type RegisterInput = {
  email: string;
  displayName: string;
  password: string;
  passwordConfirmation: string;
  acceptedPilotNotice: boolean;
};

export type RegisterError = { code: string; message: string };

export async function registerAccount(
  input: RegisterInput,
): Promise<
  { ok: true; result: LoginResult } | { ok: false; error: RegisterError }
> {
  clearLegacyApiKeyStorage();
  try {
    const res = await fetch(`${getApiBaseUrl()}/auth/register`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...browserOriginHeaders(),
      },
      body: JSON.stringify({
        email: input.email,
        display_name: input.displayName,
        password: input.password,
        password_confirmation: input.passwordConfirmation,
        accepted_pilot_notice: input.acceptedPilotNotice,
      }),
    });
    if (!res.ok) {
      const detail = (await parseDetail(res)) || "registration_failed";
      return { ok: false, error: mapRegisterError(detail, res.status) };
    }
    const result = (await res.json()) as LoginResult;
    if (!result?.user?.id) {
      return {
        ok: false,
        error: {
          code: "session_cookie_failed",
          message: "Не удалось создать сессию после регистрации.",
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

function mapRegisterError(detail: string, status: number): RegisterError {
  const d = detail.toLowerCase();
  if (status === 0 || status >= 500) {
    return { code: "backend_unavailable", message: "Сервис временно недоступен." };
  }
  if (d.includes("signup_disabled") || status === 403) {
    return {
      code: "signup_disabled",
      message: "Регистрация сейчас отключена. Войдите или активируйте приглашение.",
    };
  }
  if (d.includes("email_taken") || status === 409) {
    return {
      code: "email_taken",
      message: "Аккаунт с этим email уже существует.",
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
  if (d.includes("invalid_email")) {
    return {
      code: "invalid_email",
      message: "Введите полный email, например name@example.com",
    };
  }
  if (d.includes("notice_required")) {
    return {
      code: "notice_required",
      message: "Нужно принять условия пилота.",
    };
  }
  if (d.includes("rate_limited") || status === 429) {
    return {
      code: "rate_limited",
      message: "Слишком много попыток. Подождите и повторите.",
    };
  }
  return { code: "registration_failed", message: "Не удалось зарегистрироваться." };
}
