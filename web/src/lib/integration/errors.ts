/**
 * Integration error normalization — never invent business progress from failures.
 */

import { ApiError } from "@/lib/api/errors";
import type { LoadState } from "@/lib/integration/contracts";

export type IntegrationErrorKind =
  | "unauthorized"
  | "forbidden"
  | "not_found"
  | "network"
  | "server"
  | "config"
  | "unknown";

export type NormalizedIntegrationError = {
  kind: IntegrationErrorKind;
  loadState: LoadState;
  message: string;
  status: number | null;
};

export function normalizeIntegrationError(err: unknown): NormalizedIntegrationError {
  if (err instanceof ApiError) {
    if (err.status === 401) {
      return {
        kind: "unauthorized",
        loadState: "unauthorized",
        message: "Требуется авторизация (API key).",
        status: 401,
      };
    }
    if (err.status === 403) {
      return {
        kind: "forbidden",
        loadState: "unauthorized",
        message: "Нет доступа к ресурсу проекта.",
        status: 403,
      };
    }
    if (err.status === 404) {
      return {
        kind: "not_found",
        loadState: "empty",
        message: "Ресурс не найден.",
        status: 404,
      };
    }
    return {
      kind: "server",
      loadState: "error",
      message: "Данные недоступны — ошибка API.",
      status: err.status,
    };
  }

  if (err instanceof TypeError) {
    return {
      kind: "network",
      loadState: "error",
      message: "Backend не подключён или недоступен.",
      status: null,
    };
  }

  return {
    kind: "unknown",
    loadState: "error",
    message: "Данные недоступны.",
    status: null,
  };
}

export function unavailableLabel(): string {
  return "Недоступно";
}
