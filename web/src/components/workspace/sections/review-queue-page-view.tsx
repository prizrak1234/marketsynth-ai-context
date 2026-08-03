"use client";

import Link from "next/link";
import { WorkspaceNav } from "@/components/workspace/workspace-nav";
import { useLocale } from "@/lib/i18n";

/** Materials awaiting owner approval — customer-facing review queue shell. */
export function ReviewQueuePageView() {
  const { t } = useLocale();

  return (
    <div
      className="flex min-h-screen flex-col md:flex-row"
      style={{ background: "var(--ms-bg-canvas)", color: "var(--ms-text-primary)" }}
      data-testid="workspace-review-page"
    >
      <WorkspaceNav />
      <main className="mx-auto w-full max-w-2xl flex-1 space-y-4 px-4 py-8 sm:px-8">
        <h1 className="text-2xl font-semibold">{t("nav.reviewQueue")}</h1>
        <div
          className="rounded-xl border px-5 py-8 text-center"
          style={{
            borderColor: "var(--ms-border-default)",
            background: "var(--ms-bg-surface)",
          }}
          data-testid="review-queue-empty"
        >
          <p className="font-medium">{t("empty.reviewTitle")}</p>
          <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--ms-text-secondary)" }}>
            {t("empty.reviewBody")}
          </p>
        </div>
        <Link
          href="/workspace"
          className="inline-block text-sm underline"
          style={{ color: "var(--ms-text-muted)" }}
        >
          {t("common.backHome")}
        </Link>
      </main>
    </div>
  );
}
