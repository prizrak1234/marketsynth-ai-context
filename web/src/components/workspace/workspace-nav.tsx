"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { BrandLogoMark } from "@/components/brand/brand-logo";
import { isHomeDeveloperMode } from "@/lib/home/developer-mode";
import {
  getWorkspaceNavigationCapabilities,
  type CapabilityNavItem,
} from "@/lib/product-capabilities";
import { useLocale } from "@/lib/i18n";
import { cn } from "@/lib/utils";

function workspaceNavItems(developerMode: boolean): ReadonlyArray<CapabilityNavItem> {
  return getWorkspaceNavigationCapabilities({
    developerMode,
    role: "owner",
  });
}

function NavLinks({
  pathname,
  onNavigate,
  items,
}: {
  pathname: string;
  onNavigate?: () => void;
  items: ReadonlyArray<CapabilityNavItem>;
}) {
  const { t } = useLocale();
  return (
    <nav className="flex flex-1 flex-col gap-0.5 p-3">
      {items.map((item) => {
        const active = item.exact
          ? pathname === item.href
          : pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link
            key={`${item.href}-${item.key}`}
            href={item.href}
            data-testid={`nav-${item.href.replace(/\//g, "-").replace(/^-/, "")}`}
            onClick={onNavigate}
            className={cn("rounded-md px-3 py-2 text-sm transition-colors")}
            style={
              active
                ? {
                    background: "var(--ms-bg-elevated)",
                    color: "var(--ms-text-primary)",
                    boxShadow:
                      "inset 0 0 0 1px color-mix(in srgb, var(--brand-blue) 45%, transparent)",
                  }
                : { color: "var(--ms-text-muted)" }
            }
          >
            {t(item.key)}
          </Link>
        );
      })}
    </nav>
  );
}

export function WorkspaceNav() {
  const pathname = usePathname();
  const router = useRouter();
  const { t, locale } = useLocale();
  const [open, setOpen] = useState(false);
  const [developerMode, setDeveloperMode] = useState(false);

  useEffect(() => {
    setDeveloperMode(isHomeDeveloperMode());
  }, [pathname]);

  const navItems = workspaceNavItems(developerMode);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      <div
        className="flex items-center gap-3 border-b px-3 py-2 md:hidden"
        style={{
          borderColor: "var(--ms-border-default)",
          background: "var(--ms-bg-surface)",
        }}
        data-testid="workspace-nav-mobile"
      >
        <button
          type="button"
          className="rounded-md border px-2.5 py-1.5 text-sm"
          style={{
            borderColor: "var(--ms-border-default)",
            color: "var(--ms-text-primary)",
          }}
          aria-expanded={open}
          aria-controls="workspace-nav-drawer"
          data-testid="workspace-nav-menu"
          onClick={() => setOpen((v) => !v)}
        >
          {t("nav.menu")}
        </button>
        <button
          type="button"
          className="text-left"
          onClick={() => router.push("/workspace")}
          aria-label={t("brand.name")}
        >
          <BrandLogoMark size={28} />
        </button>
      </div>

      <aside
        className="hidden w-56 shrink-0 flex-col border-r md:flex"
        style={{
          background: "var(--ms-bg-surface)",
          borderColor: "var(--ms-border-default)",
        }}
        data-testid="workspace-nav"
        data-locale={locale}
        data-nav-mode="agency"
      >
        <div
          className="border-b px-4 py-4"
          style={{ borderColor: "var(--ms-border-default)" }}
        >
          <button
            type="button"
            className="text-left"
            onClick={() => router.push("/workspace")}
            aria-label={t("brand.name")}
          >
            <BrandLogoMark size={30} />
          </button>
          <p className="mt-2 text-xs" style={{ color: "var(--ms-text-muted)" }}>
            {t("brand.captionRu")}
          </p>
        </div>
        <NavLinks pathname={pathname} items={navItems} />
      </aside>

      {open ? (
        <div
          className="fixed inset-0 z-40 md:hidden"
          data-testid="workspace-nav-drawer"
          id="workspace-nav-drawer"
        >
          <button
            type="button"
            className="absolute inset-0"
            style={{ background: "color-mix(in srgb, black 45%, transparent)" }}
            aria-label={t("nav.closeMenu")}
            onClick={() => setOpen(false)}
          />
          <aside
            className="relative z-10 flex h-full w-64 max-w-[85vw] flex-col border-r"
            style={{
              background: "var(--ms-bg-surface)",
              borderColor: "var(--ms-border-default)",
            }}
          >
            <div
              className="border-b px-4 py-3 text-sm font-semibold"
              style={{ borderColor: "var(--ms-border-default)" }}
            >
              {t("brand.name")}
            </div>
            <NavLinks pathname={pathname} items={navItems} onNavigate={() => setOpen(false)} />
          </aside>
        </div>
      ) : null}
    </>
  );
}
