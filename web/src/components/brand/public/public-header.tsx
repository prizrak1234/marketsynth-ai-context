"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { CommercialButton } from "@/components/commercial/commercial-button";
import { PRODUCT_BRAND } from "@/lib/brand/product-brand";
import { useAuthOptional } from "@/lib/auth/auth-context";
import { useLocale } from "@/lib/i18n/locale-context";
import {
  resolveLandingPrimaryCtaHref,
} from "@/lib/landing/public-landing";
import { CANONICAL_COMMERCIAL_ROUTES } from "@/lib/routes/commercial-routes";

export function PublicHeader() {
  const { t } = useLocale();
  const { user, loading } = useAuthOptional();
  const [menuOpen, setMenuOpen] = useState(false);
  const authenticated = !loading && Boolean(user);
  const primaryHref = resolveLandingPrimaryCtaHref(authenticated) ?? CANONICAL_COMMERCIAL_ROUTES.login;
  const primaryLabel = authenticated
    ? t("landing.header.ctaNewIdea")
    : t("landing.hero.primaryCta");

  return (
    <header
      className="sticky top-0 z-40 border-b px-4 py-3 sm:px-10"
      style={{
        borderColor: "var(--ms-border-default)",
        background: "color-mix(in srgb, var(--ms-bg-canvas) 92%, transparent)",
        backdropFilter: "blur(8px)",
      }}
      data-testid="public-landing-header"
    >
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
        <Link
          href="/"
          className="flex min-w-0 items-center gap-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--ms-brand-primary)]"
          data-testid="public-landing-brand"
        >
          <Image
            src={PRODUCT_BRAND.assets.symbol}
            alt=""
            width={32}
            height={32}
            className="h-8 w-8 shrink-0"
            aria-hidden
          />
          <span className="truncate text-sm font-semibold" style={{ color: "var(--ms-text-primary)" }}>
            {PRODUCT_BRAND.displayName}
          </span>
          <span className="hidden text-xs sm:inline" style={{ color: "var(--ms-text-muted)" }}>
            {t("brand.captionRu")}
          </span>
        </Link>

        <nav
          className="hidden items-center gap-3 md:flex"
          aria-label={t("landing.header.navLabel")}
        >
          {!authenticated ? (
            <CommercialButton
              href={CANONICAL_COMMERCIAL_ROUTES.login}
              variant="secondary"
              testId="public-header-login"
            >
              {t("landing.header.login")}
            </CommercialButton>
          ) : (
            <CommercialButton
              href={CANONICAL_COMMERCIAL_ROUTES.projectsList}
              variant="secondary"
              testId="public-header-workspace"
            >
              {t("landing.header.workspace")}
            </CommercialButton>
          )}
          <CommercialButton href={primaryHref} testId="public-header-primary-cta">
            {primaryLabel}
          </CommercialButton>
        </nav>

        <button
          type="button"
          className="inline-flex rounded-md border px-3 py-2 text-sm font-medium md:hidden focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--ms-brand-primary)]"
          style={{
            borderColor: "var(--ms-border-default)",
            color: "var(--ms-text-primary)",
          }}
          aria-expanded={menuOpen}
          aria-controls="public-landing-mobile-menu"
          data-testid="public-landing-mobile-menu-button"
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? t("nav.closeMenu") : t("nav.menu")}
        </button>
      </div>

      {menuOpen ? (
        <nav
          id="public-landing-mobile-menu"
          className="mx-auto mt-3 flex max-w-6xl flex-col gap-2 border-t pt-3 md:hidden"
          style={{ borderColor: "var(--ms-border-default)" }}
          aria-label={t("landing.header.mobileNavLabel")}
          data-testid="public-landing-mobile-menu"
        >
          {!authenticated ? (
            <CommercialButton
              href={CANONICAL_COMMERCIAL_ROUTES.login}
              variant="secondary"
              testId="public-header-mobile-login"
              className="w-full"
            >
              {t("landing.header.login")}
            </CommercialButton>
          ) : (
            <CommercialButton
              href={CANONICAL_COMMERCIAL_ROUTES.projectsList}
              variant="secondary"
              testId="public-header-mobile-workspace"
              className="w-full"
            >
              {t("landing.header.workspace")}
            </CommercialButton>
          )}
          <CommercialButton
            href={primaryHref}
            testId="public-header-mobile-primary-cta"
            className="w-full"
          >
            {primaryLabel}
          </CommercialButton>
        </nav>
      ) : null}
    </header>
  );
}
