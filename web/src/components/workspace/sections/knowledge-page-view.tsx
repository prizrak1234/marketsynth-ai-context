"use client";

import Link from "next/link";
import { SectionEmpty, WorkspaceSectionShell } from "@/components/workspace/section-shell";
import { useLocale } from "@/lib/i18n";

export function KnowledgePageView() {
  const { t } = useLocale();
  return (
    <WorkspaceSectionShell
      title={t("knowledge.title")}
      description={t("knowledge.description")}
      testId="workspace-knowledge-page"
    >
      <div className="space-y-4">
        <SectionEmpty message={t("knowledge.empty")} testId="knowledge-empty" />
        <p className="text-sm" style={{ color: "var(--ms-text-secondary)" }}>
          <Link
            href="/workspace/knowledge/manage"
            className="underline"
            data-testid="knowledge-mgmt-link"
          >
            {t("knowledge.manageLink")}
          </Link>
        </p>
      </div>
    </WorkspaceSectionShell>
  );
}
