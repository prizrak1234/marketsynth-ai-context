"use client";

import { CommercialButton } from "@/components/commercial/commercial-button";
import { CommercialCard } from "@/components/commercial/commercial-card";
import { CommercialTimeline } from "@/components/commercial/commercial-timeline";
import { PublicSection } from "@/components/brand/public/public-section";
import { useAuthOptional } from "@/lib/auth/auth-context";
import { useLocale } from "@/lib/i18n/locale-context";
import { resolveLandingPrimaryCtaHref } from "@/lib/landing/public-landing";

export function CommercialLandingContent() {
  const { t } = useLocale();
  const { user, loading } = useAuthOptional();
  const authenticated = !loading && Boolean(user);
  const primaryHref = resolveLandingPrimaryCtaHref(authenticated);

  const valueCards = [
    {
      id: "evidence",
      title: t("landing.value.evidence.title"),
      body: t("landing.value.evidence.body"),
    },
    {
      id: "decision",
      title: t("landing.value.decision.title"),
      body: t("landing.value.decision.body"),
    },
    {
      id: "execution",
      title: t("landing.value.execution.title"),
      body: t("landing.value.execution.body"),
    },
  ];

  const howSteps = [
    { id: "describe", label: t("landing.how.step1"), status: "done" as const },
    { id: "research", label: t("landing.how.step2"), status: "done" as const },
    { id: "result", label: t("landing.how.step3"), status: "done" as const },
    { id: "next", label: t("landing.how.step4"), status: "pending" as const },
  ];

  return (
    <>
      <section
        className="border-b px-4 py-12 sm:px-10 sm:py-16 lg:py-20"
        style={{ borderColor: "var(--ms-border-default)" }}
        data-testid="public-landing-hero"
      >
        <div className="mx-auto max-w-4xl">
          <p
            className="text-xs font-semibold uppercase tracking-[0.24em]"
            style={{ color: "var(--ms-brand-secondary)" }}
          >
            {t("brand.captionRu")}
          </p>
          <h1
            className="mt-4 text-balance text-3xl font-semibold leading-tight tracking-tight sm:text-4xl lg:text-[2.35rem]"
            style={{ color: "var(--ms-text-primary)" }}
            data-testid="public-landing-headline"
          >
            {t("landing.hero.headline")}
          </h1>
          <p
            className="mt-5 max-w-3xl text-pretty text-base leading-relaxed sm:text-lg"
            style={{ color: "var(--ms-text-secondary)" }}
            data-testid="public-landing-subheadline"
          >
            {t("landing.hero.subheadline")}
          </p>
          <ul className="mt-8 space-y-3 text-sm sm:text-base" data-testid="public-landing-benefits">
            {[1, 2, 3].map((index) => (
              <li
                key={index}
                className="flex gap-3 rounded-lg border px-4 py-3"
                style={{
                  borderColor: "var(--ms-border-default)",
                  background: "var(--ms-bg-surface)",
                  color: "var(--ms-text-secondary)",
                }}
              >
                <span
                  className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full"
                  style={{ background: "var(--ms-brand-primary)" }}
                  aria-hidden
                />
                <span>{t(`landing.hero.benefit${index}`)}</span>
              </li>
            ))}
          </ul>
          <div className="mt-10 flex flex-col gap-3 sm:flex-row sm:items-center">
            {primaryHref ? (
              <CommercialButton href={primaryHref} testId="public-landing-cta">
                {t("landing.hero.primaryCta")}
              </CommercialButton>
            ) : null}
            <CommercialButton
              href="#how-it-works"
              variant="secondary"
              testId="public-landing-secondary-cta"
            >
              {t("landing.hero.secondaryCta")}
            </CommercialButton>
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-6xl px-4 sm:px-10">
        <PublicSection
          id="core-value"
          title={t("landing.value.title")}
          subtitle={t("landing.value.subtitle")}
          testId="public-landing-core-value"
        >
          <div className="grid gap-4 md:grid-cols-3">
            {valueCards.map((card) => (
              <CommercialCard key={card.id} testId={`public-landing-value-${card.id}`}>
                <h3 className="text-base font-semibold" style={{ color: "var(--ms-text-primary)" }}>
                  {card.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--ms-text-secondary)" }}>
                  {card.body}
                </p>
              </CommercialCard>
            ))}
          </div>
        </PublicSection>

        <PublicSection
          id="how-it-works"
          title={t("landing.how.title")}
          subtitle={t("landing.how.subtitle")}
          testId="public-landing-how-it-works"
        >
          <CommercialTimeline
            stages={howSteps}
            title={t("landing.how.timelineTitle")}
            testId="public-landing-how-timeline"
            embedded
          />
        </PublicSection>

        <PublicSection
          id="what-you-receive"
          title={t("landing.receive.title")}
          subtitle={t("landing.receive.subtitle")}
          testId="public-landing-what-you-receive"
        >
          <div className="grid gap-4 lg:grid-cols-2">
            <CommercialCard testId="public-landing-outcome-verdict">
              <h3 className="text-base font-semibold">{t("landing.receive.verdict.title")}</h3>
              <ul className="mt-3 space-y-2 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
                {[1, 2, 3, 4].map((i) => (
                  <li key={i}>{t(`landing.receive.verdict.item${i}`)}</li>
                ))}
              </ul>
            </CommercialCard>
            <CommercialCard testId="public-landing-outcome-partial">
              <h3 className="text-base font-semibold">{t("landing.receive.partial.title")}</h3>
              <ul className="mt-3 space-y-2 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
                {[1, 2, 3, 4].map((i) => (
                  <li key={i}>{t(`landing.receive.partial.item${i}`)}</li>
                ))}
              </ul>
            </CommercialCard>
          </div>
        </PublicSection>

        <PublicSection
          id="trust"
          title={t("landing.trust.title")}
          testId="public-landing-trust"
        >
          <CommercialCard testId="public-landing-trust-panel">
            <p className="text-sm leading-relaxed sm:text-base" style={{ color: "var(--ms-text-secondary)" }}>
              {t("landing.trust.body")}
            </p>
            <ul className="mt-4 space-y-2 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
              {[1, 2, 3, 4, 5].map((i) => (
                <li key={i}>{t(`landing.trust.principle${i}`)}</li>
              ))}
            </ul>
          </CommercialCard>
        </PublicSection>

        <section
          className="py-12 sm:py-16"
          data-testid="public-landing-final-cta"
          aria-labelledby="final-cta-heading"
        >
          <CommercialCard padding="lg">
            <h2 id="final-cta-heading" className="text-xl font-semibold sm:text-2xl">
              {t("landing.final.title")}
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed sm:text-base" style={{ color: "var(--ms-text-secondary)" }}>
              {t("landing.final.body")}
            </p>
            <div className="mt-6">
              {primaryHref ? (
                <CommercialButton href={primaryHref} testId="public-landing-final-cta">
                  {t("landing.hero.primaryCta")}
                </CommercialButton>
              ) : null}
            </div>
          </CommercialCard>
        </section>
      </div>
    </>
  );
}
