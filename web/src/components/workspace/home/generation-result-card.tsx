"use client";

import Link from "next/link";
import { useState } from "react";
import { AuthenticatedImage } from "@/components/workspace/home/authenticated-image";
import { getApiBaseUrl } from "@/lib/api/config";
import { useLocale } from "@/lib/i18n";

export type GenerationResultMeta = {
  model?: string | null;
  provider?: string | null;
  costLabel?: string | null;
  durationLabel?: string | null;
  attempt?: number | null;
  maxAttempts?: number | null;
  similarityLabel?: string | null;
  isMock?: boolean;
  needsIdentityReview?: boolean;
  /** Automated likeness scored low — show warning, still allow Accept. */
  lowIdentityWarning?: boolean;
  promptPackageHash?: string | null;
  autoIdentityAssessment?: string | null;
  autoIdentityAssessmentReason?: string | null;
};

type Props = {
  assetId: string;
  meta: GenerationResultMeta;
  mediaKindHint?: "image" | "video";
  reviewBusy?: boolean;
  reviewNote?: string | null;
  diagnosticsText?: string | null;
  onAccept?: () => void;
  onRepair?: () => void;
  onReject?: () => void;
  onCreateVariant?: () => void;
  onCreateVideoFromImage?: () => void;
};

function friendlyModel(provider?: string | null, model?: string | null): string | null {
  const m = (model || "").trim();
  const p = (provider || "").toLowerCase();
  if (!m && !p) return null;
  const lower = m.toLowerCase();
  if (lower.includes("gpt-image") || lower.includes("gpt_image")) return "GPT Image";
  if (lower.includes("veo")) return m || "Veo";
  if (m) return m;
  if (p.includes("openai")) return "OpenAI Images";
  if (p.includes("gptunnel")) return "GPTunnel";
  return provider || null;
}

/**
 * Commercial product card: big media → meta → Accept / Repair / Variant.
 * Internals live under a single collapsed «Show details» block.
 */
export function GenerationResultCard({
  assetId,
  meta,
  mediaKindHint = "image",
  reviewBusy,
  reviewNote,
  diagnosticsText,
  onAccept,
  onRepair,
  onReject,
  onCreateVariant,
  onCreateVideoFromImage,
}: Props) {
  const { t } = useLocale();
  const [kind, setKind] = useState<"image" | "video">(mediaKindHint);
  const isVideo = kind === "video";
  const title = isVideo
    ? t("project.resultVideo")
    : meta.needsIdentityReview || meta.lowIdentityWarning
      ? t("project.resultNeedsReview")
      : t("project.resultReady");
  const modelLabel = friendlyModel(meta.provider, meta.model);
  const attemptLabel =
    meta.attempt != null
      ? meta.maxAttempts != null
        ? t("home.resultAttemptOf", {
            current: String(meta.attempt),
            max: String(meta.maxAttempts),
          })
        : String(meta.attempt)
      : null;

  const contentUrl = `${getApiBaseUrl()}/generated-visual-assets/${assetId}/content`;

  return (
    <div
      className="mt-2 space-y-4"
      data-testid="generation-result-card"
      data-media-kind={kind}
    >
      <p
        className="text-base font-semibold"
        style={{ color: "var(--ms-text-primary)" }}
        data-testid="generation-result-title"
      >
        {title}
      </p>

      <div
        className="overflow-hidden rounded-lg border"
        style={{ borderColor: "var(--ms-border-default)" }}
      >
        <AuthenticatedImage
          assetId={assetId}
          alt={
            meta.isMock
              ? t("home.diagnosticImageAlt")
              : isVideo
                ? t("home.generatedVideoAlt")
                : t("home.generatedImageAlt")
          }
          className="h-auto w-full max-h-[70vh] object-contain bg-black/5"
          onMediaKind={setKind}
        />
      </div>

      {meta.needsIdentityReview || meta.lowIdentityWarning ? (
        <p
          className="rounded-md border px-3 py-2 text-sm"
          style={{
            borderColor: meta.lowIdentityWarning
              ? "color-mix(in srgb, #b45309 45%, var(--ms-border-default))"
              : "var(--ms-border-default)",
            color: "var(--ms-text-primary)",
            background: "var(--ms-bg-elevated)",
          }}
          data-testid="home-identity-review-banner"
        >
          {meta.lowIdentityWarning
            ? t("errors.low_identity_consistency")
            : t("home.identityReviewHint")}
        </p>
      ) : null}

      {!meta.isMock ? (
        <dl
          className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-3"
          data-testid="generation-result-meta"
        >
          {meta.costLabel ? (
            <div>
              <dt style={{ color: "var(--ms-text-muted)" }}>{t("home.resultCost")}</dt>
              <dd style={{ color: "var(--ms-text-primary)" }}>{meta.costLabel}</dd>
            </div>
          ) : null}
          {modelLabel ? (
            <div>
              <dt style={{ color: "var(--ms-text-muted)" }}>{t("home.resultModel")}</dt>
              <dd style={{ color: "var(--ms-text-primary)" }}>{modelLabel}</dd>
            </div>
          ) : null}
          {isVideo && meta.durationLabel ? (
            <div>
              <dt style={{ color: "var(--ms-text-muted)" }}>{t("home.resultDuration")}</dt>
              <dd style={{ color: "var(--ms-text-primary)" }}>{meta.durationLabel}</dd>
            </div>
          ) : null}
          {attemptLabel ? (
            <div>
              <dt style={{ color: "var(--ms-text-muted)" }}>{t("home.resultAttempt")}</dt>
              <dd style={{ color: "var(--ms-text-primary)" }}>{attemptLabel}</dd>
            </div>
          ) : null}
          {!isVideo && meta.similarityLabel ? (
            <div>
              <dt style={{ color: "var(--ms-text-muted)" }}>{t("home.resultSimilarity")}</dt>
              <dd style={{ color: "var(--ms-text-primary)" }}>{meta.similarityLabel}</dd>
            </div>
          ) : null}
          {isVideo ? (
            <div>
              <dt style={{ color: "var(--ms-text-muted)" }}>{t("home.resultRepair")}</dt>
              <dd style={{ color: "var(--ms-text-primary)" }}>
                {(meta.attempt ?? 1) > 1
                  ? t("home.resultRepairUsed")
                  : t("home.resultRepairNone")}
              </dd>
            </div>
          ) : null}
        </dl>
      ) : null}

      {!meta.isMock ? (
        <div className="flex flex-wrap gap-2" data-testid="generation-result-actions">
          {onAccept ? (
            <button
              type="button"
              className="rounded-md px-4 py-2 text-sm font-semibold disabled:opacity-50"
              style={{
                background: "var(--ms-brand-primary)",
                color: "var(--ms-text-on-brand, #fff)",
              }}
              disabled={reviewBusy}
              onClick={onAccept}
              data-testid="home-accept-result"
            >
              {t("home.acceptResult")}
            </button>
          ) : null}
          {onRepair ? (
            <button
              type="button"
              className="rounded-md border px-4 py-2 text-sm font-semibold disabled:opacity-50"
              style={{
                borderColor: "var(--ms-border-default)",
                color: "var(--ms-text-primary)",
                background: "var(--ms-bg-surface)",
              }}
              disabled={reviewBusy}
              onClick={onRepair}
              data-testid="home-repair-result"
            >
              {isVideo
                ? t("home.repairShot")
                : meta.needsIdentityReview || meta.lowIdentityWarning
                  ? t("home.strengthenLikeness")
                  : t("home.repairResult")}
            </button>
          ) : null}
          {onCreateVariant && !isVideo ? (
            <button
              type="button"
              className="rounded-md border px-4 py-2 text-sm font-semibold"
              style={{
                borderColor: "var(--ms-border-default)",
                color: "var(--ms-text-primary)",
                background: "var(--ms-bg-surface)",
              }}
              onClick={onCreateVariant}
              data-testid="home-create-variant"
            >
              {t("home.createVariant")}
            </button>
          ) : null}
          {onCreateVideoFromImage && !isVideo ? (
            <button
              type="button"
              className="rounded-md border px-4 py-2 text-sm font-semibold"
              style={{
                borderColor: "var(--ms-border-default)",
                color: "var(--ms-text-primary)",
                background: "var(--ms-bg-surface)",
              }}
              onClick={onCreateVideoFromImage}
              data-testid="home-create-video-from-image"
            >
              {t("home.createVideoFromImage")}
            </button>
          ) : null}
          {onReject && isVideo ? (
            <button
              type="button"
              className="rounded-md px-4 py-2 text-sm font-semibold disabled:opacity-50"
              style={{ color: "var(--ms-danger, #b42318)" }}
              disabled={reviewBusy}
              onClick={onReject}
              data-testid="home-reject-result"
            >
              {t("home.rejectResultShort")}
            </button>
          ) : null}
        </div>
      ) : null}

      {reviewNote ? (
        <p
          className="text-xs"
          style={{ color: "var(--ms-text-muted)" }}
          data-testid="home-review-note"
        >
          {reviewNote}
        </p>
      ) : null}

      <details
        className="text-xs"
        style={{ color: "var(--ms-text-muted)" }}
        data-testid="generation-details"
      >
        <summary>{t("home.showDetails")}</summary>
        <div className="mt-3 space-y-3" data-testid="generation-developer">
          <div className="flex flex-wrap gap-3">
            <a href={contentUrl} target="_blank" rel="noreferrer" className="underline">
              {t("home.openImage")}
            </a>
            <a href={contentUrl} download className="underline">
              {t("home.downloadImage")}
            </a>
            <Link href="/workspace/assets" className="underline">
              {t("home.openAssets")}
            </Link>
          </div>

          {meta.isMock ? (
            <p data-testid="home-test-mode-badge">
              {t("home.testModeBadge")}: {t("home.mockDisclaimer")}
            </p>
          ) : null}

          {meta.needsIdentityReview ? (
            <p data-testid="home-identity-review-hint">{t("home.identityReviewHint")}</p>
          ) : null}

          {meta.autoIdentityAssessment || meta.autoIdentityAssessmentReason ? (
            diagnosticsText ? (
              <p data-testid="home-auto-identity-assessment">{diagnosticsText}</p>
            ) : null
          ) : null}

          {onReject && !isVideo ? (
            <button
              type="button"
              className="underline"
              disabled={reviewBusy}
              onClick={onReject}
              data-testid="home-reject-result"
            >
              {t("home.rejectResult")}
            </button>
          ) : null}

          {meta.promptPackageHash ? (
            <p data-testid="generation-prompt-hash">
              {t("home.promptPackage")}: {meta.promptPackageHash.slice(0, 24)}…
            </p>
          ) : null}

          {diagnosticsText ? (
            <div data-testid="home-route-diagnostics">
              <p className="font-medium">{t("home.diagnostics")}</p>
              <p className="mt-1 whitespace-pre-wrap break-all">{diagnosticsText}</p>
            </div>
          ) : null}
        </div>
      </details>
    </div>
  );
}
