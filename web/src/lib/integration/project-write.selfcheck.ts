/**
 * Integration I2 selfcheck — intake → Project mapping + sync guards.
 * Run from web/: npx --yes tsx src/lib/integration/project-write.selfcheck.ts
 */

import { ApiError } from "@/lib/api/errors";
import {
  buildProjectDescription,
  buildProjectName,
  buildSubmissionFingerprint,
  LOCAL_ONLY_INTAKE_SECTIONS,
  mapIntakeToProjectCreate,
  mapIntakeToProjectUpdate,
  PERSISTED_INTAKE_FIELDS,
  readConfigPointer,
} from "@/lib/integration/intake-project-mapping";
import {
  ambiguousCreateError,
  normalizeProjectWriteError,
} from "@/lib/integration/project-write-adapter";
import { primaryCtaLabel } from "@/lib/integration/project-sync";
import { createEmptyDraft } from "@/lib/project-intake/schema";
import { canStartInvestigation, evaluateIntakeReadiness } from "@/lib/project-intake/readiness";
import type { ProjectIntakeDraft } from "@/lib/project-intake/types";

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}

function fillMinimal(draft: ProjectIntakeDraft): ProjectIntakeDraft {
  return {
    ...draft,
    projectBasics: {
      name: "Clinic leads",
      ideaDescription: "Проверить спрос на лидогенерацию для стоматологий в Москве",
      businessType: "local_business",
      projectStage: "validating_demand",
      geography: "Москва",
      interfaceLanguage: "ru",
    },
    product: {
      ...draft.product,
      whatIsSold: "Пакет лидов в клинику",
      primaryProblem: "Пустующее расписание",
      valueProposition: "Квалифицированные заявки",
      priceUnknown: true,
      deliveryUnknown: false,
      deliveryModel: "онлайн",
    },
    market: {
      ...draft.market,
      targetMarket: "Частные стоматологии",
      geography: "Москва",
      competitorsUnknown: true,
      demandUnavailable: true,
    },
    audience: {
      ...draft.audience,
      customerModel: "b2b",
      segments: [{ id: "s1", label: "Владельцы клиник", notes: "Ищут поток пациентов" }],
      expectedPains: "Дорогая реклама",
    },
    economics: {
      ...draft.economics,
      launchBudget: { mode: "range", min: "100000", max: "300000" },
      monthlyMarketingBudget: { mode: "unknown" },
      criticalConstraints: "Ограниченный cashflow",
    },
    materials: {
      websiteUrl: "https://example.clinic",
      socialProfiles: "",
      items: [{ id: "m1", kind: "document", label: "Прайс", note: "mock" }],
    },
  };
}

{
  const draft = fillMinimal(createEmptyDraft());
  const create = mapIntakeToProjectCreate(draft);
  assert(create.name === "Clinic leads", "create maps name");
  assert(
    Boolean(create.description && create.description.includes("лидогенерацию")),
    "create maps description from idea",
  );
  assert(!("config" in create), "create must not dump full draft config");
  assert(PERSISTED_INTAKE_FIELDS.length >= 2, "persisted field list present");
  assert(LOCAL_ONLY_INTAKE_SECTIONS.some((s) => s.includes("market")), "market stays local");
}

{
  const draft = fillMinimal(createEmptyDraft());
  const fp = buildSubmissionFingerprint(draft);
  const update = mapIntakeToProjectUpdate(draft, fp);
  assert(update.name === buildProjectName(draft), "update name");
  assert(update.description === buildProjectDescription(draft), "update description");
  const pointer = readConfigPointer(update.config);
  assert(pointer?.localDraftId === draft.id, "config pointer draft id");
  assert(pointer?.submissionFingerprint === fp, "config pointer fingerprint");
  // Ensure full sections are NOT in config
  const raw = JSON.stringify(update.config);
  assert(!raw.includes("expectedPains"), "audience pains not dumped into config");
  assert(!raw.includes("Прайс"), "materials not dumped into config");
}

{
  const a = fillMinimal(createEmptyDraft());
  const b = fillMinimal({ ...createEmptyDraft(), id: a.id });
  assert(
    buildSubmissionFingerprint(a) === buildSubmissionFingerprint({ ...b, id: a.id }),
    "fingerprint stable for same core",
  );
  const renamed = {
    ...a,
    projectBasics: { ...a.projectBasics, name: "Other" },
  };
  assert(
    buildSubmissionFingerprint(a) !== buildSubmissionFingerprint(renamed),
    "fingerprint changes with name",
  );
}

{
  assert(normalizeProjectWriteError(new ApiError("x", 401, null)).kind === "unauthorized", "401");
  assert(normalizeProjectWriteError(new ApiError("x", 403, null)).kind === "forbidden", "403");
  assert(normalizeProjectWriteError(new ApiError("x", 404, null)).kind === "project_not_found", "404");
  assert(normalizeProjectWriteError(new TypeError("fetch")).kind === "network_error", "network");
  assert(ambiguousCreateError().kind === "ambiguous_create_result", "ambiguous");
  assert(
    ambiguousCreateError().message.toLowerCase().includes("повторный post"),
    "ambiguous blocks auto POST",
  );
}

{
  assert(primaryCtaLabel("mock", null) === "Начать исследование (mock)", "mock CTA");
  assert(
    primaryCtaLabel("backend", null) === "Запустить исследование",
    "backend golden path CTA",
  );
  assert(
    primaryCtaLabel("hybrid", {
      backendProjectId: "uuid-1",
      backendSyncState: "partially_synced",
      backendSyncedAt: "2026-01-01",
      backendUpdatedAt: "2026-01-01",
      lastSyncError: null,
      submissionFingerprint: "fp",
      localDraftVersion: "v",
    }) === "Запустить исследование",
    "update CTA after sync",
  );
}

{
  const draft = fillMinimal(createEmptyDraft());
  const readiness = evaluateIntakeReadiness(draft);
  assert(canStartInvestigation(readiness), "intake readiness independent of backend status");
  assert(draft.backendSync?.backendSyncState === "local_only", "starts local_only");
  // Simulate link metadata without inventing Investigation backend
  const linked: ProjectIntakeDraft = {
    ...draft,
    backendSync: {
      backendProjectId: "11111111-1111-1111-1111-111111111111",
      backendSyncState: "partially_synced",
      backendSyncedAt: "2026-07-13T00:00:00Z",
      backendUpdatedAt: "2026-07-13T00:00:00Z",
      lastSyncError: null,
      submissionFingerprint: buildSubmissionFingerprint(draft),
      localDraftVersion: draft.updatedAt,
    },
  };
  assert(linked.market.targetMarket.length > 0, "unsupported market kept on draft");
  assert(linked.materials.items.length === 1, "materials remain local");
  assert(
    linked.backendSync?.backendSyncState === "partially_synced",
    "honest partial sync — full brief not backend",
  );
}

console.log("project-write.selfcheck.ts: OK");
