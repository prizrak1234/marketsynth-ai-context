import type {
  BusinessType,
  CustomerModel,
  IntakeReadinessResult,
  IntakeReadinessStatus,
  MoneyValue,
  ProjectStage,
} from "@/lib/project-intake/types";
import {
  BUSINESS_TYPE_OPTIONS,
  CUSTOMER_MODEL_OPTIONS,
  PROJECT_STAGE_OPTIONS,
} from "@/lib/project-intake/schema";

export function customerReadinessLabel(status: IntakeReadinessStatus): string {
  if (status === "ready") return "Готово к исследованию";
  if (status === "conditionally_ready") return "Можно начинать, но есть вопросы";
  return "Нужно дополнить данные";
}

export function customerReadinessHint(status: IntakeReadinessStatus): string {
  if (status === "ready") {
    return "Бриф достаточно полный — можно запускать проверку идеи.";
  }
  if (status === "conditionally_ready") {
    return "Исследование можно начать; открытые вопросы агентство отметит в процессе.";
  }
  return "Дополните обязательные поля, прежде чем запускать исследование.";
}

export function customerReadinessColor(status: IntakeReadinessStatus): string {
  if (status === "ready") return "var(--ms-status-success)";
  if (status === "conditionally_ready") return "var(--brand-blue-light)";
  return "var(--ms-status-danger)";
}

export function readinessStatusTone(
  status: IntakeReadinessStatus,
): "success" | "warning" | "danger" {
  if (status === "ready") return "success";
  if (status === "conditionally_ready") return "warning";
  return "danger";
}

export function formatMoneyValue(m: MoneyValue, unknownFlag?: boolean): string {
  if (unknownFlag || m.mode === "unknown") return "Пока не указано";
  if (m.mode === "exact") return m.exact?.trim() || "—";
  if (m.mode === "range") {
    const min = m.min?.trim();
    const max = m.max?.trim();
    if (min && max) return `${min} – ${max}`;
    if (min) return `от ${min}`;
    if (max) return `до ${max}`;
    return "—";
  }
  return "—";
}

function optionLabel<T extends string>(
  options: ReadonlyArray<{ value: T; label: string }>,
  value: T | "",
): string {
  if (!value) return "—";
  return options.find((o) => o.value === value)?.label ?? value;
}

export function customerBusinessTypeLabel(value: BusinessType | ""): string {
  return optionLabel(BUSINESS_TYPE_OPTIONS, value);
}

export function customerProjectStageLabel(value: ProjectStage | ""): string {
  return optionLabel(PROJECT_STAGE_OPTIONS, value);
}

export function customerAudienceModelLabel(value: CustomerModel | "unknown" | ""): string {
  if (!value || value === "unknown") return "Пока не указано";
  return optionLabel(CUSTOMER_MODEL_OPTIONS, value);
}

export function customerClarifications(readiness: IntakeReadinessResult): string[] {
  return [
    ...readiness.missingCritical,
    ...readiness.missingOptional,
    ...readiness.contradictions,
    ...readiness.recommendedAdditions.filter(
      (item) => !item.includes("Investigation") && !item.toLowerCase().includes("brief"),
    ),
  ].slice(0, 8);
}
