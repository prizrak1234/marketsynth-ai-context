"use client";

import Link from "next/link";
import { WorkspaceNav } from "@/components/workspace/workspace-nav";
import { PRODUCT_BRAND } from "@/lib/brand/product-brand";

/** Placeholder for Workspace nav destinations not yet built in Phase A1. */
export function WorkspacePlaceholder({ title }: { title: string }) {
  return (
    <div
      className="flex min-h-screen"
      style={{
        background: "var(--ms-bg-canvas)",
        color: "var(--ms-text-primary)",
      }}
    >
      <WorkspaceNav />
      <main className="flex flex-1 flex-col p-8">
        <p
          className="text-[11px] font-semibold uppercase tracking-[0.2em]"
          style={{ color: "var(--ms-brand-secondary)" }}
        >
          {PRODUCT_BRAND.displayName}
        </p>
        <h1 className="mt-2 text-2xl font-semibold">{title}</h1>
        <p className="mt-3 max-w-lg text-sm" style={{ color: "var(--ms-text-muted)" }}>
          Раздел зарезервирован для Product Alpha. Контент появится в следующих фазах. Backend не
          подключён.
        </p>
        <Link
          href="/workspace"
          className="mt-6 inline-flex w-fit rounded-md px-4 py-2 text-sm font-semibold"
          style={{
            background: "var(--ms-brand-primary)",
            color: "var(--ms-text-primary)",
          }}
        >
          Вернуться в Workspace
        </Link>
      </main>
    </div>
  );
}
