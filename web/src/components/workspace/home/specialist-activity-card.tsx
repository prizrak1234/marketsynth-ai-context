"use client";

import { useState } from "react";
import type { BackendContentDraft, ContentDraftReviewAction } from "@/lib/api/types/user-requests";
import { useLocale } from "@/lib/i18n";

type Props = {
  draft: BackendContentDraft;
  reviewStatus: string | null;
  specialistRole: string | null;
  taskText: string;
  showDiag?: boolean;
  promptPackageHash?: string | null;
  executionProvider?: string | null;
  executionModel?: string | null;
  busy?: boolean;
  onReview?: (action: ContentDraftReviewAction) => void;
  onCopy?: (text: string) => void;
};

export function SpecialistActivityCard({
  draft,
  reviewStatus,
  specialistRole,
  taskText,
  showDiag,
  promptPackageHash,
  executionProvider,
  executionModel,
  busy,
  onReview,
  onCopy,
}: Props) {
  const { t } = useLocale();
  const [copied, setCopied] = useState(false);
  const isMock = draft.generation_mode === "mock";

  const specialistName =
    specialistRole === "content_specialist"
      ? t("specialist.role.content_specialist")
      : specialistRole || t("specialist.role.generic");

  const fullText = [draft.hook, draft.body, draft.cta]
    .filter(Boolean)
    .join("\n\n");

  function handleCopy() {
    onCopy?.(fullText);
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      void navigator.clipboard.writeText(fullText);
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }

  const statusLabel =
    draft.status === "blocked"
      ? t("specialist.review.needsWork")
      : reviewStatus === "accepted"
        ? t("specialist.review.accepted")
        : reviewStatus === "rejected"
          ? t("specialist.review.rejected")
          : reviewStatus === "revision_requested"
            ? t("specialist.review.revisionRequested")
            : t("specialist.review.pending");

  return (
    <div
      className="mt-3 rounded-lg border p-3"
      style={{ borderColor: "var(--ms-border-default)", background: "var(--ms-bg-elevated)" }}
      data-testid="specialist-activity-card"
      data-generation-mode={isMock ? "mock" : "real"}
      data-review-status={reviewStatus || "pending"}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-semibold" style={{ color: "var(--ms-text-primary)" }}>
          {specialistName}
        </span>
        {isMock ? (
          <span
            className="rounded px-2 py-0.5 text-[11px] font-semibold"
            style={{ background: "color-mix(in srgb, #b45309 28%, transparent)", color: "#fbbf24" }}
            data-testid="specialist-mock-badge"
          >
            {t("home.testModeBadge")}
          </span>
        ) : null}
      </div>

      <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
        {t("specialist.task")}: {taskText.slice(0, 120)}
      </p>

      {draft.expertise_labels.length > 0 ? (
        <div className="mt-2" data-testid="specialist-expertise">
          <p className="text-xs font-medium" style={{ color: "var(--ms-text-secondary)" }}>
            {t("specialist.expertise")}
          </p>
          <ul className="mt-1 flex flex-wrap gap-1.5">
            {draft.expertise_labels.map((label) => (
              <li
                key={label}
                className="rounded-full px-2 py-0.5 text-[11px]"
                style={{
                  background: "color-mix(in srgb, var(--brand-blue) 12%, transparent)",
                  color: "var(--ms-text-secondary)",
                }}
              >
                {label}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {draft.materials_used.length > 0 ? (
        <div className="mt-2">
          <p className="text-xs font-medium" style={{ color: "var(--ms-text-secondary)" }}>
            {t("specialist.materials")}
          </p>
          <ul className="mt-1 list-disc pl-4 text-[11px]" style={{ color: "var(--ms-text-muted)" }}>
            {draft.materials_used.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div
        className="mt-3 rounded-md border p-2 text-sm"
        style={{ borderColor: "var(--ms-border-default)", background: "var(--ms-bg-surface)" }}
        data-testid="specialist-draft-body"
      >
        {draft.hook ? <p className="font-semibold">{draft.hook}</p> : null}
        {draft.body ? <p className="mt-1 whitespace-pre-wrap">{draft.body}</p> : null}
        {draft.cta ? (
          <p className="mt-1 italic" style={{ color: "var(--ms-text-secondary)" }}>
            {draft.cta}
          </p>
        ) : null}
      </div>

      {draft.assumptions.length > 0 ? (
        <details className="mt-2 text-xs" style={{ color: "var(--ms-text-muted)" }}>
          <summary>{t("specialist.assumptions")}</summary>
          <ul className="mt-1 list-disc pl-4">
            {draft.assumptions.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
        </details>
      ) : null}

      {draft.text_foundation ? (
        <details
          className="mt-2 text-xs"
          style={{ color: "var(--ms-text-muted)" }}
          data-testid="specialist-text-foundation"
        >
          <summary>{t("specialist.textFoundation")}</summary>
          <ul className="mt-1 list-disc pl-4">
            {draft.text_foundation.domain_items.map((item) => (
              <li key={`d-${item}`}>{item}</li>
            ))}
            {draft.text_foundation.external_sources.map((item) => (
              <li key={`e-${item}`}>{item}</li>
            ))}
            {draft.text_foundation.user_materials.map((item) => (
              <li key={`u-${item}`}>{item}</li>
            ))}
            {draft.text_foundation.softened_or_removed_claims.map((item) => (
              <li key={`s-${item}`}>
                {t("specialist.foundation.removed")}: {item}
              </li>
            ))}
          </ul>
        </details>
      ) : null}

      <p className="mt-2 text-xs" style={{ color: "var(--ms-text-muted)" }} data-testid="specialist-review-status">
        {t("specialist.status")}: {statusLabel}
      </p>

      <div className="mt-2 flex flex-wrap gap-3 text-xs">
        <button
          type="button"
          className="underline"
          style={{ color: "var(--ms-text-muted)" }}
          disabled={busy}
          onClick={() => onReview?.("accept")}
          data-testid="specialist-accept"
        >
          {t("specialist.action.accept")}
        </button>
        <button
          type="button"
          className="underline"
          style={{ color: "var(--ms-text-muted)" }}
          disabled={busy}
          onClick={() => onReview?.("request_revision")}
          data-testid="specialist-revise"
        >
          {t("specialist.action.revise")}
        </button>
        <button
          type="button"
          className="underline"
          style={{ color: "var(--ms-text-muted)" }}
          disabled={busy}
          onClick={() => onReview?.("create_variant")}
          data-testid="specialist-variant"
        >
          {t("specialist.action.variant")}
        </button>
        <button
          type="button"
          className="underline"
          style={{ color: "var(--ms-text-muted)" }}
          onClick={handleCopy}
          data-testid="specialist-copy"
        >
          {copied ? t("specialist.action.copied") : t("specialist.action.copy")}
        </button>
        <button
          type="button"
          className="underline"
          style={{ color: "var(--ms-text-muted)" }}
          disabled={busy}
          onClick={() => onReview?.("reject")}
          data-testid="specialist-reject"
        >
          {t("specialist.action.reject")}
        </button>
      </div>

      {showDiag ? (
        <details
          className="mt-2 border-t pt-2 text-xs"
          style={{ borderColor: "var(--ms-border-default)", color: "var(--ms-text-muted)" }}
          data-testid="specialist-diagnostics"
        >
          <summary>{t("home.diagnostics")}</summary>
          <p>
            provider={executionProvider || "—"} · model={executionModel || "—"} · prompt=
            {promptPackageHash ? promptPackageHash.slice(0, 22) + "…" : "—"} · quality=
            {draft.quality_check.score} · gates=
            {draft.quality_check.gate_decision || (draft.quality_check.passed ? "pass" : "block")} ·
            {draft.quality_check.critical_failures?.length
              ? draft.quality_check.critical_failures.join(",")
              : draft.quality_check.issues.join(",") || "—"}
          </p>
        </details>
      ) : null}
    </div>
  );
}
