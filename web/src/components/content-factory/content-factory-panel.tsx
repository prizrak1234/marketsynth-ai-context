"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ContentFactoryMaterialCard } from "@/components/content-factory/content-factory-material-card";
import { ContentFactoryMaterialEditor } from "@/components/content-factory/content-factory-material-editor";
import { ContentFactoryPackagePanel } from "@/components/content-factory/content-factory-package-panel";
import { ContentFactoryPublishPanel } from "@/components/content-factory/content-factory-publish-panel";
import { Button } from "@/components/ui/button";
import { createContentAsset, fetchContentAssets } from "@/lib/api/endpoints/content-assets";
import {
  fetchContentFactoryProviderReadiness,
  generateContentFactoryMaterials,
  type ContentFactoryGenerationStage,
} from "@/lib/api/endpoints/content-factory";
import { fetchProjects } from "@/lib/api/endpoints/projects";
import { backendChannelForProduct } from "@/lib/content-factory/labels";
import {
  CONTENT_FACTORY_CHANNEL_OPTIONS,
  isDemoMaterial,
  labelMaterialStatus,
  labelProductChannel,
  type ContentFactoryProductChannelId,
} from "@/lib/content-factory/labels";
import type { ContentFactoryBriefSeed } from "@/lib/home/content-factory-owner-preview";
import { useLocale } from "@/lib/i18n";

type ContentFactoryStep = "prepare" | "plan" | "materials" | "package" | "publish";

type BriefForm = ContentFactoryBriefSeed & {
  channel: ContentFactoryProductChannelId;
  topic: string;
  goal: string;
  audience: string;
  period: string;
  frequency: string;
  format: string;
  sourceMaterials: string;
};

const DEFAULT_BRIEF: BriefForm = {
  channel: "telegram",
  topic: "",
  goal: "",
  audience: "",
  period: "",
  frequency: "",
  format: "",
  sourceMaterials: "",
};

const MIN_MATERIALS = 3;

type ContentFactoryPanelProps = {
  initialProjectId?: string | null;
  /** Owner preview only — demo materials stay separated from commercial generation. */
  allowDemoMaterials?: boolean;
  /** Commercial Home — project comes from verdict/project context. */
  hideProjectSelect?: boolean;
  /** Seed brief fields from agency verdict context. */
  initialBrief?: Partial<ContentFactoryBriefSeed>;
  /** Product copy without preview/diagnostic terminology. */
  commercialMode?: boolean;
};

export function ContentFactoryPanel({
  initialProjectId = null,
  allowDemoMaterials = false,
  hideProjectSelect = false,
  initialBrief,
  commercialMode = false,
}: ContentFactoryPanelProps) {
  const { t, locale } = useLocale();
  const queryClient = useQueryClient();
  const [step, setStep] = useState<ContentFactoryStep>("prepare");
  const [brief, setBrief] = useState<BriefForm>(() => ({
    ...DEFAULT_BRIEF,
    ...initialBrief,
  }));
  const [projectId, setProjectId] = useState<string | null>(initialProjectId);
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);
  const [openedAssetId, setOpenedAssetId] = useState<string | null>(null);
  const [packageId, setPackageId] = useState<string | null>(null);
  const [generationStage, setGenerationStage] = useState<ContentFactoryGenerationStage | null>(
    null,
  );
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [idempotencyKey] = useState(
    () => `cf-${typeof crypto !== "undefined" ? crypto.randomUUID() : Date.now()}`,
  );

  useEffect(() => {
    if (initialProjectId) {
      setProjectId(initialProjectId);
    }
  }, [initialProjectId]);

  useEffect(() => {
    if (!initialBrief) return;
    setBrief((prev) => ({ ...prev, ...initialBrief }));
  }, [initialBrief]);

  const prepareHintKey = commercialMode
    ? "contentFactory.prepare.commercialHint"
    : "contentFactory.prepare.hint";
  const stepsLabelKey = commercialMode
    ? "contentFactory.commercialStepsLabel"
    : "contentFactory.stepsLabel";
  const needMoreMaterialsKey = commercialMode
    ? "contentFactory.plan.needMoreExistingMaterials"
    : "contentFactory.plan.needMoreMaterials";

  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: fetchProjects,
  });

  const assetsQuery = useQuery({
    queryKey: ["projects", projectId, "content-assets"],
    queryFn: () => fetchContentAssets(projectId!, { include_archived: false }),
    enabled: Boolean(projectId),
  });

  const providerReadinessQuery = useQuery({
    queryKey: ["projects", projectId, "content-factory-provider-readiness"],
    queryFn: () => fetchContentFactoryProviderReadiness(projectId!),
    enabled: Boolean(projectId) && !allowDemoMaterials,
  });

  const materials = useMemo(
    () => (assetsQuery.data ?? []).filter((row) => row.status !== "archived"),
    [assetsQuery.data],
  );

  const approvedCount = materials.filter((row) => row.status === "approved").length;
  const selectedAsset = materials.find((row) => row.id === selectedAssetId) ?? null;
  const openedAsset = materials.find((row) => row.id === openedAssetId) ?? null;
  const hasDemoMaterials = materials.some((row) => isDemoMaterial(row.metadata));
  const realMaterials = materials.filter((row) => !isDemoMaterial(row.metadata));
  const specialistMaterials = realMaterials.filter(
    (row) => row.metadata?.content_factory_generation === true,
  );

  function briefPayload() {
    return {
      topic: brief.topic.trim(),
      goal: brief.goal.trim(),
      audience: brief.audience.trim(),
      channel: backendChannelForProduct(brief.channel),
      period: brief.period.trim(),
      frequency: brief.frequency.trim(),
      format: brief.format.trim(),
      source_materials: brief.sourceMaterials.trim(),
      idempotency_key: idempotencyKey,
    };
  }

  const generateMaterialsMutation = useMutation({
    mutationFn: async () => {
      if (!projectId) throw new Error("project required");
      setGenerationError(null);

      setGenerationStage("preparing_content_plan");
      let response = await generateContentFactoryMaterials(projectId, {
        brief: briefPayload(),
        step: "prepare_plan",
        idempotency_key: idempotencyKey,
      });
      if (response.stage === "blocked") {
        throw new Error(response.safe_message);
      }
      const runId = response.execution_run_id;
      if (!runId) throw new Error("missing execution run");

      setGenerationStage("handing_to_copywriter");
      response = await generateContentFactoryMaterials(projectId, {
        brief: briefPayload(),
        execution_run_id: runId,
        step: "copywriter",
        idempotency_key: idempotencyKey,
      });
      if (response.stage === "blocked" || response.stage === "failed") {
        throw new Error(response.safe_message);
      }

      setGenerationStage("forming_materials");
      response = await generateContentFactoryMaterials(projectId, {
        brief: briefPayload(),
        execution_run_id: runId,
        step: "finalize",
        idempotency_key: idempotencyKey,
      });
      if (response.stage === "failed") {
        throw new Error(response.safe_message);
      }
      if (response.stage === "blocked") {
        throw new Error(response.safe_message);
      }

      setGenerationStage("verifying_result");
      if (response.stage !== "completed") {
        throw new Error(response.safe_message);
      }
      setGenerationStage("completed");
      return response;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["projects", projectId, "content-assets"],
      });
    },
    onError: (error: Error) => {
      setGenerationError(error.message);
      setGenerationStage("failed");
    },
  });

  const prepareMaterialsMutation = useMutation({
    mutationFn: async () => {
      if (!projectId) throw new Error("project required");
      const existing = materials.length;
      const toCreate = Math.max(0, MIN_MATERIALS - existing);
      const created = [];
      for (let i = 0; i < toCreate; i += 1) {
        const index = existing + i + 1;
        const row = await createContentAsset(projectId, {
          type: "telegram_post",
          title: t("contentFactory.plan.demoMaterialTitle", { index }),
          body: t("contentFactory.plan.demoMaterialBody", {
            topic: brief.topic || t("contentFactory.plan.defaultTopic"),
            goal: brief.goal || t("contentFactory.plan.defaultGoal"),
            audience: brief.audience || t("contentFactory.plan.defaultAudience"),
          }),
          metadata: {
            recovery_r3_demo: true,
            content_factory_channel: brief.channel,
            brief,
          },
        });
        created.push(row);
      }
      return created;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["projects", projectId, "content-assets"],
      });
    },
  });

  const planItems = useMemo(() => {
    const slots = Math.max(MIN_MATERIALS, materials.length);
    return Array.from({ length: slots }, (_, index) => {
      const asset = materials[index];
      return {
        index: index + 1,
        title: asset?.title ?? t("contentFactory.plan.slotTitle", { index: index + 1 }),
        status: asset?.status ?? "planned",
      };
    });
  }, [materials, t]);

  function canContinueFromPrepare(): boolean {
    return Boolean(
      projectId &&
        brief.topic.trim() &&
        brief.goal.trim() &&
        brief.audience.trim(),
    );
  }

  const generationStages: ContentFactoryGenerationStage[] = [
    "preparing_content_plan",
    "handing_to_copywriter",
    "forming_materials",
    "verifying_result",
  ];

  function stageLabel(stage: ContentFactoryGenerationStage): string {
    return t(`contentFactory.generation.stage.${stage}`);
  }

  function stageDone(stage: ContentFactoryGenerationStage): boolean {
    if (!generationStage) return false;
    if (generationStage === "completed") return true;
    const order = [...generationStages, "completed", "failed"];
    return order.indexOf(generationStage) > order.indexOf(stage);
  }

  function stageActive(stage: ContentFactoryGenerationStage): boolean {
    return generationStage === stage;
  }

  return (
    <div className="space-y-6" data-testid="content-factory-panel">
      <nav
        className="flex flex-wrap gap-2 text-xs"
        aria-label={t(stepsLabelKey)}
        data-testid="content-factory-steps"
      >
        {(
          [
            ["prepare", t("contentFactory.step.prepare")],
            ["plan", t("contentFactory.step.plan")],
            ["materials", t("contentFactory.step.materials")],
            ["package", t("contentFactory.step.package")],
            ["publish", t("contentFactory.step.publish")],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className="rounded-full border px-3 py-1"
            style={{
              borderColor: step === id ? "var(--ms-brand-primary)" : "var(--ms-border-default)",
              background: step === id ? "color-mix(in oklch, var(--ms-brand-primary) 12%, transparent)" : "transparent",
            }}
            onClick={() => setStep(id)}
            data-testid={`content-factory-step-${id}`}
          >
            {label}
          </button>
        ))}
      </nav>

      {step === "prepare" ? (
        <section
          className="rounded-xl border p-4"
          style={{ borderColor: "var(--ms-border-default)", background: "var(--ms-bg-surface)" }}
          data-testid="content-factory-prepare"
        >
          <h2 className="text-sm font-semibold">{t("contentFactory.prepare.title")}</h2>
          <p className="mt-1 text-xs text-muted-foreground">{t(prepareHintKey)}</p>

          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {!hideProjectSelect ? (
              <label className="block text-xs font-medium md:col-span-2">
                {t("common.project")}
                <select
                  className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
                  style={{ borderColor: "var(--ms-border-default)" }}
                  value={projectId ?? ""}
                  onChange={(e) => setProjectId(e.target.value || null)}
                  data-testid="content-factory-project-select"
                >
                  <option value="">{t("contentFactory.prepare.pickProject")}</option>
                  {(projectsQuery.data ?? []).map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}

            {hideProjectSelect && !projectId ? (
              <p
                className="text-xs text-destructive md:col-span-2"
                data-testid="content-factory-no-project"
              >
                {t("contentFactory.noProjectContext")}
              </p>
            ) : null}

            <label className="block text-xs font-medium md:col-span-2">
              {t("contentFactory.field.channel")}
              <select
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
                style={{ borderColor: "var(--ms-border-default)" }}
                value={brief.channel}
                onChange={(e) =>
                  setBrief((prev) => ({
                    ...prev,
                    channel: e.target.value as ContentFactoryProductChannelId,
                  }))
                }
                data-testid="content-factory-channel-select"
              >
                {CONTENT_FACTORY_CHANNEL_OPTIONS.map((row) => (
                  <option key={row.productId} value={row.productId}>
                    {labelProductChannel(locale, row.productId)}
                  </option>
                ))}
              </select>
            </label>

            {(
              [
                ["topic", brief.topic],
                ["goal", brief.goal],
                ["audience", brief.audience],
                ["period", brief.period],
                ["frequency", brief.frequency],
                ["format", brief.format],
              ] as const
            ).map(([field, value]) => (
              <label key={field} className="block text-xs font-medium">
                {t(`contentFactory.field.${field}`)}
                <input
                  className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
                  style={{ borderColor: "var(--ms-border-default)" }}
                  value={value}
                  onChange={(e) =>
                    setBrief((prev) => ({ ...prev, [field]: e.target.value }))
                  }
                  data-testid={`content-factory-field-${field}`}
                />
              </label>
            ))}

            <label className="block text-xs font-medium md:col-span-2">
              {t("contentFactory.field.sourceMaterials")}
              <textarea
                rows={3}
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
                style={{ borderColor: "var(--ms-border-default)" }}
                value={brief.sourceMaterials}
                onChange={(e) =>
                  setBrief((prev) => ({ ...prev, sourceMaterials: e.target.value }))
                }
                data-testid="content-factory-field-sourceMaterials"
              />
            </label>
          </div>

          <div className="mt-4">
            <Button
              type="button"
              disabled={!canContinueFromPrepare()}
              onClick={() => setStep("plan")}
              data-testid="content-factory-continue-plan"
            >
              {t("contentFactory.action.continueToPlan")}
            </Button>
          </div>
        </section>
      ) : null}

      {step === "plan" ? (
        <section
          className="rounded-xl border p-4"
          style={{ borderColor: "var(--ms-border-default)", background: "var(--ms-bg-surface)" }}
          data-testid="content-factory-plan"
        >
          <h2 className="text-sm font-semibold">{t("contentFactory.plan.title")}</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            {t("contentFactory.plan.summary", {
              channel: labelProductChannel(locale, brief.channel),
              topic: brief.topic,
              goal: brief.goal,
              audience: brief.audience,
              period: brief.period || "—",
              frequency: brief.frequency || "—",
              format: brief.format || "—",
            })}
          </p>

          <ul className="mt-4 space-y-2">
            {planItems.map((item) => (
              <li
                key={item.index}
                className="rounded-lg border px-3 py-2 text-sm"
                style={{ borderColor: "var(--ms-border-default)" }}
                data-testid={`content-factory-plan-item-${item.index}`}
              >
                <span className="font-medium">{item.title}</span>
                <span className="ml-2 text-xs text-muted-foreground">
                  {item.status === "planned"
                    ? t("contentFactory.plan.statusPlanned")
                    : labelMaterialStatus(locale, item.status)}
                </span>
              </li>
            ))}
          </ul>

          {realMaterials.length < MIN_MATERIALS ? (
            <div className="mt-4 space-y-2">
              <p className="text-xs text-muted-foreground">
                {t(needMoreMaterialsKey)}
              </p>

              {!allowDemoMaterials ? (
                <>
                  {providerReadinessQuery.data && !providerReadinessQuery.data.ready ? (
                    <p
                      className="text-xs text-destructive"
                      data-testid="content-factory-provider-blocked"
                    >
                      {providerReadinessQuery.data.blocked_message_ru ??
                        t("contentFactory.generation.blocked")}
                    </p>
                  ) : null}

                  {generationStage ? (
                    <ol
                      className="space-y-1 text-xs"
                      data-testid="content-factory-generation-stages"
                    >
                      {generationStages.map((stage) => (
                        <li
                          key={stage}
                          className={
                            stageActive(stage)
                              ? "font-medium text-foreground"
                              : stageDone(stage)
                                ? "text-muted-foreground line-through"
                                : "text-muted-foreground"
                          }
                        >
                          {stageLabel(stage)}
                        </li>
                      ))}
                    </ol>
                  ) : null}

                  {generationError ? (
                    <p className="text-xs text-destructive" data-testid="content-factory-generation-error">
                      {generationError}
                    </p>
                  ) : null}

                  {generationStage === "completed" ? (
                    <p className="text-xs text-muted-foreground" data-testid="content-factory-generation-done">
                      {t("contentFactory.generation.completedHint")}
                    </p>
                  ) : null}

                  <Button
                    type="button"
                    size="sm"
                    disabled={
                      !projectId ||
                      !canContinueFromPrepare() ||
                      generateMaterialsMutation.isPending ||
                      providerReadinessQuery.data?.ready === false
                    }
                    onClick={() => generateMaterialsMutation.mutate()}
                    data-testid="content-factory-create-materials"
                  >
                    {generateMaterialsMutation.isPending
                      ? t("contentFactory.action.generatingMaterials")
                      : t("contentFactory.action.createMaterials")}
                  </Button>
                </>
              ) : null}

              {allowDemoMaterials ? (
                <>
                  <p className="text-xs text-muted-foreground">
                    {t("contentFactory.plan.demoFallbackHint")}
                  </p>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={!projectId || prepareMaterialsMutation.isPending}
                    onClick={() => prepareMaterialsMutation.mutate()}
                    data-testid="content-factory-prepare-materials"
                  >
                    {t("contentFactory.action.prepareDemoMaterials")}
                  </Button>
                </>
              ) : null}
            </div>
          ) : null}

          {hasDemoMaterials ? (
            <p className="mt-3 text-xs text-muted-foreground" data-testid="content-factory-demo-banner">
              {t("contentFactory.demoMaterialsHint")}
            </p>
          ) : null}

          <div className="mt-4">
            <Button
              type="button"
              disabled={
                allowDemoMaterials
                  ? realMaterials.length < MIN_MATERIALS
                  : specialistMaterials.length < MIN_MATERIALS
              }
              onClick={() => setStep("materials")}
              data-testid="content-factory-continue-materials"
            >
              {t("contentFactory.action.continueToMaterials")}
            </Button>
          </div>
        </section>
      ) : null}

      {step === "materials" ? (
        <section className="space-y-4" data-testid="content-factory-materials">
          <div>
            <h2 className="text-sm font-semibold">{t("contentFactory.materials.title")}</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              {t("contentFactory.materials.hint", {
                approved: approvedCount,
                total: materials.length,
                minimum: MIN_MATERIALS,
              })}
            </p>
          </div>

          <div className="space-y-3">
            {materials.map((asset) => (
              <ContentFactoryMaterialCard
                key={asset.id}
                asset={asset}
                selected={selectedAssetId === asset.id}
                onSelect={() => setSelectedAssetId(asset.id)}
                onOpen={() => setOpenedAssetId(asset.id)}
              />
            ))}
          </div>

          {openedAsset ? (
            <ContentFactoryMaterialEditor
              projectId={projectId!}
              asset={openedAsset}
              onClose={() => setOpenedAssetId(null)}
              onUpdated={() => assetsQuery.refetch()}
            />
          ) : null}

          <Button
            type="button"
            disabled={approvedCount < 1}
            onClick={() => setStep("package")}
            data-testid="content-factory-continue-package"
          >
            {t("contentFactory.action.continueToPackage")}
          </Button>
        </section>
      ) : null}

      {step === "package" && projectId ? (
        <section className="space-y-4" data-testid="content-factory-package-step">
          <ContentFactoryPackagePanel
            projectId={projectId}
            channelProductId={brief.channel}
            selectedAsset={selectedAsset}
            onPackageReady={setPackageId}
          />
          <Button
            type="button"
            disabled={!packageId}
            onClick={() => setStep("publish")}
            data-testid="content-factory-continue-publish"
          >
            {t("contentFactory.action.continueToPublish")}
          </Button>
        </section>
      ) : null}

      {step === "publish" && projectId ? (
        <ContentFactoryPublishPanel
          projectId={projectId}
          packageId={packageId}
          channelProductId={brief.channel}
        />
      ) : null}
    </div>
  );
}
