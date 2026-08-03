"use client";

import Link from "next/link";
import { CommercialCard } from "@/components/commercial/commercial-card";
import { useLocale } from "@/lib/i18n";

type Props = {
  /** Prefer deep-link to a selected project; else projects list. */
  openHref: string;
};

/** Small Home teaser — must not compete with «Проверить идею». */
export function HomeCreativeCapabilityTeaser({ openHref }: Props) {
  const { t } = useLocale();
  return (
    <CommercialCard padding="sm" testId="home-creative-capability-teaser">
      <p className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--ms-text-muted)" }}>
        {t("homeCreativeTeaser.eyebrow")}
      </p>
      <h2 className="mt-1 text-sm font-semibold" style={{ color: "var(--ms-text-primary)" }}>
        {t("homeCreativeTeaser.title")}
      </h2>
      <p className="mt-1 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
        {t("homeCreativeTeaser.body")}
      </p>
      <Link
        href={openHref}
        className="mt-3 inline-block text-sm font-medium underline underline-offset-2"
        style={{ color: "var(--ms-text-accent, var(--ms-brand-primary))" }}
        data-testid="home-creative-teaser-open-project"
      >
        {t("homeCreativeTeaser.cta")}
      </Link>
    </CommercialCard>
  );
}
