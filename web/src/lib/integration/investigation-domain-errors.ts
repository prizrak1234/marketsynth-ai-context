/**
 * P0.2 — Investigation domain error normalization.
 * Never convert domain errors into mock Investigation success in backend mode.
 */

import { ApiError } from "@/lib/api/errors";

export type InvestigationDomainErrorKind =
  | "investigation_not_found"
  | "project_not_found"
  | "brief_not_found"
  | "brief_not_submitted"
  | "brief_version_mismatch"
  | "fingerprint_mismatch"
  | "active_investigation_exists"
  | "invalid_transition"
  | "stale_version"
  | "unauthorized"
  | "forbidden"
  | "backend_unavailable"
  | "local_backend_conflict"
  | "unsupported_source_domain"
  | "unsupported_evidence_domain"
  | "unknown_error";

export type InvestigationDomainError = {
  kind: InvestigationDomainErrorKind;
  message: string;
  status: number | null;
  actionHint: string;
};

const SAFE_KIND_MAP: Record<string, InvestigationDomainErrorKind> = {
  investigation_not_found: "investigation_not_found",
  project_not_found: "project_not_found",
  brief_not_found: "brief_not_found",
  brief_not_submitted: "brief_not_submitted",
  brief_version_mismatch: "brief_version_mismatch",
  fingerprint_mismatch: "fingerprint_mismatch",
  active_investigation_exists: "active_investigation_exists",
  investigation_invalid_transition: "invalid_transition",
  invalid_transition: "invalid_transition",
  stale_version: "stale_version",
};

function messageFor(kind: InvestigationDomainErrorKind): { message: string; hint: string } {
  switch (kind) {
    case "brief_not_submitted":
      return {
        message: "Нужен submitted ProjectBrief.",
        hint: "Сохраните и отправьте полный бриф, затем создайте исследование.",
      };
    case "brief_version_mismatch":
    case "fingerprint_mismatch":
      return {
        message: "Версия или fingerprint брифа не совпадают.",
        hint: "Перезагрузите submitted ProjectBrief и повторите создание.",
      };
    case "active_investigation_exists":
      return {
        message: "Уже есть active Investigation.",
        hint: "Завершите или supersede текущее исследование.",
      };
    case "invalid_transition":
      return {
        message: "Недопустимый переход lifecycle.",
        hint: "Проверьте текущий статус Investigation.",
      };
    case "unsupported_source_domain":
      return {
        message: "Source domain недоступен до P0.3.",
        hint: "Не ожидайте durable Source в P0.2.",
      };
    case "unsupported_evidence_domain":
      return {
        message: "Evidence domain недоступен до P0.4.",
        hint: "Не ожидайте durable Evidence в P0.2.",
      };
    case "local_backend_conflict":
      return {
        message: "Локальный stage state конфликтует с backend.",
        hint: "Backend lifecycle побеждает; локальные артефакты — preview.",
      };
    case "investigation_not_found":
      return {
        message: "Investigation не найдено.",
        hint: "Создайте Investigation явно кнопкой «Создать исследование».",
      };
    default:
      return {
        message: "Ошибка Investigation domain.",
        hint: "Повторите или вернитесь в Workspace.",
      };
  }
}

export function normalizeInvestigationDomainError(err: unknown): InvestigationDomainError {
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
        kind: "investigation_not_found",
        message: "Investigation или Project не найдены.",
        status: 404,
        actionHint: "Создайте Investigation явно — page load ничего не создаёт.",
      };
    }
    if (err.status >= 500) {
      return {
        kind: "backend_unavailable",
        message: "Backend недоступен.",
        status: err.status,
        actionHint: "Mock Investigation не подставляется в backend mode.",
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
    const kind = SAFE_KIND_MAP[raw] ?? "unknown_error";
    const copy = messageFor(kind);
    return {
      kind,
      message: kind === "unknown_error" && raw ? raw : copy.message,
      status: err.status,
      actionHint: copy.hint,
    };
  }

  return {
    kind: "unknown_error",
    message: "Неизвестная ошибка Investigation.",
    status: null,
    actionHint: "Обновите страницу.",
  };
}

export function unsupportedSourceDomainError(): InvestigationDomainError {
  return {
    kind: "unsupported_source_domain",
    ...messageFor("unsupported_source_domain"),
    status: null,
    actionHint: messageFor("unsupported_source_domain").hint,
  };
}

export function unsupportedEvidenceDomainError(): InvestigationDomainError {
  return {
    kind: "unsupported_evidence_domain",
    ...messageFor("unsupported_evidence_domain"),
    status: null,
    actionHint: messageFor("unsupported_evidence_domain").hint,
  };
}
