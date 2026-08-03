"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  SectionEmpty,
  SectionError,
  SectionLoading,
  WorkspaceSectionShell,
} from "@/components/workspace/section-shell";
import {
  loadWorkspaceTaskIndex,
  type WorkspaceTaskIndexResult,
} from "@/lib/integration/workspace-task-index-adapter";
import type { WorkspaceTaskItem } from "@/lib/home/workspace-task-types";
import {
  formatDateTime,
  labelTaskStatus,
  labelTaskType,
  useLocale,
} from "@/lib/i18n";
import { useAuth } from "@/lib/auth/auth-context";

const STATUS_VALUES = [
  "routed",
  "ready_for_draft",
  "needs_clarification",
  "draft",
  "submitted",
  "completed",
] as const;

const TYPE_VALUES = [
  "content",
  "content_plan",
  "social_media",
  "image_generation",
  "telegram_bot",
  "idea_validation",
  "website",
  "market_research",
  "competitor_analysis",
  "marketing_strategy",
  "youtube",
  "saas",
  "automation",
] as const;

export function WorkspaceTasksPageView() {
  const { t, locale, prefs } = useLocale();
  const { user } = useAuth();
  const showDiag =
    (user?.role === "owner" || user?.role === "admin") &&
    process.env.NODE_ENV !== "production";

  const [result, setResult] = useState<WorkspaceTaskIndexResult | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");

  const refresh = useCallback(async () => {
    setResult(null);
    setResult(await loadWorkspaceTaskIndex());
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const filtered = useMemo(() => {
    const items = result?.items ?? [];
    return items.filter((task) => {
      if (statusFilter !== "all" && task.status !== statusFilter) return false;
      if (typeFilter !== "all" && task.route_category !== typeFilter) return false;
      return true;
    });
  }, [result, statusFilter, typeFilter]);

  const emptyMessage =
    result?.state === "empty"
      ? t("task.empty")
      : result?.message || t("task.empty");

  return (
    <WorkspaceSectionShell
      title={t("task.title")}
      description={t("task.description")}
      testId="workspace-tasks-page"
      actions={
        <Link
          href="/workspace"
          className="rounded-md px-3 py-2 text-sm font-semibold"
          style={{
            background: "var(--ms-brand-primary)",
            color: "var(--ms-text-on-brand, #fff)",
          }}
          data-testid="tasks-new-link"
        >
          {t("task.newOnHome")}
        </Link>
      }
    >
      {!result ? <SectionLoading /> : null}

      {result ? (
        <div className="mb-4 flex flex-wrap gap-3 text-sm">
          <label>
            {t("task.filterStatus")}{" "}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="ml-1 rounded border px-2 py-1"
              style={{
                background: "var(--ms-bg-surface)",
                borderColor: "var(--ms-border-default)",
              }}
              data-testid="tasks-filter-status"
            >
              <option value="all">{t("common.all")}</option>
              {STATUS_VALUES.map((s) => (
                <option key={s} value={s}>
                  {labelTaskStatus(locale, s)}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t("task.filterType")}{" "}
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="ml-1 rounded border px-2 py-1"
              style={{
                background: "var(--ms-bg-surface)",
                borderColor: "var(--ms-border-default)",
              }}
              data-testid="tasks-filter-type"
            >
              <option value="all">{t("common.all")}</option>
              {TYPE_VALUES.map((type) => (
                <option key={type} value={type}>
                  {labelTaskType(locale, type)}
                </option>
              ))}
            </select>
          </label>
        </div>
      ) : null}

      {result?.state === "error" ? (
        <SectionError message={result.message || t("section.unavailable")} onRetry={() => void refresh()} />
      ) : null}
      {result?.state === "mock_notice" || result?.state === "empty" ? (
        <SectionEmpty message={emptyMessage} testId="tasks-empty" />
      ) : null}
      {result?.state === "success" && filtered.length === 0 ? (
        <SectionEmpty message={t("task.emptyFilters")} />
      ) : null}

      {result?.state === "success" ? (
        <ul className="space-y-3" data-testid="tasks-list">
          {filtered.map((task: WorkspaceTaskItem) => (
            <li
              key={task.id}
              className="rounded-lg border px-4 py-3"
              style={{
                borderColor: "var(--ms-border-default)",
                background: "var(--ms-bg-surface)",
              }}
              data-testid="task-card"
              data-source-domain={task.source_domain}
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="font-medium">{task.title}</h2>
                <span className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                  {formatDateTime(locale, task.created_at, prefs)}
                </span>
              </div>
              <p className="mt-1 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
                {task.request_text}
              </p>
              <dl
                className="mt-2 grid gap-1 text-xs sm:grid-cols-2"
                style={{ color: "var(--ms-text-muted)" }}
              >
                <div>
                  {t("common.type")}: {labelTaskType(locale, task.route_category)}
                </div>
                <div>
                  {t("common.status")}: {labelTaskStatus(locale, task.status)}
                </div>
                <div>
                  {t("common.project")}: {task.project_id || "—"}
                </div>
                <div data-testid="task-specialist">
                  {t("home.specialistLabel", {
                    role: task.specialist_role
                      ? t(`specialist.${task.specialist_role}`)
                      : "—",
                  })}
                </div>
                {task.skill_code ? (
                  <div data-testid="task-skill">
                    {t("task.skill")}: {task.skill_code}
                    {task.skill_version ? ` v${task.skill_version}` : ""}
                    {task.execution_readiness
                      ? ` · ${t(`task.readiness.${task.execution_readiness}`)}`
                      : ""}
                  </div>
                ) : null}
                {task.missing_inputs && task.missing_inputs.length > 0 ? (
                  <div data-testid="task-missing-inputs">
                    {t("task.missingInputs")}: {task.missing_inputs.join(", ")}
                  </div>
                ) : null}
                {typeof task.approved_knowledge_count === "number" &&
                task.approved_knowledge_count > 0 ? (
                  <div data-testid="task-knowledge-count">
                    {t("task.knowledgeReady")}: {task.approved_knowledge_count}
                    {task.knowledge_snapshot_hash
                      ? ` · ${task.knowledge_snapshot_hash.slice(0, 18)}…`
                      : ""}
                  </div>
                ) : null}
                <div>
                  {t("common.next")}: {task.next_action}
                </div>
              </dl>
              {task.next_href ? (
                <Link href={task.next_href} className="mt-2 inline-block text-sm underline">
                  {task.next_action}
                </Link>
              ) : null}
              {showDiag ? (
                <details className="mt-2 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                  <summary>diagnostics</summary>
                  <p>
                    source_domain={task.source_domain} · authority={task.authority} · raw=
                    {task.status}/{task.route_category}
                  </p>
                </details>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}

      {result?.persistenceNote ? (
        <p
          className="mt-4 text-xs"
          style={{ color: "var(--ms-text-muted)" }}
          data-testid="tasks-persistence-note"
        >
          {t("task.persistenceNote")}
        </p>
      ) : null}
    </WorkspaceSectionShell>
  );
}
