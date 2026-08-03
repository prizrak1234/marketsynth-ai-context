/**
 * P0.3 — Source domain error normalization.
 * Never convert errors into mock Source success in backend mode.
 */

import { ApiError } from "@/lib/api/errors";

export type SourceErrorKind =
  | "source_not_found"
  | "project_not_found"
  | "investigation_not_found"
  | "unauthorized"
  | "forbidden"
  | "duplicate_source"
  | "fingerprint_conflict"
  | "immutable_source"
  | "invalid_transition"
  | "cross_project_link"
  | "invalid_provenance"
  | "invalid_capability"
  | "stale_version"
  | "backend_unavailable"
  | "network_error"
  | "unsupported_fetch"
  | "unsupported_file_upload"
  | "unknown_error";

export type SourceError = {
  kind: SourceErrorKind;
  message: string;
  status: number | null;
  actionHint: string;
};

const SAFE: Record<string, SourceErrorKind> = {
  duplicate_source: "duplicate_source",
  fingerprint_conflict: "fingerprint_conflict",
  immutable_source: "immutable_source",
  invalid_transition: "invalid_transition",
  cross_project_link: "cross_project_link",
  invalid_provenance: "invalid_provenance",
  invalid_capability: "invalid_capability",
  source_not_found: "source_not_found",
  investigation_not_found: "investigation_not_found",
};

export function normalizeSourceError(err: unknown): SourceError {
  if (err instanceof ApiError) {
    if (err.status === 401) {
      return {
        kind: "unauthorized",
        message: "Требуется авторизация.",
        status: 401,
        actionHint: "Укажите API key.",
      };
    }
    if (err.status === 403) {
      return {
        kind: "forbidden",
        message: "Нет доступа.",
        status: 403,
        actionHint: "Проверьте владельца проекта.",
      };
    }
    if (err.status === 404) {
      return {
        kind: "source_not_found",
        message: "Source или Project не найдены.",
        status: 404,
        actionHint: "Зарегистрируйте источник явно — page load ничего не создаёт.",
      };
    }
    if (err.status >= 500) {
      return {
        kind: "backend_unavailable",
        message: "Backend недоступен.",
        status: err.status,
        actionHint: "Mock Source не подставляется в backend mode.",
      };
    }
    const body = err.body;
    const raw =
      (typeof body === "object" &&
        body &&
        "safe_message" in body &&
        String((body as { safe_message?: string }).safe_message)) ||
      (typeof body === "object" &&
        body &&
        "detail" in body &&
        String((body as { detail?: string }).detail)) ||
      err.message ||
      "";
    const kind = SAFE[raw] ?? "unknown_error";
    return {
      kind,
      message:
        kind === "duplicate_source"
          ? "Такой Source уже зарегистрирован."
          : kind === "unsupported_fetch"
            ? "Fetch URL не поддерживается в P0.3."
            : "Ошибка Source domain.",
      status: err.status,
      actionHint:
        kind === "duplicate_source"
          ? "Прикрепите существующий Source к Investigation."
          : "Проверьте метаданные происхождения.",
    };
  }
  if (err instanceof TypeError) {
    return {
      kind: "network_error",
      message: "Сеть недоступна.",
      status: null,
      actionHint: "Повторите позже.",
    };
  }
  return {
    kind: "unknown_error",
    message: "Неизвестная ошибка Source.",
    status: null,
    actionHint: "Обновите страницу.",
  };
}

export function unsupportedFetchError(): SourceError {
  return {
    kind: "unsupported_fetch",
    message: "Автоматическая загрузка URL не выполняется.",
    status: null,
    actionHint: "Сохраняется только provenance metadata.",
  };
}

export function unsupportedUploadError(): SourceError {
  return {
    kind: "unsupported_file_upload",
    message: "Загрузка файлов не реализована в P0.3.",
    status: null,
    actionHint: "Зарегистрируйте метаданные документа без бинарного содержимого.",
  };
}
