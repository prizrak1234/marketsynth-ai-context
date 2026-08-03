"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CommercialButton } from "@/components/commercial/commercial-button";
import { CommercialCard } from "@/components/commercial/commercial-card";
import { CommercialStatus } from "@/components/commercial/commercial-status";
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
  /**
   * `section` — compact Content capability inside Project Command Center (default).
   * Do not use as the root project screen.
   */
  variant?: "section";
};

function contentDirectorHref(projectId: string, mode?: "text" | "image") {
  const params = new URLSearchParams({
    project: projectId,
    view: "content_director",
  });
  if (mode) params.set("mode", mode);
  return `/workspace?${params.toString()}`;
}

/** Content capability section inside Project Command Center — not a root product screen. */
export function ProjectContentHub({
  projectId,
  projectName,
  projectStatus,
  variant = "section",
}: Props) {
  const { t } = useLocale();
  const router = useRouter();
  const [materialCount, setMaterialCount] = useState(0);
  const [approvedCount, setApprovedCount] = useState(0);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const openHref = contentDirectorHref(projectId);

  const reload = useCallback(async () => {
    try {
      const [textRows, imageRows] = await Promise.all([
        listContentDirectorRequests(projectId).catch(() => [] as ContentDirectorRequest[]),
        listVisualDirectorRequests(projectId).catch(() => [] as VisualDirectorRequest[]),
      ]);
      const all = [...textRows, ...imageRows];
      setMaterialCount(all.length);
      setApprovedCount(all.filter((r) => r.approved_asset_id).length);
      const sorted = [...all].sort((a, b) =>
        a.updated_at < b.updated_at ? 1 : -1,
      );
      setLastUpdated(sorted[0]?.updated_at ?? null);
    } catch {
      setMaterialCount(0);
      setApprovedCount(0);
      setLastUpdated(null);
    }
  }, [projectId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return (
    <section
      className="space-y-3"
      data-testid="project-content-hub"
      data-variant={variant}
    >
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2
            className="text-base font-semibold"
            style={{ color: "var(--ms-text-primary)" }}
          >
            {t("projectContentHub.title")}
          </h2>
          <p className="text-sm" style={{ color: "var(--ms-text-secondary)" }}>
            {t("projectContentHub.sectionSubtitle")}
          </p>
          {projectName ? (
            <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
              {t("projectContentHub.projectLabel")}: {projectName}
              {projectStatus ? (
                <>
                  {" · "}
                  <span data-testid="project-content-hub-status">{projectStatus}</span>
                </>
              ) : null}
            </p>
          ) : null}
        </div>
        <CommercialButton
          href={openHref}
          onClick={(e) => {
            e.preventDefault();
            router.push(openHref);
          }}
          testId="project-content-hub-open"
        >
          {t("projectContentHub.openContentDirector")}
        </CommercialButton>
      </div>

      <CommercialCard padding="sm" testId="project-content-hub-summary">
        <ul
          className="flex flex-wrap gap-x-4 gap-y-1 text-sm"
          data-testid="project-content-hub-lanes"
        >
          <li data-testid="project-content-hub-text">
            {t("projectContentHub.text")}
          </li>
          <li data-testid="project-content-hub-image">
            {t("projectContentHub.images")}
          </li>
          <li data-testid="project-content-hub-video" className="flex items-center gap-2">
            {t("projectContentHub.video")}
            <CommercialStatus tone="neutral">{t("projectContentHub.videoSoon")}</CommercialStatus>
          </li>
        </ul>
        <div className="mt-3 flex flex-wrap gap-4 text-sm" style={{ color: "var(--ms-text-muted)" }}>
          <span data-testid="project-content-hub-material-count">
            {t("projectContentHub.materialCount")}: <strong>{materialCount}</strong>
          </span>
          <span>
            {t("projectContentHub.approvedCount")}: <strong>{approvedCount}</strong>
          </span>
          <span>
            {t("projectContentHub.lastChange")}:{" "}
            {lastUpdated
              ? new Date(lastUpdated).toLocaleString()
              : t("projectContentHub.never")}
          </span>
        </div>
      </CommercialCard>
    </section>
  );
}
