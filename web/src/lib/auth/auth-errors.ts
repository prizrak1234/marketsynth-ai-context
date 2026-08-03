/** Auth error kinds (CPH.3 login regression fix). */

import {
  DEFAULT_LOCALE,
  LOCALE_STORAGE_KEY,
  resolveLocale,
  type AppLocale,
} from "@/lib/i18n/config";
import { labelErrorCode, translate } from "@/lib/i18n/domain-labels";

export type AuthErrorKind =
  | "invalid_credentials"
  | "account_disabled"
  | "session_expired"
  | "session_revoked"
  | "authentication_required"
  | "forbidden"
  | "resource_not_found"
  | "csrf_failed"
  | "cors_origin_denied"
  | "session_cookie_failed"
  | "rate_limited"
  | "backend_unavailable"
  | "unknown_auth_error";

export type AuthError = {
  kind: AuthErrorKind;
  message: string;
  actionHint: string;
};

function currentLocale(): AppLocale {
  if (typeof window === "undefined") return DEFAULT_LOCALE;
  try {
    const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY);
    const browser = typeof navigator !== "undefined" ? navigator.language : undefined;
    return resolveLocale([stored, browser, DEFAULT_LOCALE]);
  } catch {
    return DEFAULT_LOCALE;
  }
}

function authMsg(kind: AuthErrorKind, fallbackRu: string): string {
  return labelErrorCode(currentLocale(), kind) ?? fallbackRu;
}

function authHint(hintKey: string, fallbackRu: string): string {
  const locale = currentLocale();
  const text = translate(locale, `errors.hint.${hintKey}`);
  return text === `errors.hint.${hintKey}` ? fallbackRu : text;
}

/** Anonymous session probe — not a login failure. */
export function mapAnonymousMeFailure(
  detail: string | undefined,
  status: number,
): AuthError {
  if (status === 0 || status >= 500) {
    return {
      kind: "backend_unavailable",
      message: authMsg("backend_unavailable", "Сервис временно недоступен."),
      actionHint: authHint("check_backend", "Проверьте backend и обновите страницу."),
    };
  }
  return {
    kind: "authentication_required",
    message: authMsg("authentication_required", "Требуется вход."),
    actionHint: authHint("enter_credentials", "Введите email и пароль."),
  };
}

export function mapLoginFailure(
  detail: string | undefined,
  status: number,
): AuthError {
  const d = (detail || "").toLowerCase();

  if (status === 0) {
    return {
      kind: "backend_unavailable",
      message: authMsg("backend_unavailable", "Сервер недоступен."),
      actionHint: authHint("api_running", "Убедитесь, что API запущен, и повторите вход."),
    };
  }
  if (status >= 500) {
    return {
      kind: "backend_unavailable",
      message: authMsg("backend_unavailable", "Сервис временно недоступен."),
      actionHint: authHint("try_later", "Попробуйте позже."),
    };
  }
  if (status === 429 || d.includes("rate_limited")) {
    return {
      kind: "rate_limited",
      message: authMsg("rate_limited", "Слишком много попыток входа."),
      actionHint: authHint("wait_retry", "Подождите несколько минут и попробуйте снова."),
    };
  }
  if (status === 403 && (d.includes("csrf") || d === "csrf_failed")) {
    return {
      kind: "csrf_failed",
      message: authMsg("csrf_failed", "Запрос отклонён политикой безопасности (CSRF)."),
      actionHint: authHint("use_canonical", "Откройте приложение по http://localhost:3000 и войдите снова."),
    };
  }
  if (
    status === 403 &&
    (d.includes("origin") || d.includes("not allowed"))
  ) {
    return {
      kind: "cors_origin_denied",
      message: authMsg("cors_origin_denied", "Недопустимый frontend origin."),
      actionHint: authHint("use_canonical", "Используйте http://localhost:3000."),
    };
  }
  if (d.includes("account_disabled") || d.includes("inactive") || d.includes("disabled")) {
    return {
      kind: "account_disabled",
      message: authMsg("account_disabled", "Учётная запись отключена."),
      actionHint: authHint("contact_admin", "Обратитесь к администратору."),
    };
  }
  if (
    d.includes("session") &&
    (d.includes("failed") || d.includes("cookie") || d.includes("create"))
  ) {
    return {
      kind: "session_cookie_failed",
      message: authMsg("session_cookie_failed", "Не удалось создать сессию."),
      actionHint: authHint("cookie_policy", "Проверьте cookie policy и совпадение API host с frontend host."),
    };
  }
  if (status === 401 || d.includes("invalid_credentials")) {
    return {
      kind: "invalid_credentials",
      message: authMsg("invalid_credentials", "Неверный логин или пароль."),
      actionHint: authHint("check_credentials", "Проверьте данные и повторите вход."),
    };
  }
  if (status === 403) {
    return {
      kind: "forbidden",
      message: authMsg("forbidden", "Недостаточно прав."),
      actionHint: authHint("use_own_account", "Войдите под своей учётной записью."),
    };
  }
  return {
    kind: "unknown_auth_error",
    message: authMsg("unknown_auth_error", "Ошибка входа."),
    actionHint: authHint("try_again", "Попробуйте ещё раз."),
  };
}

/** @deprecated Prefer mapAnonymousMeFailure / mapLoginFailure. Kept for non-login callers. */
export function mapAuthDetail(detail: string | undefined, status: number): AuthError {
  const d = (detail || "").toLowerCase();
  if (status === 401 && (d.includes("authentication_required") || !d || d === "unauthorized")) {
    return mapAnonymousMeFailure(detail, status);
  }
  if (status === 401 && d.includes("invalid_credentials")) {
    return mapLoginFailure(detail, status);
  }
  if (status === 401) {
    return mapAnonymousMeFailure(detail, status);
  }
  return mapLoginFailure(detail, status);
}
