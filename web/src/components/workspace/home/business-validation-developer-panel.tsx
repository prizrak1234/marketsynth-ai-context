"use client";

import { useState } from "react";

import type {
  BivInternalResearchDiagnostics,
  BusinessIdeaValidationOutput,
} from "@/lib/api/types/business-idea-validation";
import { isHomeDeveloperMode } from "@/lib/home/developer-mode";
import { useLocale } from "@/lib/i18n";

type Props = {
  result: BusinessIdeaValidationOutput;
};

/** Debug-only engine diagnostics — never shown in commercial flow by default. */
export function BusinessValidationDeveloperPanel({ result }: Props) {
  const { t } = useLocale();
  const [open, setOpen] = useState(false);
  const diag: BivInternalResearchDiagnostics | null | undefined =
    result.internal_diagnostics;

  if (!diag || !isHomeDeveloperMode()) {
    return null;
  }

  return (
    <section
      className="rounded-xl border"
      style={{ borderColor: "var(--ms-border-subtle)" }}
      data-testid="biv-developer-panel"
    >
      <button
        type="button"
        className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium"
        onClick={() => setOpen((v) => !v)}
        data-testid="biv-developer-toggle"
      >
        <span>{t("agency.biv.commercial.developerReport")}</span>
        <span style={{ color: "var(--ms-text-muted)" }}>{open ? "−" : "+"}</span>
      </button>
      {open ? (
        <div
          className="space-y-4 border-t px-4 py-3 text-xs"
          style={{ borderColor: "var(--ms-border-subtle)", color: "var(--ms-text-secondary)" }}
        >
          <div>
            <p className="font-semibold">{t("agency.biv.commercial.engineStats")}</p>
            <p>
              MCP search: {diag.mcp_search_calls} · fetch: {diag.mcp_fetch_calls}
            </p>
            {diag.research_stop_reason_code ? (
              <p>
                {t("agency.biv.commercial.stopCode")}: {diag.research_stop_reason_code}
              </p>
            ) : null}
            {diag.pipeline_phases_completed?.length ? (
              <p>
                {t("agency.biv.commercial.phases")}: {diag.pipeline_phases_completed.join(", ")}
              </p>
            ) : null}
            {diag.pipeline_metrics ? (
              <div data-testid="biv-pipeline-metrics">
                <p className="font-semibold">Pipeline metrics</p>
                <p>
                  Search: {diag.pipeline_metrics.discovery.search_success_count}/
                  {diag.pipeline_metrics.discovery.search_requests} · fetch success:{" "}
                  {Math.round((diag.pipeline_metrics.fetch.fetch_success_rate || 0) * 100)}% (
                  {diag.pipeline_metrics.fetch.fetch_success_count}/
                  {diag.pipeline_metrics.fetch.attempted_eligible_urls || diag.pipeline_metrics.fetch.eligible_urls})
                </p>
                {Object.keys(diag.pipeline_metrics.fetch.failures_by_outcome || {}).length ? (
                  <p>
                    Fetch outcomes:{" "}
                    {Object.entries(diag.pipeline_metrics.fetch.failures_by_outcome)
                      .map(([k, v]) => `${k}=${v}`)
                      .join(", ")}
                  </p>
                ) : null}
                {diag.pipeline_metrics.fetch.provider_circuit_state ? (
                  <p>
                    Circuits:{" "}
                    {Object.entries(diag.pipeline_metrics.fetch.provider_circuit_state)
                      .map(([k, v]) => `${k}=${v}`)
                      .join(", ")}
                  </p>
                ) : null}
              </div>
            ) : null}
            {diag.pipeline_failure ? (
              <p data-testid="biv-pipeline-failure">
                Failure: {diag.pipeline_failure.failure_code} ({diag.pipeline_failure.failure_stage})
              </p>
            ) : null}
          </div>
          {diag.raw_research_gaps?.length ? (
            <div data-testid="biv-dev-gaps">
              <p className="font-semibold">{t("agency.biv.commercial.rawGaps")}</p>
              <ul className="mt-1 list-disc pl-4">
                {diag.raw_research_gaps.map((g) => (
                  <li key={g}>{g}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {diag.raw_limitations?.length ? (
            <div>
              <p className="font-semibold">{t("agency.biv.commercial.rawLimitations")}</p>
              <ul className="mt-1 list-disc pl-4">
                {diag.raw_limitations.map((l) => (
                  <li key={l}>{l}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {diag.search_queries?.length ? (
            <div data-testid="biv-dev-queries">
              <p className="font-semibold">{t("agency.biv.commercial.searchQueries")}</p>
              <ul className="mt-2 space-y-2">
                {diag.search_queries.map((q, idx) => (
                  <li key={`${q.category}-${idx}`} className="rounded border px-2 py-1">
                    <span className="opacity-70">
                      [{q.pipeline_phase ?? "direct"}] {q.category}
                    </span>
                    <p className="mt-1">{q.query}</p>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
