/**
 * PRODUCT-01.3A-OWNER-FAIL-01 — brief submit → project → confirm → BIV run.
 */

import {
  confirmAnalysisContext,
  createAnalysisContextDraft,
  type AnalysisContextRecord,
} from "@/lib/api/endpoints/analysis-contexts";
import {
  buildResearchIdempotencyKey,
  startBusinessIdeaValidationRun,
} from "@/lib/api/endpoints/business-idea-validation";
import { fetchProject } from "@/lib/api/endpoints/projects";
import { createUserRequest } from "@/lib/api/endpoints/user-requests";
import { persistActiveResearchSession } from "@/lib/biv/active-research-session";
import {
  intakeDraftMeetsAnalysisContextGate,
  mapIntakeDraftToAnalysisContextFields,
} from "@/lib/integration/intake-draft-to-analysis-context";
import { syncIntakeBrief } from "@/lib/integration/project-brief-sync";
import { syncIntakeProject } from "@/lib/integration/project-sync";
import {
  canStartInvestigation,
  evaluateIntakeReadiness,
} from "@/lib/project-intake/readiness";
import type { ProjectIntakeDraft } from "@/lib/project-intake/types";

export type IntakeGoldenPathStage =
  | "readiness"
  | "project_sync"
  | "project_verify"
  | "brief_sync"
  | "analysis_context"
  | "confirm"
  | "user_request"
  | "research_run";

export type IntakeGoldenPathSuccess = {
  ok: true;
  projectId: string;
  briefId: string;
  analysisContextId: string;
  inputSnapshotHash: string;
  userRequestId: string;
  runId: string | null;
  context: AnalysisContextRecord;
  draft: ProjectIntakeDraft;
};

export type IntakeGoldenPathFailure = {
  ok: false;
  stage: IntakeGoldenPathStage;
  message: string;
  actionHint: string;
  draft: ProjectIntakeDraft;
};

export type IntakeGoldenPathResult = IntakeGoldenPathSuccess | IntakeGoldenPathFailure;

export async function executeIntakeBriefGoldenPath(
  draft: ProjectIntakeDraft,
): Promise<IntakeGoldenPathResult> {
  const readiness = evaluateIntakeReadiness(draft);
  if (!canStartInvestigation(readiness)) {
    return {
      ok: false,
      stage: "readiness",
      message: "Недостаточно данных для старта исследования.",
      actionHint: "Дополните критические поля брифа.",
      draft,
    };
  }

  const gate = intakeDraftMeetsAnalysisContextGate(draft);
  if (!gate.ok) {
    return {
      ok: false,
      stage: "analysis_context",
      message: `Бриф не проходит gate анализа: ${gate.missing_fields.join(", ")}`,
      actionHint: "Уточните поля, необходимые для исследования.",
      draft,
    };
  }

  const projectSync = await syncIntakeProject({ ...draft, readiness });
  if (!projectSync.ok) {
    return {
      ok: false,
      stage: "project_sync",
      message: projectSync.error.message,
      actionHint: projectSync.error.actionHint,
      draft: projectSync.draft,
    };
  }

  let workingDraft = projectSync.draft;
  const projectId = projectSync.projectId;

  try {
    await fetchProject(projectId);
  } catch {
    return {
      ok: false,
      stage: "project_verify",
      message: "Backend project не найден после сохранения.",
      actionHint: "Повторите сохранение или создайте новый бриф.",
      draft: workingDraft,
    };
  }

  const briefSync = await syncIntakeBrief(workingDraft, { submit: true });
  workingDraft = briefSync.draft;
  if (!briefSync.ok) {
    return {
      ok: false,
      stage: "brief_sync",
      message: briefSync.error.message,
      actionHint: briefSync.error.actionHint,
      draft: workingDraft,
    };
  }

  const fields = mapIntakeDraftToAnalysisContextFields(workingDraft);
  let context: AnalysisContextRecord;
  try {
    context = await createAnalysisContextDraft(projectId, fields);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Не удалось создать analysis context.";
    return {
      ok: false,
      stage: "analysis_context",
      message,
      actionHint: "Проверьте заполнение брифа и повторите.",
      draft: workingDraft,
    };
  }

  if (!context.input_snapshot_hash) {
    return {
      ok: false,
      stage: "analysis_context",
      message: "Analysis context создан без input_snapshot_hash.",
      actionHint: "Повторите submit после обновления страницы.",
      draft: workingDraft,
    };
  }

  let confirmed: AnalysisContextRecord;
  try {
    confirmed = await confirmAnalysisContext(
      projectId,
      context.context_id,
      context.input_snapshot_hash,
    );
  } catch (err) {
    const message = err instanceof Error ? err.message : "Не удалось подтвердить analysis context.";
    return {
      ok: false,
      stage: "confirm",
      message,
      actionHint: "Проверьте обязательные поля и повторите.",
      draft: workingDraft,
    };
  }

  if (!confirmed.confirmed_by_user || !confirmed.input_snapshot_hash) {
    return {
      ok: false,
      stage: "confirm",
      message: "Analysis context не подтверждён.",
      actionHint: "Повторите submit после проверки полей.",
      draft: workingDraft,
    };
  }

  let userRequestId: string;
  try {
    const userRequest = await createUserRequest({
      text: confirmed.idea_description,
      selected_scenario: "idea_validation",
      skill_inputs: {
        home_agency_flow: "v2",
        analysis_intent: "business_viability_research",
        analysis_context_id: confirmed.context_id,
        intake_wizard: "project_intake_v1",
      },
    });
    userRequestId = userRequest.id;
  } catch (err) {
    const message = err instanceof Error ? err.message : "Не удалось создать user request.";
    return {
      ok: false,
      stage: "user_request",
      message,
      actionHint: "Проверьте сессию и повторите.",
      draft: workingDraft,
    };
  }

  const idempotencyKey = buildResearchIdempotencyKey(
    confirmed.context_id,
    confirmed.input_snapshot_hash,
  );

  persistActiveResearchSession({
    projectId,
    userRequestId,
    contextId: confirmed.context_id,
    inputSnapshotHash: confirmed.input_snapshot_hash,
    startedAt: Date.now(),
  });

  try {
    const accepted = await startBusinessIdeaValidationRun(userRequestId, {
      idempotency_key: idempotencyKey,
      research_mode: "initial",
      analysis_context_id: confirmed.context_id,
      input_snapshot_hash: confirmed.input_snapshot_hash,
      idea: confirmed.idea_description,
      location: confirmed.geography ?? undefined,
      target_audience: confirmed.target_customer ?? undefined,
      market: confirmed.business_model ?? undefined,
      budget: confirmed.budget_context ?? undefined,
      constraints: confirmed.known_competitors ?? undefined,
    });

    persistActiveResearchSession({
      projectId,
      userRequestId,
      contextId: confirmed.context_id,
      inputSnapshotHash: confirmed.input_snapshot_hash,
      runId: accepted.run_id,
      startedAt: Date.now(),
    });

    return {
      ok: true,
      projectId,
      briefId: briefSync.brief.id,
      analysisContextId: confirmed.context_id,
      inputSnapshotHash: confirmed.input_snapshot_hash,
      userRequestId,
      runId: accepted.run_id,
      context: confirmed,
      draft: workingDraft,
    };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Не удалось запустить исследование.";
    return {
      ok: false,
      stage: "research_run",
      message,
      actionHint: "Проект сохранён. Откройте Workspace и повторите запуск.",
      draft: workingDraft,
    };
  }
}

export function workspaceUrlAfterGoldenPath(projectId: string): string {
  return `/workspace?project=${encodeURIComponent(projectId)}`;
}
