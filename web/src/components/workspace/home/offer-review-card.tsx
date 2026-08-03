"use client";

import { useMemo, useState } from "react";
import type { OfferArtifactDetail } from "@/lib/api/endpoints/offers";
import {
  approveOffer,
  rejectOffer,
  requestOfferRevision,
} from "@/lib/api/endpoints/offers";
import { ApiError } from "@/lib/api/client";
import { useLocale, labelErrorCode } from "@/lib/i18n";
import { OfferDetailView } from "@/components/workspace/home/offer-detail-view";
import { OfferVersionHistory } from "@/components/workspace/home/offer-version-history";

type Props = {
  projectId: string;
  offer: OfferArtifactDetail;
  busy?: boolean;
  onBusyChange?: (busy: boolean) => void;
  onOfferUpdate: (offer: OfferArtifactDetail) => void;
};

export function OfferReviewCard({
  projectId,
  offer,
  busy,
  onBusyChange,
  onOfferUpdate,
}: Props) {
  const { t, locale } = useLocale();
  const [error, setError] = useState<string | null>(null);
  const [revisionComment, setRevisionComment] = useState("");
  const [showRevisionForm, setShowRevisionForm] = useState(false);
  const [rejectComment, setRejectComment] = useState("");
  const [showRejectForm, setShowRejectForm] = useState(false);

  const canReview = useMemo(
    () =>
      offer.status === "review_required" &&
      offer.approval_status === "pending" &&
      offer.human_review_required,
    [offer],
  );

  const isApproved = offer.approval_status === "approved";
  const isRejected = offer.approval_status === "rejected";

  async function handleApprove() {
    if (busy || !canReview) return;
    setError(null);
    onBusyChange?.(true);
    try {
      const updated = await approveOffer(projectId, offer.id, {
        expected_output_hash: offer.output_hash,
      });
      onOfferUpdate(updated);
    } catch (err) {
      setError(formatError(err, locale, t));
    } finally {
      onBusyChange?.(false);
    }
  }

  async function handleReject() {
    if (busy || !canReview) return;
    setError(null);
    onBusyChange?.(true);
    try {
      const updated = await rejectOffer(projectId, offer.id, {
        expected_output_hash: offer.output_hash,
        comment: rejectComment.trim() || undefined,
      });
      onOfferUpdate(updated);
      setShowRejectForm(false);
    } catch (err) {
      setError(formatError(err, locale, t));
    } finally {
      onBusyChange?.(false);
    }
  }

  async function handleRevision() {
    if (busy || !canReview) return;
    if (!revisionComment.trim()) {
      setError(t("offer.errors.revisionCommentRequired"));
      return;
    }
    setError(null);
    onBusyChange?.(true);
    try {
      const updated = await requestOfferRevision(projectId, offer.id, {
        expected_output_hash: offer.output_hash,
        comment: revisionComment.trim(),
      });
      onOfferUpdate(updated);
      setShowRevisionForm(false);
      setRevisionComment("");
    } catch (err) {
      setError(formatError(err, locale, t));
    } finally {
      onBusyChange?.(false);
    }
  }

  return (
    <section
      className="space-y-4 rounded-xl border p-5"
      style={{
        borderColor: "var(--ms-border-default)",
        background: "var(--ms-bg-surface)",
      }}
      data-testid="offer-review-card"
    >
      <header className="space-y-1">
        <p className="text-xs uppercase tracking-wide" style={{ color: "var(--ms-text-muted)" }}>
          {t("offer.sectionLabel")}
        </p>
        <h3 className="text-lg font-semibold" data-testid="offer-title">
          {offer.offer_title || t("offer.untitled")}
        </h3>
        {offer.offer_summary ? (
          <p className="text-sm leading-relaxed" style={{ color: "var(--ms-text-secondary)" }}>
            {offer.offer_summary}
          </p>
        ) : null}
        {isApproved ? (
          <p
            className="text-sm font-medium"
            style={{ color: "var(--ms-success, #067647)" }}
            data-testid="offer-approved-badge"
          >
            {t("offer.status.approved")}
          </p>
        ) : null}
        {isRejected ? (
          <p
            className="text-sm font-medium"
            style={{ color: "var(--ms-danger, #b42318)" }}
            data-testid="offer-rejected-badge"
          >
            {t("offer.status.rejected")}
          </p>
        ) : null}
      </header>

      <OfferDetailView offer={offer} />

      <OfferVersionHistory projectId={projectId} offerId={offer.id} versionNumber={offer.version_number} />

      {canReview ? (
        <div className="space-y-3 border-t pt-4" style={{ borderColor: "var(--ms-border-default)" }}>
          <p className="text-sm font-semibold">{t("offer.review.title")}</p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={busy}
              className="rounded-md px-4 py-2.5 text-sm font-semibold disabled:opacity-50"
              style={{
                background: "var(--ms-brand-primary)",
                color: "var(--ms-text-on-brand, #fff)",
              }}
              data-testid="offer-approve-btn"
              onClick={() => void handleApprove()}
            >
              {t("offer.review.approve")}
            </button>
            <button
              type="button"
              disabled={busy}
              className="rounded-md border px-4 py-2.5 text-sm font-semibold disabled:opacity-50"
              style={{
                borderColor: "var(--ms-border-default)",
                color: "var(--ms-text-primary)",
              }}
              data-testid="offer-revision-btn"
              onClick={() => {
                setShowRevisionForm((v) => !v);
                setShowRejectForm(false);
              }}
            >
              {t("offer.review.requestRevision")}
            </button>
            <button
              type="button"
              disabled={busy}
              className="rounded-md border px-4 py-2.5 text-sm font-semibold disabled:opacity-50"
              style={{
                borderColor: "var(--ms-border-default)",
                color: "var(--ms-danger, #b42318)",
              }}
              data-testid="offer-reject-btn"
              onClick={() => {
                setShowRejectForm((v) => !v);
                setShowRevisionForm(false);
              }}
            >
              {t("offer.review.reject")}
            </button>
          </div>

          {showRevisionForm ? (
            <div className="space-y-2" data-testid="offer-revision-form">
              <label className="text-sm font-medium" htmlFor="offer-revision-comment">
                {t("offer.review.revisionLabel")}
              </label>
              <textarea
                id="offer-revision-comment"
                rows={3}
                value={revisionComment}
                onChange={(e) => setRevisionComment(e.target.value)}
                className="w-full rounded-md border px-3 py-2 text-sm"
                style={{
                  borderColor: "var(--ms-border-default)",
                  background: "var(--ms-bg-canvas)",
                }}
              />
              <button
                type="button"
                disabled={busy}
                className="rounded-md px-3 py-2 text-sm font-semibold disabled:opacity-50"
                style={{
                  background: "var(--ms-brand-primary)",
                  color: "var(--ms-text-on-brand, #fff)",
                }}
                data-testid="offer-revision-submit"
                onClick={() => void handleRevision()}
              >
                {t("offer.review.submitRevision")}
              </button>
            </div>
          ) : null}

          {showRejectForm ? (
            <div className="space-y-2" data-testid="offer-reject-form">
              <label className="text-sm font-medium" htmlFor="offer-reject-comment">
                {t("offer.review.rejectLabel")}
              </label>
              <textarea
                id="offer-reject-comment"
                rows={2}
                value={rejectComment}
                onChange={(e) => setRejectComment(e.target.value)}
                className="w-full rounded-md border px-3 py-2 text-sm"
                style={{
                  borderColor: "var(--ms-border-default)",
                  background: "var(--ms-bg-canvas)",
                }}
              />
              <button
                type="button"
                disabled={busy}
                className="rounded-md px-3 py-2 text-sm font-semibold disabled:opacity-50"
                style={{
                  borderColor: "1px solid var(--ms-danger, #b42318)",
                  color: "var(--ms-danger, #b42318)",
                }}
                data-testid="offer-reject-submit"
                onClick={() => void handleReject()}
              >
                {t("offer.review.confirmReject")}
              </button>
            </div>
          ) : null}
        </div>
      ) : null}

      {error ? (
        <p className="text-sm" style={{ color: "var(--ms-danger, #b42318)" }}>
          {error}
        </p>
      ) : null}
    </section>
  );
}

function formatError(
  err: unknown,
  locale: "ru" | "en",
  t: (key: string) => string,
): string {
  const code =
    err instanceof ApiError && typeof err.body === "object" && err.body
      ? String((err.body as { detail?: string }).detail || "")
      : "";
  return (
    (code ? labelErrorCode(locale, code) : null) ||
    (err instanceof Error ? err.message : t("section.unavailable"))
  );
}
