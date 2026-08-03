"use client";

import { useRouter } from "next/navigation";

import { ContentFactoryPanel } from "@/components/content-factory/content-factory-panel";
import { WorkspaceNav } from "@/components/workspace/workspace-nav";
import { useRecoveryPreviewAccess } from "@/lib/home/recovery-preview";
import { useLocale } from "@/lib/i18n";

export function RecoveryPreviewR3View() {
  const { t } = useLocale();
  const router = useRouter();
  const { allowed, loading } = useRecoveryPreviewAccess();

  if (loading || !allowed) {
    return (
      <div
        className="flex min-h-[40vh] items-center justify-center text-sm"
        style={{ color: "var(--ms-text-secondary)" }}
        data-testid="recovery-preview-r3-guard"
      >
        {t("common.loading")}
      </div>
    );
  }

  return (
    <div
      className="flex min-h-screen flex-col md:flex-row"
      style={{ background: "var(--ms-bg-canvas)", color: "var(--ms-text-primary)" }}
      data-testid="recovery-preview-r3"
      data-home-mode="recovery-preview"
    >
      <WorkspaceNav />
      <div className="mx-auto w-full max-w-[1360px] flex-1 space-y-5 px-4 py-8 sm:px-8">
        <div
          className="rounded-xl border px-4 py-3 text-sm leading-relaxed"
          style={{
            borderColor: "var(--ms-border-default)",
            background: "var(--ms-bg-surface)",
          }}
          data-testid="recovery-preview-r3-banner"
        >
          <p className="font-semibold">{t("recovery.preview.r3BannerTitle")}</p>
          <p className="mt-1" style={{ color: "var(--ms-text-secondary)" }}>
            {t("recovery.preview.r3BannerBody")}
          </p>
          <p
            className="mt-2 text-xs"
            style={{ color: "var(--ms-text-muted)" }}
            data-testid="recovery-preview-r3-seed-hint"
          >
            {t("recovery.preview.r3SeedHint")}
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-semibold">{t("contentFactory.previewTitle")}</h1>
            <p className="text-sm text-muted-foreground">{t("contentFactory.previewSubtitle")}</p>
          </div>
          <button
            type="button"
            className="rounded-md border px-3 py-2 text-sm font-semibold"
            style={{ borderColor: "var(--ms-border-default)" }}
            onClick={() => router.push("/workspace")}
            data-testid="recovery-preview-r3-back"
          >
            {t("recovery.preview.backToDeveloper")}
          </button>
        </div>

        <ContentFactoryPanel allowDemoMaterials />
      </div>
    </div>
  );
}
