"use client";

import { useEffect, useMemo, useState } from "react";
import { AuthenticatedImage } from "@/components/workspace/home/authenticated-image";
import { GenerationResultCard } from "@/components/workspace/home/generation-result-card";
import {
  generateVideoClip,
  getOwnerVideoAcceptancePreview,
  getVideoClipBySource,
  previewVideoClip,
  reconcileVideoClip,
  type VideoClipExecutionDto,
  type VideoClipPreviewDto,
} from "@/lib/api/endpoints/video-clips";
import {
  getGeneratedVisualAsset,
  reviewGeneratedVisual,
} from "@/lib/api/endpoints/generated-visual-assets";
import { useVideoStudioCapabilities } from "@/lib/video-studio/use-video-capabilities";
import { useLocale } from "@/lib/i18n";

type Props = {
  sourceImageAssetId: string;
  onClose: () => void;
  /** When false, quote/confirm are disabled — existing clips still restore. */
  generationEnabled?: boolean;
  ownerVideoPreview?: boolean;
  onVideoReviewChange?: () => void;
};

type Step = "form" | "quoted" | "working" | "done" | "blocked" | "unknown";

function newIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `idem-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function reviewLabelFromAsset(
  userAccepted: boolean | null | undefined,
  labels: { accepted: string; rejected: string },
): string | null {
  if (userAccepted === true) return labels.accepted;
  if (userAccepted === false) return labels.rejected;
  return null;
}

export function AnimateImagePanel({
  sourceImageAssetId,
  onClose,
  generationEnabled = false,
  ownerVideoPreview = false,
  onVideoReviewChange,
}: Props) {
  const { t, locale } = useLocale();
  const { data: caps, loading: capsLoading } = useVideoStudioCapabilities();
  const [sceneDescription, setSceneDescription] = useState("");
  const [cameraMovementId, setCameraMovementId] = useState("");
  const [cameraMovementInstruction, setCameraMovementInstruction] = useState("");
  const [durationSeconds, setDurationSeconds] = useState<number>(8);
  const [aspectRatio, setAspectRatio] = useState<string>("16:9");
  const [step, setStep] = useState<Step>("form");
  const [busy, setBusy] = useState(false);
  const [hydrating, setHydrating] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<VideoClipPreviewDto | null>(null);
  const [execution, setExecution] = useState<VideoClipExecutionDto | null>(null);
  const [idempotencyKey, setIdempotencyKey] = useState<string>(() => newIdempotencyKey());
  const [reviewNote, setReviewNote] = useState<string | null>(null);

  const canCreateNew = generationEnabled && !ownerVideoPreview;

  const singleClipDurations = useMemo(() => {
    const supported = caps?.provider_supported_single_clip_durations_seconds;
    if (supported?.length) return supported;
    const max = caps?.single_clip_max_seconds ?? 15;
    const all = caps?.requested_durations_seconds ?? [8];
    return all.filter((d) => d <= max && d >= (caps?.single_clip_min_seconds ?? 5));
  }, [caps]);

  const aspectOptions = caps?.aspect_ratios ?? [];
  const movementOptions = caps?.camera_movements ?? [];

  const canQuote =
    canCreateNew &&
    sceneDescription.trim().length >= 4 &&
    Boolean(cameraMovementId) &&
    !busy &&
    !capsLoading &&
    !hydrating;

  function applyExecution(result: VideoClipExecutionDto) {
    setExecution(result);
    if (result.status === "succeeded" || result.status === "result_requires_review") {
      setStep("done");
    } else if (result.status === "outcome_unknown") {
      setStep("unknown");
    } else if (result.status === "failed") {
      setStep("blocked");
      setError(result.user_message_ru);
    } else if (result.status === "executing") {
      setStep("working");
    }
  }

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setHydrating(true);
      try {
        if (ownerVideoPreview) {
          const binding = await getOwnerVideoAcceptancePreview();
          if (cancelled || binding.source_image_asset_id !== sourceImageAssetId) return;
          applyExecution(binding.execution);
          if (binding.result_asset_id) {
            const note = reviewLabelFromAsset(binding.video_user_accepted, {
              accepted: t("home.acceptResult"),
              rejected: t("home.rejectResultShort"),
            });
            if (note) setReviewNote(note);
          }
          return;
        }

        const hydration = await getVideoClipBySource(sourceImageAssetId);
        if (cancelled || !hydration) return;

        if (hydration.preview) {
          setPreview(hydration.preview);
          setSceneDescription(hydration.preview.motion_brief);
          setDurationSeconds(hydration.preview.duration_seconds);
          setAspectRatio(hydration.preview.aspect_ratio);
          if (hydration.preview.blocked_reason_ru || !hydration.preview.ready_to_generate) {
            setStep("blocked");
          } else {
            setStep("quoted");
          }
        }
        if (hydration.execution) {
          applyExecution(hydration.execution);
          if (hydration.execution.result_asset_id) {
            try {
              const asset = await getGeneratedVisualAsset(hydration.execution.result_asset_id);
              const note = reviewLabelFromAsset(asset.user_accepted, {
                accepted: t("home.acceptResult"),
                rejected: t("home.rejectResultShort"),
              });
              if (note) setReviewNote(note);
            } catch {
              /* optional */
            }
          }
        }
      } catch {
        /* no existing clip — stay on form */
      } finally {
        if (!cancelled) setHydrating(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sourceImageAssetId, ownerVideoPreview, t]);

  async function runQuote() {
    if (!canQuote) return;
    setBusy(true);
    setError(null);
    setExecution(null);
    try {
      const quoted = await previewVideoClip({
        source_image_asset_id: sourceImageAssetId,
        motion_brief: sceneDescription.trim(),
        duration_seconds: durationSeconds,
        aspect_ratio: aspectRatio,
        camera_movement_id: cameraMovementId,
        camera_movement_instruction: cameraMovementInstruction.trim() || null,
      });
      setPreview(quoted);
      setIdempotencyKey(newIdempotencyKey());
      if (quoted.blocked_reason_ru || !quoted.ready_to_generate) {
        setStep("blocked");
      } else {
        setStep("quoted");
      }
    } catch {
      setError(t("home.animateImage.errorPreview"));
      setStep("form");
    } finally {
      setBusy(false);
    }
  }

  async function runGenerate() {
    if (!preview?.clip_request_id || step !== "quoted" || !canCreateNew) return;
    setBusy(true);
    setError(null);
    setStep("working");
    try {
      const result = await generateVideoClip(
        preview.clip_request_id,
        idempotencyKey,
        true,
      );
      setExecution(result);
      if (result.status === "succeeded") {
        setStep("done");
      } else if (result.status === "result_requires_review") {
        setStep("done");
        setError(result.user_message_ru);
      } else if (result.status === "outcome_unknown") {
        setStep("unknown");
        setError(result.user_message_ru);
      } else {
        setStep("blocked");
        setError(result.user_message_ru);
      }
    } catch {
      setError(t("home.animateImage.errorGenerate"));
      setStep("quoted");
    } finally {
      setBusy(false);
    }
  }

  async function runReconcile() {
    if (!execution?.clip_request_id || !execution.can_reconcile) return;
    setBusy(true);
    setError(null);
    try {
      const result = await reconcileVideoClip(execution.clip_request_id);
      setExecution(result);
      if (result.status === "succeeded") {
        setStep("done");
        setError(null);
      } else if (result.status === "result_requires_review") {
        setStep("done");
        setError(result.user_message_ru);
      } else if (result.status === "outcome_unknown") {
        setStep("unknown");
        setError(result.user_message_ru);
      } else {
        setStep("blocked");
        setError(result.user_message_ru);
      }
    } catch {
      setError(t("home.animateImage.errorReconcile"));
    } finally {
      setBusy(false);
    }
  }

  async function acceptClip() {
    if (!execution?.result_asset_id) return;
    setBusy(true);
    try {
      await reviewGeneratedVisual(execution.result_asset_id, {
        user_accepted: true,
        identity_similarity: "not_applicable",
        brand_similarity: "not_applicable",
        review_notes: "video_clip_accepted",
      });
      setReviewNote(t("home.acceptResult"));
      onVideoReviewChange?.();
    } catch {
      setReviewNote(t("section.unavailable"));
    } finally {
      setBusy(false);
    }
  }

  async function rejectClip() {
    if (!execution?.result_asset_id) return;
    setBusy(true);
    try {
      await reviewGeneratedVisual(execution.result_asset_id, {
        user_accepted: false,
        identity_similarity: "not_applicable",
        brand_similarity: "not_applicable",
        review_notes: "video_clip_rejected",
      });
      setReviewNote(t("home.rejectResultShort"));
      onVideoReviewChange?.();
    } catch {
      setReviewNote(t("section.unavailable"));
    } finally {
      setBusy(false);
    }
  }

  function resetForNewMotion() {
    if (!canCreateNew) return;
    setPreview(null);
    setExecution(null);
    setError(null);
    setReviewNote(null);
    setIdempotencyKey(newIdempotencyKey());
    setStep("form");
  }

  function resetForVariant() {
    resetForNewMotion();
    void runQuote();
  }

  const statusMessage = useMemo(() => {
    if (hydrating) return t("home.animateImage.restoring");
    if (step === "working") return t("home.animateImage.statusWorking");
    if (step === "unknown" && execution) return execution.user_message_ru;
    if (step === "done" && execution) {
      if (execution.status === "result_requires_review") {
        return execution.user_message_ru;
      }
      return execution.user_message_ru;
    }
    if (step === "blocked" && preview?.blocked_reason_ru) {
      return preview.blocked_reason_ru;
    }
    return null;
  }, [step, execution, preview, hydrating, t]);

  const showCreateForm = step !== "done" && canCreateNew;

  return (
    <section
      className="mt-4 space-y-4 rounded-xl border p-4"
      style={{
        borderColor: "var(--ms-border-default)",
        background: "var(--ms-bg-surface)",
      }}
      data-testid="animate-image-panel"
      data-hydrating={hydrating ? "1" : "0"}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3
            className="text-base font-semibold"
            style={{ color: "var(--ms-text-primary)" }}
          >
            {t("home.animateImage.title")}
          </h3>
          <p className="text-sm" style={{ color: "var(--ms-text-muted)" }}>
            {t("home.animateImage.subtitle")}
          </p>
        </div>
        <button
          type="button"
          className="text-sm underline"
          style={{ color: "var(--ms-text-muted)" }}
          onClick={onClose}
          data-testid="animate-image-close"
        >
          {t("home.animateImage.close")}
        </button>
      </div>

      <div
        className="overflow-hidden rounded-lg border max-w-md"
        style={{ borderColor: "var(--ms-border-default)" }}
      >
        <AuthenticatedImage
          assetId={sourceImageAssetId}
          alt={t("home.generatedImageAlt")}
          className="h-auto w-full object-contain"
        />
      </div>

      {showCreateForm ? (
        <div className="space-y-3" data-testid="animate-image-form">
          <label className="block text-sm">
            <span style={{ color: "var(--ms-text-primary)" }}>
              {t("home.videoField.camera")}
            </span>
            <select
              className="mt-1 w-full rounded-md border px-2 py-1.5 text-sm"
              style={{ borderColor: "var(--ms-border-default)" }}
              value={cameraMovementId}
              onChange={(e) => setCameraMovementId(e.target.value)}
              disabled={capsLoading || hydrating}
              data-testid="animate-image-camera-preset"
            >
              <option value="">{t("home.videoCameraSelect")}</option>
              {movementOptions.map((m) => (
                <option key={m.id} value={m.id}>
                  {locale === "en" ? m.label_en : m.label_ru}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-sm">
            <span style={{ color: "var(--ms-text-muted)" }}>
              {t("home.videoCameraInstruction")}
            </span>
            <input
              className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
              style={{
                borderColor: "var(--ms-border-default)",
                background: "var(--ms-bg-elevated)",
              }}
              value={cameraMovementInstruction}
              onChange={(e) => setCameraMovementInstruction(e.target.value)}
              placeholder={t("home.videoCameraInstructionPlaceholder")}
              data-testid="animate-image-camera-instruction"
            />
          </label>

          <label className="block text-sm">
            <span style={{ color: "var(--ms-text-primary)" }}>
              {t("home.videoField.scene_description")}
            </span>
            <textarea
              rows={3}
              value={sceneDescription}
              onChange={(e) => setSceneDescription(e.target.value)}
              className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
              style={{
                borderColor: "var(--ms-border-default)",
                background: "var(--ms-bg-elevated)",
              }}
              placeholder={t("home.videoScenePlaceholder")}
              data-testid="animate-image-motion"
            />
          </label>

          <div className="flex flex-wrap gap-4">
            <label className="text-sm">
              <span style={{ color: "var(--ms-text-muted)" }}>
                {t("home.animateImage.duration")}
              </span>
              <select
                className="mt-1 block rounded-md border px-2 py-1.5 text-sm"
                style={{ borderColor: "var(--ms-border-default)" }}
                value={durationSeconds}
                onChange={(e) => setDurationSeconds(Number(e.target.value))}
                disabled={capsLoading || hydrating}
                data-testid="animate-image-duration"
              >
                {singleClipDurations.map((d) => (
                  <option key={d} value={d}>
                    {d} {t("home.animateImage.seconds")}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm">
              <span style={{ color: "var(--ms-text-muted)" }}>
                {t("home.animateImage.format")}
              </span>
              <select
                className="mt-1 block rounded-md border px-2 py-1.5 text-sm"
                style={{ borderColor: "var(--ms-border-default)" }}
                value={aspectRatio}
                onChange={(e) => setAspectRatio(e.target.value)}
                disabled={capsLoading || hydrating}
                data-testid="animate-image-aspect"
              >
                {(aspectOptions.length
                  ? aspectOptions
                  : [
                      {
                        id: "16:9",
                        label_ru: "16:9",
                        label_en: "16:9",
                        availability: "available" as const,
                      },
                    ]
                ).map((a) => (
                  <option
                    key={a.id}
                    value={a.id}
                    disabled={a.availability === "unavailable"}
                  >
                    {locale === "en" ? a.label_en : a.label_ru}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <button
            type="button"
            className="rounded-md border px-4 py-2 text-sm font-semibold disabled:opacity-50"
            style={{
              borderColor: "var(--ms-border-default)",
              color: "var(--ms-text-primary)",
            }}
            disabled={!canQuote}
            onClick={() => void runQuote()}
            data-testid="animate-image-quote"
          >
            {busy && step === "form"
              ? t("home.animateImage.quoting")
              : t("home.animateImage.quote")}
          </button>
        </div>
      ) : null}

      {preview && (step === "quoted" || step === "working" || step === "blocked") ? (
        <div
          className="space-y-2 rounded-md border px-3 py-3 text-sm"
          style={{
            borderColor: "var(--ms-border-default)",
            background: "var(--ms-bg-elevated)",
          }}
          data-testid="animate-image-quote-summary"
        >
          <p style={{ color: "var(--ms-text-primary)" }}>
            {preview.what_will_be_created_ru}
          </p>
          <p style={{ color: "var(--ms-text-muted)" }}>
            {t("home.animateImage.estimatedCost")}: {preview.estimated_cost_label}
          </p>
          <p style={{ color: "var(--ms-text-muted)" }}>
            {t("home.animateImage.estimatedWait")}: ~
            {preview.estimated_wait_seconds} {t("home.animateImage.seconds")}
          </p>
          {preview.limitations_ru.length > 0 ? (
            <ul className="list-disc pl-5" style={{ color: "var(--ms-text-muted)" }}>
              {preview.limitations_ru.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {step === "quoted" && canCreateNew ? (
        <button
          type="button"
          className="rounded-md px-4 py-2 text-sm font-semibold disabled:opacity-50"
          style={{
            background: "var(--ms-brand-primary)",
            color: "var(--ms-text-on-brand, #fff)",
          }}
          disabled={busy}
          onClick={() => void runGenerate()}
          data-testid="animate-image-confirm"
        >
          {t("home.animateImage.confirm")}
        </button>
      ) : null}

      {statusMessage ? (
        <p
          className="text-sm"
          style={{
            color:
              step === "blocked" && !execution
                ? "var(--ms-text-muted)"
                : "var(--ms-text-primary)",
          }}
          data-testid="animate-image-status"
        >
          {statusMessage}
        </p>
      ) : null}

      {error ? (
        <p className="text-sm" style={{ color: "var(--ms-danger, #b42318)" }}>
          {error}
        </p>
      ) : null}

      {step === "unknown" && execution?.can_reconcile ? (
        <div
          className="flex flex-wrap gap-2"
          data-testid="animate-image-unknown-actions"
        >
          <button
            type="button"
            className="rounded-md px-4 py-2 text-sm font-semibold disabled:opacity-50"
            style={{
              background: "var(--ms-brand-primary)",
              color: "var(--ms-text-on-brand, #fff)",
            }}
            disabled={busy}
            onClick={() => void runReconcile()}
            data-testid="animate-image-reconcile"
          >
            {busy
              ? t("home.animateImage.reconciling")
              : t("home.animateImage.reconcile")}
          </button>
          {execution.can_contact_admin ? (
            <p className="text-sm" style={{ color: "var(--ms-text-muted)" }}>
              {t("home.animateImage.contactAdmin")}
            </p>
          ) : null}
        </div>
      ) : null}

      {step === "done" && execution?.result_asset_id ? (
        <div className="space-y-3" data-testid="animate-image-result">
          {execution.status === "result_requires_review" ? (
            <p
              className="text-sm font-medium"
              style={{ color: "var(--ms-warning, #b54708)" }}
              data-testid="animate-image-duration-mismatch"
            >
              {execution.user_message_ru}
              {execution.actual_duration_seconds != null &&
              execution.requested_duration_seconds != null ? (
                <>
                  {" "}
                  ({execution.requested_duration_seconds} →{" "}
                  {execution.actual_duration_seconds.toFixed(1)} с)
                </>
              ) : null}
            </p>
          ) : null}
          <GenerationResultCard
            assetId={execution.result_asset_id}
            meta={{
              durationLabel:
                execution.actual_duration_seconds != null
                  ? `${execution.actual_duration_seconds.toFixed(1)} s`
                  : `${durationSeconds} s`,
              costLabel: preview?.estimated_cost_label ?? null,
            }}
            mediaKindHint="video"
            reviewBusy={busy}
            reviewNote={reviewNote}
            onAccept={
              execution.can_accept ? () => void acceptClip() : undefined
            }
            onReject={
              execution.can_accept || execution.status === "result_requires_review"
                ? () => void rejectClip()
                : undefined
            }
            onCreateVariant={
              canCreateNew && execution.can_create_variant ? resetForVariant : undefined
            }
            onRepair={canCreateNew ? resetForNewMotion : undefined}
          />
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="rounded-md border px-3 py-2 text-sm font-semibold"
              style={{
                borderColor: "var(--ms-border-default)",
                color: "var(--ms-text-primary)",
              }}
              onClick={() => setReviewNote(t("home.animateImage.addedToProject"))}
              data-testid="animate-image-add-scene"
            >
              {t("home.animateImage.addToProject")}
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
