"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AuthenticatedImage } from "@/components/workspace/home/authenticated-image";
import { SpecialistActivityCard } from "@/components/workspace/home/specialist-activity-card";
import { useAuth } from "@/lib/auth/auth-context";
import { reviewGeneratedVisual } from "@/lib/api/endpoints/generated-visual-assets";
import type { HomeChatMessage } from "@/lib/home/user-intent-draft";
import type { ContentDraftReviewAction } from "@/lib/api/types/user-requests";
import { useLocale } from "@/lib/i18n";
import { getApiBaseUrl } from "@/lib/api/config";

type Props = {
  messages: HomeChatMessage[];
  loading?: boolean;
  error?: string | null;
  /** Hydrated from GeneratedVisualAsset.user_accepted (backend truth). */
  initialReviewNotes?: Record<string, string>;
  onRetryGeneration?: (message: HomeChatMessage) => void;
  onCreateVariant?: (message: HomeChatMessage) => void;
  onStrengthenLikeness?: (message: HomeChatMessage) => void;
  onCreateVideoFromImage?: (message: HomeChatMessage) => void;
  onReviewDraft?: (message: HomeChatMessage, action: ContentDraftReviewAction) => void;
  draftBusyId?: string | null;
};

export function HomeConversation({
  messages,
  loading,
  error,
  initialReviewNotes,
  onRetryGeneration,
  onCreateVariant,
  onStrengthenLikeness,
  onCreateVideoFromImage,
  onReviewDraft,
  draftBusyId,
}: Props) {
  const { t } = useLocale();
  const { user } = useAuth();
  const showDiag = user?.role === "owner" || user?.role === "admin";
  const [reviewBusy, setReviewBusy] = useState<string | null>(null);
  const [reviewNote, setReviewNote] = useState<Record<string, string>>({});

  useEffect(() => {
    if (initialReviewNotes) {
      setReviewNote(initialReviewNotes);
    }
  }, [initialReviewNotes]);

  async function submitReview(
    assetId: string,
    accepted: boolean,
  ): Promise<void> {
    setReviewBusy(assetId);
    try {
      await reviewGeneratedVisual(assetId, {
        user_accepted: accepted,
        identity_similarity: accepted ? "high" : "low",
        brand_similarity: "not_applicable",
        review_notes: accepted
          ? "owner_accepted"
          : "owner_rejected_needs_variant",
      });
      setReviewNote((prev) => ({
        ...prev,
        [assetId]: accepted ? t("home.acceptResult") : t("home.rejectResult"),
      }));
    } catch {
      setReviewNote((prev) => ({
        ...prev,
        [assetId]: t("section.unavailable"),
      }));
    } finally {
      setReviewBusy(null);
    }
  }

  return (
    <div
      className="flex max-h-[520px] min-h-[240px] flex-col gap-3 overflow-y-auto rounded-xl border p-4"
      style={{
        borderColor: "var(--ms-border-default)",
        background: "var(--ms-bg-elevated)",
      }}
      data-testid="home-conversation"
      aria-live="polite"
    >
      {messages.length === 0 && !loading ? (
        <p
          className="text-sm"
          style={{ color: "var(--ms-text-muted)" }}
          data-testid="home-conversation-empty"
        >
          {t("home.conversationEmpty")}
        </p>
      ) : null}

      {messages.map((m, mIndex) => {
        const ids = m.role === "assistant" ? m.generatedVisualAssetIds || [] : [];
        const contentDraft = m.role === "assistant" ? m.contentDraft ?? null : null;
        const priorUserText =
          [...messages.slice(0, mIndex)].reverse().find((x) => x.role === "user")?.text ||
          m.text;
        const isMock =
          m.generationStatus === "diagnostic" ||
          (m.generationWarnings || []).includes("mock_diagnostic_placeholder");
        const needsIdentityReview =
          m.generationStatus === "awaiting_identity_review";
        const isReal =
          (m.generationStatus === "succeeded" || needsIdentityReview) && !isMock;
        const failed =
          m.generationStatus === "unavailable" || m.generationStatus === "failed";
        return (
          <div
            key={m.id}
            className="rounded-lg px-3 py-2 text-sm"
            style={{
              background:
                m.role === "user"
                  ? "color-mix(in srgb, var(--brand-blue) 14%, transparent)"
                  : "var(--ms-bg-surface)",
              color: "var(--ms-text-primary)",
              alignSelf: m.role === "user" ? "flex-end" : "flex-start",
              maxWidth: "92%",
            }}
            data-testid={`home-message-${m.role}`}
            data-route-kind={m.route?.kind || undefined}
            data-route-category={m.route?.category || undefined}
            data-generation-status={m.generationStatus || undefined}
            data-generation-mode={isMock ? "mock" : isReal ? "real" : undefined}
          >
            {isMock ? (
              <span
                className="mb-2 inline-block rounded px-2 py-0.5 text-[11px] font-semibold tracking-wide"
                style={{
                  background: "color-mix(in srgb, #b45309 28%, transparent)",
                  color: "#fbbf24",
                }}
                data-testid="home-test-mode-badge"
              >
                {t("home.testModeBadge")}
              </span>
            ) : null}
            <p className="whitespace-pre-wrap">{m.text}</p>
            {contentDraft ? (
              <SpecialistActivityCard
                draft={contentDraft}
                reviewStatus={m.contentDraftReviewStatus ?? null}
                specialistRole={m.assignedSpecialist ?? "content_specialist"}
                taskText={priorUserText}
                showDiag={showDiag}
                promptPackageHash={m.promptPackageHash ?? null}
                executionProvider={m.executionProvider ?? null}
                executionModel={m.executionModel ?? null}
                busy={draftBusyId === m.requestId}
                onReview={(action) => onReviewDraft?.(m, action)}
              />
            ) : null}
            {ids.length > 0 ? (
              <div className="mt-3 space-y-2" data-testid="home-generated-images">
                {ids.map((id) => (
                  <div key={id} className="space-y-1">
                    <div
                      className="block overflow-hidden rounded-md border"
                      style={{ borderColor: "var(--ms-border-default)" }}
                    >
                      <AuthenticatedImage
                        assetId={id}
                        alt={
                          isMock
                            ? t("home.diagnosticImageAlt")
                            : t("home.generatedImageAlt")
                        }
                        className="h-auto w-full max-w-md object-cover"
                      />
                    </div>
                    {isMock ? (
                      <p
                        className="text-xs"
                        style={{ color: "var(--ms-text-muted)" }}
                        data-testid="home-mock-disclaimer"
                      >
                        {t("home.mockDisclaimer")}
                      </p>
                    ) : (
                      <div className="flex flex-wrap gap-2 text-xs">
                        <a
                          href={`${getApiBaseUrl()}/generated-visual-assets/${id}/content`}
                          target="_blank"
                          rel="noreferrer"
                          className="underline"
                          style={{ color: "var(--ms-text-muted)" }}
                        >
                          {t("home.openImage")}
                        </a>
                        <a
                          href={`${getApiBaseUrl()}/generated-visual-assets/${id}/content`}
                          download
                          className="underline"
                          style={{ color: "var(--ms-text-muted)" }}
                        >
                          {t("home.downloadImage")}
                        </a>
                        <Link
                          href="/workspace/assets"
                          className="underline"
                          style={{ color: "var(--ms-text-muted)" }}
                        >
                          {t("home.openAssets")}
                        </Link>
                      </div>
                    )}
                  </div>
                ))}
                {isReal && onCreateVariant ? (
                  <div className="flex flex-wrap gap-3">
                    {needsIdentityReview ? (
                      <p
                        className="w-full text-xs"
                        style={{ color: "var(--ms-text-secondary)" }}
                        data-testid="home-identity-review-hint"
                      >
                        {t("home.identityReviewHint")}
                      </p>
                    ) : null}
                    <button
                      type="button"
                      className="text-xs underline"
                      style={{ color: "var(--ms-text-muted)" }}
                      disabled={reviewBusy === ids[0]}
                      onClick={() => {
                        if (ids[0]) void submitReview(ids[0], true);
                      }}
                      data-testid="home-accept-result"
                    >
                      {t("home.acceptResult")}
                    </button>
                    <button
                      type="button"
                      className="text-xs underline"
                      style={{ color: "var(--ms-text-muted)" }}
                      disabled={reviewBusy === ids[0]}
                      onClick={() => {
                        if (ids[0]) void submitReview(ids[0], false);
                      }}
                      data-testid="home-reject-result"
                    >
                      {t("home.rejectResult")}
                    </button>
                    <button
                      type="button"
                      className="text-xs underline"
                      style={{ color: "var(--ms-text-muted)" }}
                      onClick={() => onCreateVariant(m)}
                      data-testid="home-create-variant"
                    >
                      {t("home.createVariant")}
                    </button>
                    {onStrengthenLikeness ? (
                      <button
                        type="button"
                        className="text-xs underline"
                        style={{ color: "var(--ms-text-muted)" }}
                        onClick={() => onStrengthenLikeness(m)}
                        data-testid="home-strengthen-likeness"
                      >
                        {t("home.strengthenLikeness")}
                      </button>
                    ) : null}
                    {onCreateVideoFromImage ? (
                      <button
                        type="button"
                        className="text-xs underline"
                        style={{ color: "var(--ms-text-muted)" }}
                        onClick={() => onCreateVideoFromImage(m)}
                        data-testid="home-create-video-from-image"
                      >
                        {t("home.createVideoFromImage")}
                      </button>
                    ) : null}
                  </div>
                ) : null}
                {ids[0] && reviewNote[ids[0]] ? (
                  <p
                    className="text-xs"
                    style={{ color: "var(--ms-text-muted)" }}
                    data-testid="home-review-note"
                  >
                    {reviewNote[ids[0]]}
                  </p>
                ) : null}
              </div>
            ) : null}
            {failed && onRetryGeneration ? (
              <button
                type="button"
                className="mt-2 text-xs underline"
                style={{ color: "var(--ms-text-muted)" }}
                onClick={() => onRetryGeneration(m)}
                data-testid="home-retry-generation"
              >
                {t("home.retryGeneration")}
              </button>
            ) : null}
            {m.route && showDiag ? (
              <details
                className="mt-2 border-t pt-2 text-xs"
                style={{
                  borderColor: "var(--ms-border-default)",
                  color: "var(--ms-text-muted)",
                }}
                data-testid="home-route-diagnostics"
              >
                <summary>{t("home.diagnostics")}</summary>
                <p>
                  route={m.route.category} · kind={m.route.kind} · skill=
                  {m.skillCode || "—"} · status={m.route.status || "—"} · gen=
                  {m.generationStatus || "—"}
                </p>
              </details>
            ) : null}
          </div>
        );
      })}

      {loading ? (
        <p className="text-sm" style={{ color: "var(--ms-text-muted)" }}>
          {t("common.loading")}
        </p>
      ) : null}
      {error ? (
        <p className="text-sm" style={{ color: "var(--ms-danger, #b42318)" }}>
          {error}
        </p>
      ) : null}
    </div>
  );
}
