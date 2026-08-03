/**
 * P1.1 — handoff preview adapter (read-only; no MarketingPlan create).
 */

import type { BackendImplementationHandoffPreviewDto } from "@/lib/api/types/implementation-plans";

export type ImplementationHandoffPreviewView = {
  eligible: boolean;
  mappedTaskCount: number;
  unsupportedTaskCount: number;
  blockedTaskCount: number;
  unsupportedRoles: string[];
  blockers: string[];
  readiness: string;
  createsMarketingPlan: false;
  createsSpecialistTasks: false;
  ctaLabel: string;
  forbiddenCtAs: string[];
  note: string;
};

export function mapHandoffPreview(
  dto: BackendImplementationHandoffPreviewDto,
): ImplementationHandoffPreviewView {
  return {
    eligible: dto.eligible,
    mappedTaskCount: dto.mapped_task_count,
    unsupportedTaskCount: dto.unsupported_task_count,
    blockedTaskCount: dto.blocked_task_count,
    unsupportedRoles: dto.unsupported_roles,
    blockers: dto.blockers,
    readiness: dto.readiness,
    createsMarketingPlan: false,
    createsSpecialistTasks: false,
    ctaLabel: "Проверить готовность к передаче в MarketingPlan",
    forbiddenCtAs: [
      "Создать MarketingPlan",
      "Запустить агента",
      "Назначить специалистам",
    ],
    note: dto.note,
  };
}
