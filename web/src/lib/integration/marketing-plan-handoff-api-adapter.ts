/**
 * P1.2 — controlled MarketingPlan draft handoff API adapter.
 */

import {
  confirmMarketingPlanHandoff,
  previewMarketingPlanHandoff,
} from "@/lib/api/endpoints/marketing-plan-handoff";
import type { BackendMarketingPlanHandoffConfirmDto } from "@/lib/api/types/marketing-plan-handoff";
import { getIntegrationMode } from "@/lib/integration/mode";
import {
  normalizeMarketingPlanHandoffError,
  type MarketingPlanHandoffError,
} from "@/lib/integration/marketing-plan-handoff-errors";
import {
  mapMarketingPlanHandoffPreview,
  type MarketingPlanHandoffPreviewView,
} from "@/lib/integration/marketing-plan-handoff-preview-adapter";

export type MarketingPlanHandoffResultView = {
  handoffId: string;
  marketingPlanId: string;
  marketingPlanVersion: number;
  marketingPlanStatus: string;
  mappingFingerprint: string;
  includedTaskCount: number;
  excludedTaskCount: number;
  blockedTaskCount: number;
  warnings: string[];
  idempotentReplay: boolean;
  createsApproval: false;
  createsAgentRun: false;
  createsCampaign: false;
  dispatchesTasks: false;
  sideEffects: string[];
  notice: string;
};

function mapConfirm(dto: BackendMarketingPlanHandoffConfirmDto): MarketingPlanHandoffResultView {
  return {
    handoffId: dto.handoff_id,
    marketingPlanId: dto.marketing_plan_id,
    marketingPlanVersion: dto.marketing_plan_version,
    marketingPlanStatus: dto.marketing_plan_status,
    mappingFingerprint: dto.mapping_fingerprint,
    includedTaskCount: dto.included_task_count,
    excludedTaskCount: dto.excluded_task_count,
    blockedTaskCount: dto.blocked_task_count,
    warnings: dto.warnings,
    idempotentReplay: dto.idempotent_replay,
    createsApproval: false,
    createsAgentRun: false,
    createsCampaign: false,
    dispatchesTasks: false,
    sideEffects: dto.side_effects,
    notice:
      "MarketingPlan draft создан. Ничего не исполнено: no approve, no specialist dispatch, no Campaign, no Agent Run.",
  };
}

export async function requestMarketingPlanHandoffPreview(args: {
  projectId: string;
  implementationPlanId: string;
}): Promise<
  | { ok: true; view: MarketingPlanHandoffPreviewView }
  | { ok: false; error: MarketingPlanHandoffError }
> {
  const mode = getIntegrationMode();
  if (mode === "mock") {
    return {
      ok: false,
      error: {
        kind: "backend_unavailable",
        message: "MOCK: backend MarketingPlan handoff недоступен.",
        status: null,
        actionHint: "Переключите integration mode на backend/hybrid с durable ImplementationPlan.",
      },
    };
  }
  try {
    const dto = await previewMarketingPlanHandoff(
      args.projectId,
      args.implementationPlanId,
    );
    return { ok: true, view: mapMarketingPlanHandoffPreview(dto) };
  } catch (err) {
    return { ok: false, error: normalizeMarketingPlanHandoffError(err) };
  }
}

export async function confirmMarketingPlanHandoffDraft(args: {
  projectId: string;
  implementationPlanId: string;
  handoffPreviewId: string;
  mappingFingerprint: string;
  expectedImplementationPlanVersion: number;
  explicitConfirmation: boolean;
  note?: string;
}): Promise<
  | { ok: true; view: MarketingPlanHandoffResultView }
  | { ok: false; error: MarketingPlanHandoffError }
> {
  const mode = getIntegrationMode();
  if (mode === "mock") {
    return {
      ok: false,
      error: {
        kind: "backend_unavailable",
        message: "MOCK: создание MarketingPlan draft через handoff запрещено.",
        status: null,
        actionHint: "Используйте backend/hybrid с durable approved ImplementationPlan.",
      },
    };
  }
  if (!args.explicitConfirmation) {
    return {
      ok: false,
      error: {
        kind: "explicit_confirmation_required",
        message: "explicit_confirmation_required",
        status: null,
        actionHint: "Отметьте «Создать только черновик MarketingPlan».",
      },
    };
  }
  try {
    const dto = await confirmMarketingPlanHandoff(
      args.projectId,
      args.implementationPlanId,
      {
        handoff_preview_id: args.handoffPreviewId,
        mapping_fingerprint: args.mappingFingerprint,
        expected_implementation_plan_version: args.expectedImplementationPlanVersion,
        explicit_confirmation: true,
        existing_plan_policy: "create_new_draft",
        note: args.note,
      },
    );
    return { ok: true, view: mapConfirm(dto) };
  } catch (err) {
    return { ok: false, error: normalizeMarketingPlanHandoffError(err) };
  }
}
