"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { PRODUCT_BRAND } from "@/lib/brand/product-brand";
import { cn } from "@/lib/utils";

const navItems: Array<{
  href: string;
  label: string;
  match: (path: string) => boolean;
  disabled?: boolean;
}> = [
  { href: "/dashboard", label: "Dashboard", match: (path) => path === "/dashboard" },
  {
    href: "/campaigns",
    label: "Campaigns",
    match: (path) => path === "/campaigns" || path.startsWith("/campaigns/"),
  },
  { href: "/review", label: "Review Queue", match: (path) => path === "/review" },
  {
    href: "/agents/chat",
    label: "AI Chat",
    match: (path) => path.startsWith("/agents/chat"),
  },
  {
    href: "/settings/channels",
    label: "Channels",
    match: (path) => path.startsWith("/settings/channels"),
  },
  {
    href: "/settings/beta-qa",
    label: "Beta QA",
    match: (path) => path.startsWith("/settings/beta-qa"),
  },
  {
    href: "/assets",
    label: "Assets",
    match: (path) => path.startsWith("/assets/"),
    disabled: true,
  },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="flex w-56 shrink-0 flex-col border-r"
      style={{
        background: "var(--ms-bg-surface)",
        borderColor: "var(--ms-border-default)",
        color: "var(--ms-text-primary)",
      }}
    >
      <div
        className="border-b px-4 py-4"
        style={{ borderColor: "var(--ms-border-default)" }}
      >
        <p
          className="text-sm font-semibold"
          style={{ color: "var(--ms-brand-secondary)" }}
        >
          {PRODUCT_BRAND.displayName}
        </p>
        <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
          Internal Operations
        </p>
      </div>
      <nav className="flex flex-1 flex-col gap-1 p-3">
        {navItems
          .filter(
            (item) =>
              process.env.NODE_ENV === "production"
                ? item.href !== "/settings/beta-qa"
                : true,
          )
          .map((item) => {
          const active = !item.disabled && item.match(pathname);
          if ("disabled" in item && item.disabled) {
            return (
              <span
                key={item.href}
                className="rounded-md px-3 py-2 text-sm"
                style={{ color: "color-mix(in srgb, var(--ms-text-muted) 70%, transparent)" }}
                title="Open a specific asset via /assets/{id}"
              >
                {item.label}
              </span>
            );
          }
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn("rounded-md px-3 py-2 text-sm transition-colors")}
              style={
                active
                  ? {
                      background: "var(--ms-bg-elevated)",
                      color: "var(--ms-text-primary)",
                      boxShadow:
                        "inset 0 0 0 1px color-mix(in srgb, var(--brand-blue) 40%, transparent)",
                    }
                  : {
                      color: "var(--ms-text-muted)",
                    }
              }
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
      <p
        className="border-t px-4 py-3 text-xs"
        style={{
          borderColor: "var(--ms-border-default)",
          color: "var(--ms-text-muted)",
        }}
      >
        Marketsynth · brand foundation
      </p>
    </aside>
  );
}
