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
  loadStrategyIndex,
  type StrategyIndexResult,
} from "@/lib/integration/strategy-index-adapter";
import {
  formatDateTime,
  labelLifecycle,
  labelVerdictType,
  useLocale,
} from "@/lib/i18n";

export function StrategiesPageView() {
  const { t, locale, prefs } = useLocale();
  const [result, setResult] = useState<StrategyIndexResult | null>(null);
  const refresh = useCallback(async () => {
    setResult(null);
    setResult(await loadStrategyIndex());
  }, []);
  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <WorkspaceSectionShell
      title={t("strategies.title")}
      description={t("strategies.description")}
      testId="workspace-strategies-page"
    >
      {!result ? <SectionLoading /> : null}
      {result?.state === "error" || result?.state === "unauthorized" ? (
        <SectionError
          message={result.message || t("section.unavailable")}
          onRetry={() => void refresh()}
        />
      ) : null}
      {result?.state === "empty" || result?.state === "mock_notice" ? (
        <SectionEmpty
          message={
            result.state === "mock_notice"
              ? t("strategies.mockNotice")
              : t("strategies.empty")
          }
          testId="strategies-empty"
        />
      ) : null}
      {result?.state === "success" ? (
        <ul className="space-y-3" data-testid="strategies-list">
          {result.items.map((s) => (
            <li
              key={s.id}
              className="rounded-lg border px-4 py-3 text-sm"
              style={{
                borderColor: "var(--ms-border-default)",
                background: "var(--ms-bg-surface)",
              }}
              data-testid="strategy-card"
            >
              <div className="font-medium">
                {s.projectName} · {t("common.version")} {s.strategyVersion}
              </div>
              <div style={{ color: "var(--ms-text-muted)" }}>
                {labelVerdictType(locale, s.verdictType)} ·{" "}
                {labelLifecycle(locale, s.lifecycleStatus)} · {t("common.readiness")}:{" "}
                {labelLifecycle(locale, s.readiness)}
              </div>
              <div className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                {formatDateTime(locale, s.updatedAt, prefs)}
              </div>
              <Link href={s.href} className="mt-2 inline-block underline">
                {t("strategies.open")}
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </WorkspaceSectionShell>
  );
}
