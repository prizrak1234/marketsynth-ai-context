"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  SectionEmpty,
  SectionError,
  SectionLoading,
  WorkspaceSectionShell,
} from "@/components/workspace/section-shell";
import {
  loadInvestigationIndex,
  type InvestigationIndexResult,
} from "@/lib/integration/investigation-index-adapter";
import { formatDateTime, labelLifecycle, useLocale } from "@/lib/i18n";
import { useCommercialPathGuard } from "@/lib/home/developer-mode";

export function InvestigationsPageView() {
  const { t, locale, prefs } = useLocale();
  const allowed = useCommercialPathGuard();
  const [result, setResult] = useState<InvestigationIndexResult | null>(null);
  const refresh = useCallback(async () => {
    setResult(null);
    setResult(await loadInvestigationIndex());
  }, []);
  useEffect(() => {
    void refresh();
  }, [refresh]);

  if (!allowed) {
    return null;
  }

  return (
    <WorkspaceSectionShell
      title={t("investigations.title")}
      description={t("investigations.description")}
      testId="workspace-investigations-page"
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
      {result?.state === "empty" || result?.state === "mock_notice" ? (
        <SectionEmpty
          message={
            result.state === "mock_notice"
              ? t("investigations.mockNotice")
              : t("investigations.empty")
          }
          testId="investigations-empty"
        />
      ) : null}
      {result?.state === "success" ? (
        <ul className="space-y-3" data-testid="investigations-list">
          {result.items.map((item) => (
            <li
              key={item.id}
              className="rounded-lg border px-4 py-3 text-sm"
              style={{
                borderColor: "var(--ms-border-default)",
                background: "var(--ms-bg-surface)",
              }}
              data-testid="investigation-card"
            >
              <div className="font-medium">{item.projectName}</div>
              <div style={{ color: "var(--ms-text-muted)" }}>
                {labelLifecycle(locale, item.status)}
                {item.currentStage ? ` · ${item.currentStage}` : ""}
                {item.readiness ? ` · ${labelLifecycle(locale, item.readiness)}` : ""}
              </div>
              <div className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                {formatDateTime(locale, item.updatedAt, prefs)}
              </div>
              <Link href={item.href} className="mt-2 inline-block underline">
                {t("investigations.open")}
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </WorkspaceSectionShell>
  );
}
