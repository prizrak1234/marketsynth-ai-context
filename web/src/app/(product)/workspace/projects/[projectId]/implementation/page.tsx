"use client";

import { Suspense, use } from "react";
import { LegacyProjectPipelineGuard } from "@/components/routing/legacy-commercial-guard";
import { ImplementationPlanWorkspaceView } from "@/components/implementation-plan/implementation-plan-workspace-view";

export default function ImplementationPlanPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  return (
    <LegacyProjectPipelineGuard projectId={projectId}>
      <Suspense fallback={<div className="p-8 text-sm">Загрузка…</div>}>
        <ImplementationPlanWorkspaceView projectId={projectId} />
      </Suspense>
    </LegacyProjectPipelineGuard>
  );
}
