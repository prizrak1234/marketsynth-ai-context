"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { CommercialButton } from "@/components/commercial/commercial-button";
import { CommercialCard } from "@/components/commercial/commercial-card";
import { CommercialPageHeader } from "@/components/commercial/commercial-page-header";
import { CommercialStatus } from "@/components/commercial/commercial-status";
import { ContentDirectorTextPanel } from "@/components/content-director/content-director-text-panel";
import { VisualDirectorPanel } from "@/components/content-director/visual-director-panel";
import {
  listContentDirectorRequests,
  type ContentDirectorRequest,
} from "@/lib/api/endpoints/content-director";
import {
  listVisualDirectorRequests,
  type VisualDirectorRequest,
} from "@/lib/api/endpoints/visual-director";
import { useLocale } from "@/lib/i18n";

type Props = {
  projectId: string;
  projectName?: string | null;
  projectStatus?: string | null;
};

type Mode = "home" | "text" | "image";

type MaterialRow = {
  id: string;
  title: string;
  kind: "text" | "image";
  status: string;
  version: number;
  updatedAt: string;
};

function materialStatus(
  row: ContentDirectorRequest | VisualDirectorRequest,
  t: (key: string) => string,
): string {
  if (row.approved_asset_id) return t("contentDirector.materialStatus.approved");
  if (row.current_run_id) return t("contentDirector.materialStatus.inProgress");
  return t("contentDirector.materialStatus.draft");
}

export function ContentDirectorPanel({
  projectId,
  projectName,
  projectStatus,
}: Props) {
  const { t } = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const modeParam = searchParams.get("mode") || searchParams.get("type");
  const mode: Mode =
    modeParam === "text" || modeParam === "image" ? modeParam : "home";

  const [materials, setMaterials] = useState<MaterialRow[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  const projectHref = `/workspace?project=${encodeURIComponent(projectId)}`;

  const setMode = useCallback(
    (next: Mode) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set("project", projectId);
      params.set("view", "content_director");
      if (next === "home") {
        params.delete("mode");
        params.delete("type");
      } else {
        params.set("mode", next);
        params.delete("type");
      }
      router.replace(`${pathname}?${params.toString()}`);
    },
    [pathname, projectId, router, searchParams],
  );

  const reloadMaterials = useCallback(async () => {
    setLoadError(null);
    try {
      const [textRows, imageRows] = await Promise.all([
        listContentDirectorRequests(projectId).catch(() => [] as ContentDirectorRequest[]),
        listVisualDirectorRequests(projectId).catch(() => [] as VisualDirectorRequest[]),
      ]);
      const rows: MaterialRow[] = [
        ...textRows.map((r) => ({
          id: r.id,
          title: r.title,
          kind: "text" as const,
          status: materialStatus(r, t),
          version: r.version,
          updatedAt: r.updated_at,
        })),
        ...imageRows.map((r) => ({
          id: r.id,
          title: r.title,
          kind: "image" as const,
          status: materialStatus(r, t),
          version: r.version,
          updatedAt: r.updated_at,
        })),
      ];
      rows.sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : -1));
      setMaterials(rows.slice(0, 12));
    } catch {
      setLoadError(t("contentDirector.loadError"));
    }
  }, [projectId, t]);

  useEffect(() => {
    void reloadMaterials();
  }, [reloadMaterials]);

  const emptyHint = useMemo(() => t("contentDirector.emptyMaterials"), [t]);
  const displayName =
    projectName?.trim() || t("contentDirector.projectContext.unnamed");
  const displayStatus =
    projectStatus?.trim() || t("contentDirector.projectContext.statusUnknown");

  return (
    <div className="space-y-6" data-testid="content-director-panel">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <CommercialButton
          href={projectHref}
          variant="secondary"
          testId="content-director-back-to-project"
        >
          {t("contentDirector.backToProject")}
        </CommercialButton>
      </div>

      <CommercialCard padding="md" testId="content-director-project-context">
        <p className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--ms-text-muted)" }}>
          {t("contentDirector.projectContext.eyebrow")}
        </p>
        <p className="mt-1 text-base font-semibold" style={{ color: "var(--ms-text-primary)" }}>
          {displayName}
        </p>
        <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-3">
          <div>
            <dt style={{ color: "var(--ms-text-muted)" }}>
              {t("contentDirector.projectContext.status")}
            </dt>
            <dd data-testid="content-director-project-status">{displayStatus}</dd>
          </div>
          <div>
            <dt style={{ color: "var(--ms-text-muted)" }}>
              {t("contentDirector.projectContext.strategy")}
            </dt>
            <dd data-testid="content-director-strategy-status">
              {t("contentDirector.projectContext.strategyNotPrepared")}
            </dd>
          </div>
          <div>
            <dt style={{ color: "var(--ms-text-muted)" }}>
              {t("contentDirector.projectContext.launch")}
            </dt>
            <dd data-testid="content-director-launch-status">
              {t("contentDirector.projectContext.launchNotPrepared")}
            </dd>
          </div>
        </dl>
      </CommercialCard>

      <CommercialPageHeader
        title={t("contentDirector.title")}
        description={t("contentDirector.subtitle")}
        testId="content-director-header"
      />

      <div className="flex flex-wrap gap-2" data-testid="content-director-mode-switch">
        <CommercialButton
          variant={mode === "home" ? "primary" : "secondary"}
          onClick={() => setMode("home")}
          testId="content-director-mode-home"
        >
          {t("contentDirector.modeHome")}
        </CommercialButton>
        <CommercialButton
          variant={mode === "text" ? "primary" : "secondary"}
          onClick={() => setMode("text")}
          testId="content-director-mode-text"
        >
          {t("contentDirector.modeText")}
        </CommercialButton>
        <CommercialButton
          variant={mode === "image" ? "primary" : "secondary"}
          onClick={() => setMode("image")}
          testId="content-director-mode-image"
        >
          {t("contentDirector.modeImage")}
        </CommercialButton>
      </div>

      {mode === "home" ? (
        <div className="space-y-6" data-testid="content-director-home">
          <p className="text-sm" style={{ color: "var(--ms-text-secondary)" }}>
            {t("contentDirector.providerHonesty")}
          </p>
          <div className="flex flex-wrap gap-3">
            <CommercialButton
              onClick={() => setMode("text")}
              testId="content-director-create-text"
            >
              {t("contentDirector.createText")}
            </CommercialButton>
            <CommercialButton
              onClick={() => setMode("image")}
              testId="content-director-create-image"
            >
              {t("contentDirector.createImage")}
            </CommercialButton>
          </div>

          <CommercialCard padding="md" testId="content-director-materials">
            <h2 className="mb-3 text-lg font-semibold">
              {t("contentDirector.recentMaterials")}
            </h2>
            {loadError ? (
              <p className="text-sm" style={{ color: "var(--ms-danger, #b42318)" }}>
                {loadError}
              </p>
            ) : null}
            {materials.length === 0 && !loadError ? (
              <p className="text-sm" style={{ color: "var(--ms-text-muted)" }}>
                {emptyHint}
              </p>
            ) : (
              <ul className="space-y-2">
                {materials.map((row) => (
                  <li key={`${row.kind}-${row.id}`}>
                    <button
                      type="button"
                      className="flex w-full items-center justify-between gap-3 rounded-md border px-3 py-2 text-left text-sm"
                      style={{ borderColor: "var(--ms-border-default)" }}
                      data-testid={`content-director-material-${row.kind}`}
                      onClick={() => setMode(row.kind)}
                    >
                      <span className="min-w-0 flex-1 truncate font-medium">{row.title}</span>
                      <CommercialStatus tone="neutral">
                        {row.kind === "text"
                          ? t("contentDirector.kindText")
                          : t("contentDirector.kindImage")}
                      </CommercialStatus>
                      <span style={{ color: "var(--ms-text-muted)" }}>{row.status}</span>
                      <span style={{ color: "var(--ms-text-muted)" }}>v{row.version}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </CommercialCard>
        </div>
      ) : null}

      {mode === "text" ? <ContentDirectorTextPanel projectId={projectId} /> : null}
      {mode === "image" ? <VisualDirectorPanel projectId={projectId} /> : null}
    </div>
  );
}
