import { ApiError } from "@/lib/api/client";

/** Snake_case domain codes that must never be shown to users. */
const INTERNAL_CODE_PATTERN = /^[a-z][a-z0-9_]*$/;

export type CommercialErrorView = {
  title: string;
  message: string;
  actionHint: string;
  internalCode: string | null;
};

export function isInternalErrorCode(value: string | null | undefined): boolean {
  if (!value) return false;
  const trimmed = value.trim();
  if (!trimmed) return false;
  if (trimmed.startsWith("Request failed (")) return true;
  if (/^\d{3}$/.test(trimmed)) return true;
  return INTERNAL_CODE_PATTERN.test(trimmed);
}

function readApiErrorCode(err: ApiError): string | null {
  if (err.errorCode && isInternalErrorCode(err.errorCode)) {
    return err.errorCode;
  }
  if (isInternalErrorCode(err.message)) {
    return err.message;
  }
  return err.errorCode ?? null;
}

type TranslateFn = (key: string) => string;

function translateOr(
  t: TranslateFn,
  key: string,
  fallback: string,
): string {
  const translated = t(key);
  return translated !== key ? translated : fallback;
}

/**
 * Map backend/API failures to commercial user-facing copy.
 * Never returns raw domain codes, HTTP statuses, or stack traces.
 */
export function mapCommercialError(
  err: unknown,
  t: TranslateFn,
  context: "research" | "general" = "general",
): CommercialErrorView {
  if (err instanceof ApiError) {
    const code = readApiErrorCode(err);
    const safeBodyMessage =
      typeof err.body === "object" &&
      err.body !== null &&
      typeof (err.body as Record<string, unknown>).safe_message === "string"
        ? String((err.body as Record<string, unknown>).safe_message).trim()
        : null;

    if (safeBodyMessage && !isInternalErrorCode(safeBodyMessage)) {
      return {
        title: translateOr(
          t,
          context === "research"
            ? "commercial.errors.researchFailedTitle"
            : "commercial.errors.genericFailedTitle",
          "Не удалось выполнить операцию",
        ),
        message: safeBodyMessage,
        actionHint: translateOr(
          t,
          "commercial.errors.retryHint",
          "Попробуйте повторить. Если ошибка повторится — обратитесь в поддержку.",
        ),
        internalCode: code,
      };
    }

    if (code) {
      const commercialKey = `commercial.errors.${code}`;
      const commercial = t(commercialKey);
      if (commercial !== commercialKey) {
        return {
          title: translateOr(
            t,
            context === "research"
              ? "commercial.errors.researchFailedTitle"
              : "commercial.errors.genericFailedTitle",
            "Не удалось выполнить операцию",
          ),
          message: commercial,
          actionHint: translateOr(
            t,
            "commercial.errors.retryHint",
            "Попробуйте повторить. Если ошибка повторится — обратитесь в поддержку.",
          ),
          internalCode: code,
        };
      }

      if (code.includes("idempotency") || code.includes("rerun")) {
        return {
          title: translateOr(
            t,
            "commercial.errors.researchRerunFailedTitle",
            "Не удалось повторно запустить исследование",
          ),
          message: translateOr(
            t,
            "commercial.errors.researchRerunFailedBody",
            "Во время подготовки нового анализа возникла внутренняя ошибка. Попробуйте повторить запуск.",
          ),
          actionHint: translateOr(
            t,
            "commercial.errors.retryHint",
            "Попробуйте повторить. Если ошибка повторится — обратитесь в поддержку.",
          ),
          internalCode: code,
        };
      }

      if (code.includes("context") || code.includes("analysis")) {
        return {
          title: translateOr(
            t,
            "commercial.errors.researchFailedTitle",
            "Не удалось завершить исследование",
          ),
          message: translateOr(
            t,
            "commercial.errors.contextMissingBody",
            "Не удалось восстановить подтверждённые данные проекта. Откройте проект и повторите.",
          ),
          actionHint: translateOr(
            t,
            "commercial.errors.retryHint",
            "Попробуйте повторить. Если ошибка повторится — обратитесь в поддержку.",
          ),
          internalCode: code,
        };
      }
    }

    if (err.status === 401) {
      return {
        title: translateOr(t, "auth.session_expired", "Сессия истекла"),
        message: translateOr(t, "auth.authentication_required", "Требуется вход."),
        actionHint: translateOr(t, "errors.hint.enter_credentials", "Войдите снова, чтобы продолжить."),
        internalCode: code,
      };
    }

    if (err.status === 403) {
      return {
        title: translateOr(t, "commercial.errors.accessDeniedTitle", "Доступ ограничен"),
        message: translateOr(
          t,
          "commercial.errors.accessDeniedBody",
          "У вас нет прав для этого действия.",
        ),
        actionHint: translateOr(t, "commercial.errors.retryHint", "Попробуйте позже или обратитесь в поддержку."),
        internalCode: code,
      };
    }

    if (err.status === 404) {
      return {
        title: translateOr(t, "commercial.errors.notFoundTitle", "Данные не найдены"),
        message: translateOr(
          t,
          "commercial.errors.notFoundBody",
          "Запрошенные данные недоступны. Обновите страницу и попробуйте снова.",
        ),
        actionHint: translateOr(t, "commercial.errors.retryHint", "Попробуйте повторить."),
        internalCode: code,
      };
    }

    if (err.status >= 500) {
      return {
        title: translateOr(
          t,
          "commercial.errors.serverFailedTitle",
          "Сервис временно недоступен",
        ),
        message: translateOr(
          t,
          "commercial.errors.serverFailedBody",
          "Не удалось завершить операцию на сервере. Попробуйте через несколько минут.",
        ),
        actionHint: translateOr(t, "commercial.errors.retryHint", "Попробуйте повторить позже."),
        internalCode: code,
      };
    }

    if (err.status === 409) {
      return {
        title: translateOr(
          t,
          context === "research"
            ? "commercial.errors.researchFailedTitle"
            : "commercial.errors.genericFailedTitle",
          "Не удалось выполнить операцию",
        ),
        message: translateOr(
          t,
          "commercial.errors.conflictBody",
          "Операция не может быть выполнена в текущем состоянии. Попробуйте ещё раз.",
        ),
        actionHint: translateOr(t, "commercial.errors.retryHint", "Попробуйте повторить."),
        internalCode: code,
      };
    }
  }

  if (err instanceof Error && err.message === "research_timeout") {
    return {
      title: translateOr(
        t,
        "commercial.errors.researchFailedTitle",
        "Исследование не удалось завершить",
      ),
      message: translateOr(
        t,
        "commercial.errors.researchTimeoutBody",
        "Анализ занял слишком много времени. Попробуйте повторить запуск.",
      ),
      actionHint: translateOr(t, "commercial.errors.retryHint", "Попробуйте повторить."),
      internalCode: "research_timeout",
    };
  }

  return {
    title: translateOr(
      t,
      context === "research"
        ? "commercial.errors.researchFailedTitle"
        : "commercial.errors.genericFailedTitle",
      "Не удалось выполнить операцию",
    ),
    message: translateOr(
      t,
      "commercial.errors.genericFailedBody",
      "Произошла непредвиденная ошибка. Попробуйте ещё раз.",
    ),
    actionHint: translateOr(
      t,
      "commercial.errors.retryHint",
      "Если ошибка повторится — обратитесь в поддержку.",
    ),
    internalCode: null,
  };
}
