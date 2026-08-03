"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  SectionEmpty,
  SectionError,
  SectionLoading,
  WorkspaceSectionShell,
} from "@/components/workspace/section-shell";
import { loadVerdictIndex, type VerdictIndexResult } from "@/lib/integration/verdict-index-adapter";
import {
  formatDateTime,
  labelLifecycle,
  labelVerdictType,
  useLocale,
} from "@/lib/i18n";

export function VerdictsPageView() {
  const { t, locale, prefs } = useLocale();
  const [result, setResult] = useState<VerdictIndexResult | null>(null);
  const [typeFilter, setTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  const refresh = useCallback(async () => {
    setResult(null);
    setResult(await loadVerdictIndex());
  }, []);
  useEffect(() => {
    void refresh();
  }, [refresh]);

  const items = useMemo(() => {
    return (result?.items || []).filter((v) => {
      if (typeFilter !== "all" && v.verdictType !== typeFilter) return false;
      if (statusFilter !== "all" && v.lifecycleStatus !== statusFilter) return false;
      return true;
    });
  }, [result, typeFilter, statusFilter]);

  return (
    <WorkspaceSectionShell
      title={t("verdicts.title")}
      description={t("verdicts.description")}
      testId="workspace-verdicts-page"
    >
      {!result ? <SectionLoading /> : null}
      {result ? (
        <div className="mb-4 flex flex-wrap gap-3 text-sm">
          <label>
            {t("common.type")}{" "}
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="ml-1 rounded border px-2 py-1"
              style={{
                background: "var(--ms-bg-surface)",
                borderColor: "var(--ms-border-default)",
              }}
            >
              <option value="all">{t("common.all")}</option>
              {(["go", "conditional_go", "no_go", "insufficient_data"] as const).map(
                (type) => (
                  <option key={type} value={type}>
                    {labelVerdictType(locale, type)}
                  </option>
                ),
              )}
            </select>
          </label>
          <label>
            {t("common.status")}{" "}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="ml-1 rounded border px-2 py-1"
              style={{
                background: "var(--ms-bg-surface)",
                borderColor: "var(--ms-border-default)",
              }}
            >
              <option value="all">{t("common.all")}</option>
              {(["draft", "under_review", "approved", "rejected"] as const).map((s) => (
                <option key={s} value={s}>
                  {labelLifecycle(locale, s)}
                </option>
              ))}
            </select>
          </label>
        </div>
      ) : null}
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
        <SectionEmpty message={t("verdicts.empty")} testId="verdicts-empty" />
      ) : null}
      {result?.state === "success" ? (
        <ul className="space-y-3" data-testid="verdicts-list">
          {items.map((v) => (
            <li
              key={v.id}
              className="rounded-lg border px-4 py-3 text-sm"
              style={{
                borderColor: "var(--ms-border-default)",
                background: "var(--ms-bg-surface)",
              }}
              data-testid="verdict-card"
            >
              <div className="font-medium">
                {v.projectName} · {labelVerdictType(locale, v.verdictType)} ·{" "}
                {t("common.version")} {v.version}
              </div>
              <div style={{ color: "var(--ms-text-muted)" }}>
                {labelLifecycle(locale, v.lifecycleStatus)}
              </div>
              <div className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                {v.strategyEligible
                  ? t("verdicts.strategyEligible")
                  : t("verdicts.strategyNotEligible")}{" "}
                · {formatDateTime(locale, v.reviewDate, prefs)}
              </div>
              <Link href={v.href} className="mt-2 inline-block underline">
                {t("verdicts.open")}
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </WorkspaceSectionShell>
  );
}
