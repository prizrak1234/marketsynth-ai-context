"use client";

import Image from "next/image";
import Link from "next/link";
import { PRODUCT_BRAND } from "@/lib/brand/product-brand";
import { useAuthOptional } from "@/lib/auth/auth-context";
import { canonicalIntakeHref, loginNextHref } from "@/lib/routes/commercial-surface";

/**
 * First-screen brand composition for Marketsynth.
 *
 * FREEZE (2026-07-13): User-approved home look.
 * Do not change layout, logo placement, copy, or colors until explicitly unfrozen.
 * See docs/marketsynth_home_screen_freeze.md
 *
 * Copy is frozen in PRODUCT_BRAND.hero — do not rewrite without approval.
 */
export function MarketsynthHomeHero() {
  const { hero, displayName, logoDisplayName, assets } = PRODUCT_BRAND;
  const { user, loading } = useAuthOptional();
  const intakeHref = canonicalIntakeHref();
  const ctaHref = !loading && user ? intakeHref : loginNextHref(intakeHref);

  return (
    <section
      className="relative overflow-hidden rounded-xl border px-6 py-10 sm:px-10 sm:py-14"
      style={{
        background:
          "radial-gradient(ellipse 80% 60% at 50% 0%, color-mix(in srgb, var(--brand-blue) 18%, transparent), transparent 55%), var(--ms-bg-surface)",
        borderColor: "var(--ms-border-default)",
        color: "var(--ms-text-primary)",
      }}
    >
      <div className="mx-auto flex max-w-3xl flex-col items-center text-center">
        <Image
          src={assets.master}
          alt={logoDisplayName}
          width={520}
          height={280}
          priority
          className="h-auto w-full max-w-[min(100%,28rem)] object-contain"
        />

        <p
          className="mt-6 text-xs font-semibold uppercase tracking-[0.28em]"
          style={{ color: "var(--ms-brand-secondary)" }}
        >
          {displayName}
        </p>

        <h1
          className="mt-4 text-balance text-2xl font-semibold leading-snug tracking-tight sm:text-3xl"
          style={{ color: "var(--ms-text-primary)" }}
        >
          {hero.headline}
        </h1>

        <p
          className="mt-4 max-w-2xl text-pretty text-sm leading-relaxed sm:text-base"
          style={{ color: "var(--ms-text-secondary)" }}
        >
          {hero.subheadline}
        </p>

        <ul className="mt-8 w-full max-w-xl space-y-3 text-left text-sm sm:text-[0.95rem]">
          {hero.benefits.map((item) => (
            <li
              key={item}
              className="flex gap-3 rounded-lg border px-4 py-3"
              style={{
                borderColor: "var(--ms-border-default)",
                background: "var(--ms-bg-elevated)",
                color: "var(--ms-text-secondary)",
              }}
            >
              <span
                className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full"
                style={{ background: "var(--ms-brand-primary)" }}
                aria-hidden
              />
              <span>{item}</span>
            </li>
          ))}
        </ul>

        <Link
          href={ctaHref}
          className="mt-10 inline-flex items-center justify-center rounded-md px-6 py-3 text-sm font-semibold transition-opacity hover:opacity-90"
          data-testid="public-landing-cta"
          style={{
            background: "var(--ms-brand-primary)",
            color: "var(--ms-text-primary)",
            boxShadow: "0 0 0 1px color-mix(in srgb, var(--brand-blue-light) 35%, transparent)",
          }}
        >
          {hero.primaryCta}
        </Link>
      </div>
    </section>
  );
}
