"use client";

import Link from "next/link";
import { WorkspaceNav } from "@/components/workspace/workspace-nav";
import { useLocale } from "@/lib/i18n";

/** Connected publication channels — no credential fields on empty state. */
export function ChannelsPageView() {
  const { t } = useLocale();

  return (
    <div
      className="flex min-h-screen flex-col md:flex-row"
      style={{ background: "var(--ms-bg-canvas)", color: "var(--ms-text-primary)" }}
      data-testid="workspace-channels-page"
    >
      <WorkspaceNav />
      <main className="mx-auto w-full max-w-2xl flex-1 space-y-4 px-4 py-8 sm:px-8">
        <h1 className="text-2xl font-semibold">{t("nav.channels")}</h1>
        <div
          className="rounded-xl border px-5 py-8 text-center"
          style={{
            borderColor: "var(--ms-border-default)",
            background: "var(--ms-bg-surface)",
          }}
          data-testid="channels-empty"
        >
          <p className="font-medium">{t("empty.channelsTitle")}</p>
          <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--ms-text-secondary)" }}>
            {t("empty.channelsBody")}
          </p>
          <Link
            href="/workspace/settings"
            className="mt-4 inline-block rounded-md px-4 py-2 text-sm font-semibold"
            style={{
              background: "var(--ms-brand-primary)",
              color: "var(--ms-text-on-brand, #fff)",
            }}
            data-testid="channels-settings-cta"
          >
            {t("empty.channelsCta")}
          </Link>
        </div>
      </main>
    </div>
  );
}
