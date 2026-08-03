"use client";



import Link from "next/link";

import { BrandLogoMark } from "@/components/brand/brand-logo";

import { PRODUCT_BRAND } from "@/lib/brand/product-brand";

import {

  CANONICAL_COMMERCIAL_ROUTES,

  canonicalIntakeHref,

} from "@/lib/routes/commercial-routes";

import { useLocale } from "@/lib/i18n";



type CanonicalCommercialEntryProps = {

  showProjectsLink?: boolean;

};



/** RUNTIME-01E — single public commercial entry (7-step intake). */

export function CanonicalCommercialEntryPanel({

  showProjectsLink = true,

}: CanonicalCommercialEntryProps) {

  const { t } = useLocale();

  const { hero, displayName } = PRODUCT_BRAND;



  return (

    <section

      className="rounded-2xl border px-6 py-8 sm:px-10 sm:py-10"

      style={{

        background:

          "radial-gradient(ellipse 85% 55% at 50% 0%, color-mix(in srgb, var(--brand-blue) 16%, transparent), transparent 60%), var(--ms-bg-surface)",

        borderColor: "var(--ms-border-default)",

      }}

      data-testid="canonical-commercial-entry"

    >

      <header className="mx-auto max-w-3xl space-y-5 text-center sm:text-left">

        <div

          className="flex flex-col items-center gap-3 sm:flex-row sm:items-center"

          data-testid="home-brand-block"

        >

          <BrandLogoMark size={44} />

          <div>

            <p

              className="text-sm font-semibold uppercase tracking-[0.18em]"

              style={{ color: "var(--ms-brand-secondary)" }}

              data-testid="home-brand-caption"

            >

              {t("brand.captionRu")}

            </p>

            <p className="text-lg font-semibold tracking-tight">{displayName}</p>

          </div>

        </div>



        <h1

          className="text-balance text-2xl font-bold leading-tight tracking-tight sm:text-3xl lg:text-4xl"

          data-testid="canonical-entry-headline"

        >

          {hero.headline}

        </h1>

        <p

          className="mx-auto max-w-2xl text-pretty text-base leading-relaxed sm:mx-0 sm:text-lg"

          style={{ color: "var(--ms-text-secondary)" }}

          data-testid="canonical-entry-subheadline"

        >

          {hero.subheadline}

        </p>

        <ul

          className="mx-auto grid max-w-2xl gap-3 text-left sm:mx-0"

          data-testid="canonical-entry-benefits"

        >

          {hero.benefits.map((item) => (

            <li

              key={item}

              className="flex gap-3 rounded-lg border px-4 py-3 text-base leading-relaxed"

              style={{

                borderColor: "var(--ms-border-default)",

                background: "var(--ms-bg-elevated)",

                color: "var(--ms-text-secondary)",

              }}

            >

              <span

                className="mt-2 h-2 w-2 shrink-0 rounded-full"

                style={{ background: "var(--ms-brand-primary)" }}

                aria-hidden

              />

              <span>{item}</span>

            </li>

          ))}

        </ul>

      </header>



      <div

        className="mx-auto mt-8 flex max-w-3xl flex-wrap justify-center gap-3 sm:justify-start"

        data-testid="canonical-entry-actions"

      >

        <Link

          href={canonicalIntakeHref()}

          className="inline-flex min-w-[12rem] items-center justify-center rounded-lg px-6 py-3.5 text-base font-semibold transition-opacity hover:opacity-90"

          style={{

            background: "var(--ms-brand-primary)",

            color: "var(--ms-text-on-brand, #fff)",

            boxShadow:

              "0 0 0 1px color-mix(in srgb, var(--brand-blue-light) 35%, transparent)",

          }}

          data-testid="canonical-entry-cta"

        >

          {hero.primaryCta}

        </Link>

        {showProjectsLink ? (

          <Link

            href={CANONICAL_COMMERCIAL_ROUTES.projectsList}

            className="inline-flex min-w-[10rem] items-center justify-center rounded-lg border px-6 py-3.5 text-base font-semibold transition-colors hover:opacity-95"

            style={{

              borderColor: "var(--ms-border-default)",

              background: "var(--ms-bg-elevated)",

              color: "var(--ms-text-primary)",

            }}

            data-testid="canonical-entry-projects"

          >

            {t("nav.projects")}

          </Link>

        ) : null}

      </div>

    </section>

  );

}


