"use client";

import { useEffect, useState } from "react";
import { BrandLogoMark } from "@/components/brand/brand-logo";
import {
  USER_INTENTS,
  type UserIntent,
  type UserSubIntent,
} from "@/lib/home/user-intent-catalog";
import { isHomeIntentPubliclyAvailable } from "@/lib/product-capabilities";
import { useLocale } from "@/lib/i18n";

type Props = {
  draftText: string;
  onDraftChange: (value: string) => void;
  onSubmitFreeText: () => void;
  onSelectIntent: (intent: UserIntent, subIntent?: UserSubIntent) => void;
  loading?: boolean;
  error?: string | null;
  apiUnavailable?: boolean;
};

/** Intent-driven commercial entry — task first, brand second. */
export function IntentStartPanel({
  draftText,
  onDraftChange,
  onSubmitFreeText,
  onSelectIntent,
  loading = false,
  error = null,
  apiUnavailable = false,
}: Props) {
  const { t } = useLocale();
  const [expandedContent, setExpandedContent] = useState(false);

  useEffect(() => {
    if (expandedContent) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setExpandedContent(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [expandedContent]);

  const contentIntent = USER_INTENTS.find((i) => i.id === "create-content");
  const publicIntents = USER_INTENTS.filter((intent) => isHomeIntentPubliclyAvailable(intent.id));

  return (
    <div className="space-y-6" data-testid="intent-start-panel">
      <header className="space-y-3" data-testid="home-hero">
        <div className="flex items-center gap-3" data-testid="home-brand-block">
          <BrandLogoMark size={36} />
          <div>
            <p
              className="text-xs font-semibold uppercase tracking-wide"
              style={{ color: "var(--ms-brand-secondary)" }}
              data-testid="home-brand-caption"
            >
              {t("brand.captionRu")}
            </p>
            <p className="text-sm font-semibold">{t("brand.name")}</p>
          </div>
        </div>

        <h1
          className="text-xl font-bold leading-snug whitespace-pre-line sm:text-2xl"
          data-testid="home-offer"
        >
          {t("home.offer")}
        </h1>
        <p
          className="max-w-2xl text-sm leading-relaxed sm:text-base"
          style={{ color: "var(--ms-text-secondary)" }}
          data-testid="home-support"
        >
          {t("home.support")}
        </p>
        <ul
          className="grid gap-1 text-sm sm:grid-cols-3"
          style={{ color: "var(--ms-text-muted)" }}
          data-testid="home-brand-points"
        >
          <li>{t("intent.brandPoint1")}</li>
          <li>{t("intent.brandPoint2")}</li>
          <li>{t("intent.brandPoint3")}</li>
        </ul>
      </header>

      <section className="space-y-3" aria-labelledby="home-task-heading">
        <h2 id="home-task-heading" className="text-base font-semibold" data-testid="home-question">
          {t("intent.whatToDo")}
        </h2>
        <label htmlFor="home-intent-input" className="sr-only">
          {t("intent.whatToDo")}
        </label>
        <textarea
          id="home-intent-input"
          rows={3}
          value={draftText}
          disabled={loading || apiUnavailable}
          onChange={(e) => onDraftChange(e.target.value)}
          placeholder={t("intent.taskPlaceholder")}
          className="w-full resize-y rounded-xl border px-4 py-3 text-sm leading-relaxed"
          style={{
            borderColor: "var(--ms-border-default)",
            background: "var(--ms-bg-surface)",
            color: "var(--ms-text-primary)",
          }}
          data-testid="home-intent-input"
        />
        <button
          type="button"
          disabled={loading || apiUnavailable}
          onClick={onSubmitFreeText}
          className="rounded-md px-5 py-2.5 text-sm font-semibold disabled:opacity-50"
          style={{
            background: "var(--ms-brand-primary)",
            color: "var(--ms-text-on-brand, #fff)",
          }}
          data-testid="home-intent-submit"
        >
          {loading ? t("common.loading") : t("intent.startWork")}
        </button>
      </section>

      <section className="space-y-3" aria-labelledby="intent-cards-heading">
        <h2 id="intent-cards-heading" className="text-sm font-semibold" style={{ color: "var(--ms-text-secondary)" }}>
          {t("intent.orChooseCategory")}
        </h2>
        <div
          className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3"
          data-testid="home-action-cards"
        >
          {publicIntents.map((intent) => {
            const isContent = intent.id === "create-content";
            const isPlanned = intent.status === "planned";
            return (
              <button
                key={intent.id}
                type="button"
                disabled={loading || apiUnavailable || isPlanned}
                onClick={() => {
                  if (isContent) {
                    setExpandedContent(true);
                    return;
                  }
                  onSelectIntent(intent);
                }}
                className="rounded-xl border px-4 py-4 text-left transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-50"
                style={{
                  borderColor: "var(--ms-border-default)",
                  background: "var(--ms-bg-surface)",
                  color: "var(--ms-text-primary)",
                }}
                data-testid={`intent-card-${intent.id}`}
                data-intent-status={intent.status}
              >
                <span className="text-lg" aria-hidden="true">
                  {intent.emoji}
                </span>
                <p className="mt-2 font-semibold">{t(intent.titleKey)}</p>
                <p className="mt-1 text-xs leading-relaxed" style={{ color: "var(--ms-text-secondary)" }}>
                  {t(intent.descriptionKey)}
                </p>
                {intent.status === "partial" ? (
                  <span
                    className="mt-2 inline-block text-[11px] font-medium"
                    style={{ color: "var(--ms-text-muted)" }}
                  >
                    {t("intent.partialBadge")}
                  </span>
                ) : null}
                {isPlanned ? (
                  <span
                    className="mt-2 inline-block text-[11px] font-medium"
                    style={{ color: "var(--ms-text-muted)" }}
                  >
                    {t("intent.plannedBadge")}
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>
      </section>

      {expandedContent && contentIntent?.subIntents ? (
        <section
          className="rounded-xl border p-4"
          style={{
            borderColor: "var(--ms-border-default)",
            background: "var(--ms-bg-elevated)",
          }}
          data-testid="intent-content-subpanel"
          role="dialog"
          aria-labelledby="content-sub-heading"
        >
          <div className="mb-3 flex items-center justify-between gap-2">
            <h3 id="content-sub-heading" className="font-semibold">
              {t("intent.createContent.title")}
            </h3>
            <button
              type="button"
              className="text-sm underline"
              style={{ color: "var(--ms-text-muted)" }}
              onClick={() => setExpandedContent(false)}
              data-testid="intent-content-sub-close"
            >
              {t("common.close")}
            </button>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            {contentIntent.subIntents.map((sub) => (
              <button
                key={sub.id}
                type="button"
                disabled={loading || apiUnavailable || sub.status === "planned"}
                onClick={() => {
                  setExpandedContent(false);
                  onSelectIntent(contentIntent, sub);
                }}
                className="rounded-lg border px-3 py-3 text-left text-sm focus-visible:outline focus-visible:outline-2"
                style={{
                  borderColor: "var(--ms-border-default)",
                  background: "var(--ms-bg-surface)",
                }}
                data-testid={`intent-sub-${sub.id}`}
                data-sub-status={sub.status}
              >
                {t(sub.titleKey)}
              </button>
            ))}
          </div>
        </section>
      ) : null}

      {error ? (
        <p className="text-sm" role="alert" style={{ color: "var(--ms-danger, #b42318)" }}>
          {error}
        </p>
      ) : null}
    </div>
  );
}
