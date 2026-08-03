"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth/auth-context";
import { BrandLogoHero } from "@/components/brand/brand-logo";
import { WorkspaceNav } from "@/components/workspace/workspace-nav";
import { getApiBaseUrl } from "@/lib/api/config";
import { useLocale } from "@/lib/i18n";

/**
 * Developer Workspace — service console only. Not Commercial Home.
 * Diagnostics, internal routes, runtime links. No owner/recovery preview entry points.
 */
export function DeveloperWorkspaceView() {
  const { user } = useAuth();
  const { t } = useLocale();
  const apiBase = getApiBaseUrl();

  const internalLinks = [
    { href: "/workspace/investigations", label: t("nav.investigations") },
    { href: "/workspace/verdicts", label: t("nav.verdicts") },
    { href: "/workspace/strategies", label: t("nav.strategies") },
    { href: "/workspace/implementation", label: t("nav.implementation") },
    { href: "/workspace/tasks", label: t("nav.history") },
    { href: "/workspace/settings", label: t("nav.settings") },
  ];

  return (
    <div
      className="flex min-h-screen flex-col md:flex-row"
      style={{ background: "var(--ms-bg-canvas)", color: "var(--ms-text-primary)" }}
      data-testid="developer-workspace"
      data-home-mode="developer"
    >
      <WorkspaceNav />
      <div className="mx-auto w-full max-w-3xl flex-1 space-y-8 px-4 py-8 sm:px-8">
        <header className="space-y-3">
          <Link
            href="/workspace"
            className="text-sm underline"
            style={{ color: "var(--ms-text-muted)" }}
            data-testid="developer-back-commercial"
          >
            {t("videoStudio.backToWorkspace")}
          </Link>
          <BrandLogoHero className="ms-logo-hero--home" />
          <h1 className="text-2xl font-semibold">{t("agency.openDeveloperWorkspace")}</h1>
          <p className="text-sm" style={{ color: "var(--ms-text-secondary)" }}>
            {user?.email ?? user?.display_name ?? t("home.defaultOwnerName")}
          </p>
        </header>

        <section className="space-y-3 rounded-xl border p-4" style={{ borderColor: "var(--ms-border-default)" }}>
          <h2 className="text-sm font-semibold">{t("home.diagnostics")}</h2>
          <ul className="space-y-2 text-sm">
            <li>
              <a
                href={`${apiBase}/health`}
                target="_blank"
                rel="noreferrer"
                className="underline"
                data-testid="developer-health-link"
              >
                GET /health
              </a>
            </li>
            <li>
              <a
                href={`${apiBase}/health/runtime`}
                target="_blank"
                rel="noreferrer"
                className="underline"
                data-testid="developer-runtime-link"
              >
                GET /health/runtime
              </a>
            </li>
          </ul>
        </section>

        <section className="space-y-3 rounded-xl border p-4" style={{ borderColor: "var(--ms-border-default)" }}>
          <h2 className="text-sm font-semibold">{t("nav.projects")}</h2>
          <ul className="space-y-2 text-sm">
            {internalLinks.map((link) => (
              <li key={link.href}>
                <Link href={link.href} className="underline" data-testid={`developer-link-${link.href}`}>
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
