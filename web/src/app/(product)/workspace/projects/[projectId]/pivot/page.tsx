"use client";

import { Suspense, use } from "react";
import { LegacyProjectPipelineGuard } from "@/components/routing/legacy-commercial-guard";
import { PivotWorkspaceView } from "@/components/strategy/pivot-workspace-view";

export default function PivotPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  return (
    <LegacyProjectPipelineGuard projectId={projectId}>
      <Suspense fallback={<div className="p-8 text-sm">Загрузка…</div>}>
        <PivotWorkspaceView projectId={projectId} />
      </Suspense>
    </LegacyProjectPipelineGuard>
  );
}
