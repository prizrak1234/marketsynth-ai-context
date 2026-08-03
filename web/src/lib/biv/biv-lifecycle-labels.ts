import type { BusinessIdeaValidationProjectLatestRunSummary } from "@/lib/api/endpoints/business-idea-validation";

export const BIV_LIFECYCLE_NOT_CHECKED = "Не проверялось";
export const BIV_LIFECYCLE_QUEUED = "Исследование запланировано";
export const BIV_LIFECYCLE_RUNNING = "Исследование выполняется";
export const BIV_LIFECYCLE_SUCCEEDED = "Исследование завершено";
export const BIV_LIFECYCLE_PARTIAL = "Результат ограничен данными";
export const BIV_LIFECYCLE_FAILED = "Исследование прервано";

export function bivLifecycleStatusLabel(
  summary: BusinessIdeaValidationProjectLatestRunSummary | null | undefined,
): string | null {
  if (!summary) {
    return null;
  }
  if (summary.status === "queued") {
    return BIV_LIFECYCLE_QUEUED;
  }
  if (summary.status === "running") {
    return BIV_LIFECYCLE_RUNNING;
  }
  if (summary.status === "succeeded") {
    return BIV_LIFECYCLE_SUCCEEDED;
  }
  if (summary.status === "failed") {
    if (summary.result_kind === "partial_research") {
      return BIV_LIFECYCLE_PARTIAL;
    }
    return BIV_LIFECYCLE_FAILED;
  }
  return null;
}

export function isActiveBivRunStatus(status: string): boolean {
  return status === "queued" || status === "running";
}

export function workspaceProjectLifecycleLabel(input: {
  bivLifecycleLabel?: string | null;
  bivHydrationError?: boolean;
  projectName: string;
  statusLabel?: string;
}): string {
  if (input.bivHydrationError) {
    return "Данные временно недоступны";
  }
  if (input.bivLifecycleLabel) {
    return input.bivLifecycleLabel;
  }
  if (input.projectName && input.projectName !== "Новый проект") {
    return BIV_LIFECYCLE_NOT_CHECKED;
  }
  return BIV_LIFECYCLE_NOT_CHECKED;
}
