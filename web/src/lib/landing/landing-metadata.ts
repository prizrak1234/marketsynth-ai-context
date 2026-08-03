import type { Metadata } from "next";
import type { AppLocale } from "@/lib/i18n/config";
import { translate } from "@/lib/i18n/domain-labels";

export function getLandingPageMetadata(locale: AppLocale = "ru"): Metadata {
  const title = translate(locale, "landing.meta.title");
  const description = translate(locale, "landing.meta.description");
  return {
    title,
    description,
    openGraph: {
      title,
      description,
      type: "website",
    },
  };
}
