"use client";

import { AuthProvider } from "@/lib/auth/auth-context";
import { LocaleProvider, useLocale } from "@/lib/i18n/locale-context";
import { CommercialLandingContent } from "@/components/brand/public/commercial-landing-content";
import { PublicFooter } from "@/components/brand/public/public-footer";
import { PublicHeader } from "@/components/brand/public/public-header";
import { PublicPageShell } from "@/components/brand/public/public-page-shell";

function PublicLandingBody() {
  const { t } = useLocale();
  return (
    <PublicPageShell skipLabel={t("landing.skipToContent")}>
      <PublicHeader />
      <main id="main-content">
        <CommercialLandingContent />
      </main>
      <PublicFooter />
    </PublicPageShell>
  );
}

/** Client shell for public landing — session-aware CTA without AppShell. */
export function PublicLandingView() {
  return (
    <AuthProvider>
      <LocaleProvider>
        <PublicLandingBody />
      </LocaleProvider>
    </AuthProvider>
  );
}
