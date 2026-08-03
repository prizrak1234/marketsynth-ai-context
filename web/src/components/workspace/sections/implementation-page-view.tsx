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
  loadImplementationIndex,
  type ImplementationIndexResult,
} from "@/lib/integration/implementation-index-adapter";
import { labelLifecycle, useLocale } from "@/lib/i18n";

export function ImplementationPageView() {
  const { t, locale } = useLocale();
  const [result, setResult] = useState<ImplementationIndexResult | null>(null);
  const refresh = useCallback(async () => {
    setResult(null);
    setResult(await loadImplementationIndex());
  }, []);
  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <WorkspaceSectionShell
      title={t("implementation.title")}
      description={t("implementation.description")}
      testId="workspace-implementation-page"
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
          message={t("implementation.empty")}
          testId="implementation-empty"
        />
      ) : null}
      {result?.state === "success" ? (
        <ul className="space-y-3" data-testid="implementation-list">
          {result.items.map((p) => (
            <li
              key={p.id}
              className="rounded-lg border px-4 py-3 text-sm"
              style={{
                borderColor: "var(--ms-border-default)",
                background: "var(--ms-bg-surface)",
              }}
              data-testid="implementation-card"
            >
              <div className="font-medium">
                {p.projectName} · {t("common.version")} {p.planVersion}
              </div>
              <div style={{ color: "var(--ms-text-muted)" }}>
                {labelLifecycle(locale, p.lifecycleStatus)} · {t("common.readiness")}:{" "}
                {labelLifecycle(locale, p.readiness)}
              </div>
              <Link href={p.href} className="mt-2 inline-block underline">
                {t("implementation.open")}
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </WorkspaceSectionShell>
  );
}
