"use client";

import { useCallback, useEffect, useState } from "react";
import { AuthenticatedImage } from "@/components/workspace/home/authenticated-image";
import {
  SectionEmpty,
  SectionError,
  SectionLoading,
  WorkspaceSectionShell,
} from "@/components/workspace/section-shell";
import { loadAssetsIndex, type AssetIndexResult } from "@/lib/integration/assets-index-adapter";
import { labelLifecycle, useLocale } from "@/lib/i18n";

export function AssetsPageView() {
  const { t, locale } = useLocale();
  const [result, setResult] = useState<AssetIndexResult | null>(null);
  const refresh = useCallback(async () => {
    setResult(null);
    setResult(await loadAssetsIndex());
  }, []);
  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <WorkspaceSectionShell
      title={t("assets.title")}
      description={t("assets.description")}
      testId="workspace-assets-page"
    >
      {!result ? <SectionLoading /> : null}
      {result?.state === "error" || result?.state === "unauthorized" ? (
        <SectionError
          message={
            result.state === "unauthorized"
              ? t("section.unauthorized")
              : t("section.unavailable")
          }
          onRetry={() => void refresh()}
        />
      ) : null}
      {result?.state === "empty" ||
      result?.state === "mock_notice" ||
      result?.state === "unavailable" ? (
        <SectionEmpty
          message={`${t("empty.materialsTitle")}. ${t("empty.materialsBody")}`}
          testId="assets-empty"
        />
      ) : null}
      {result?.state === "success" ? (
        <ul className="space-y-3" data-testid="assets-list">
          {result.items.map((a) => {
            const isMock = a.generationMode === "mock";
            return (
              <li
                key={`${a.kind || "asset"}-${a.id}`}
                className="rounded-lg border px-4 py-3 text-sm"
                style={{
                  borderColor: "var(--ms-border-default)",
                  background: "var(--ms-bg-surface)",
                }}
                data-testid="asset-card"
                data-asset-kind={a.kind || "content"}
                data-generation-mode={a.generationMode || undefined}
              >
                {isMock ? (
                  <span
                    className="mb-2 inline-block rounded px-2 py-0.5 text-[11px] font-semibold"
                    style={{
                      background: "color-mix(in srgb, #b45309 28%, transparent)",
                      color: "#fbbf24",
                    }}
                    data-testid="asset-test-mode-badge"
                  >
                    {t("home.testModeBadge")}
                  </span>
                ) : null}
                {a.kind === "generated_visual" ? (
                  <div className="mb-2 max-w-xs overflow-hidden rounded-md">
                    <AuthenticatedImage
                      assetId={a.id}
                      alt={a.title}
                      className="h-auto w-full object-cover"
                    />
                  </div>
                ) : null}
                <div className="font-medium">{a.title}</div>
                <div style={{ color: "var(--ms-text-muted)" }}>
                  {a.projectName}
                  {a.provider ? ` · provider=${a.provider}` : ""}
                  {a.assetType ? ` · ${a.assetType}` : ""} ·{" "}
                  {labelLifecycle(locale, a.status)}
                </div>
                {!isMock && a.kind === "generated_visual" && a.href ? (
                  <a
                    href={a.href}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-1 inline-block text-xs underline"
                    style={{ color: "var(--ms-text-muted)" }}
                  >
                    {t("home.downloadImage")}
                  </a>
                ) : null}
                {isMock ? (
                  <p
                    className="mt-1 text-xs"
                    style={{ color: "var(--ms-text-muted)" }}
                  >
                    {t("home.mockDisclaimer")}
                  </p>
                ) : null}
              </li>
            );
          })}
        </ul>
      ) : null}
    </WorkspaceSectionShell>
  );
}
