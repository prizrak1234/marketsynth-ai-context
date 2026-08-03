"use client";

import { Suspense, use } from "react";
import { useSearchParams } from "next/navigation";
import { LegacyProjectPipelineGuard } from "@/components/routing/legacy-commercial-guard";
import { InvestigationWorkspaceView } from "@/components/investigation/investigation-workspace-view";

function InvestigationPageInner({ projectId }: { projectId: string }) {
  const searchParams = useSearchParams();
  const investigationId = searchParams.get("investigationId");
  return (
    <InvestigationWorkspaceView
      projectId={projectId}
      investigationId={investigationId}
    />
  );
}

export default function InvestigationPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  return (
    <Suspense
      fallback={
        <div
          className="flex min-h-screen items-center justify-center"
          style={{ background: "var(--ms-bg-canvas)", color: "var(--ms-text-muted)" }}
        >
          Загрузка investigation workspace…
        </div>
      }
    >
      <LegacyProjectPipelineGuard projectId={projectId}>
        <InvestigationPageInner projectId={projectId} />
      </LegacyProjectPipelineGuard>
    </Suspense>
  );
}
