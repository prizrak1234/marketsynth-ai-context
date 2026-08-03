"use client";

import { Suspense, use } from "react";
import { LegacyProjectPipelineGuard } from "@/components/routing/legacy-commercial-guard";
import { StrategyWorkspaceView } from "@/components/strategy/strategy-workspace-view";

export default function StrategyPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  return (
    <LegacyProjectPipelineGuard projectId={projectId}>
      <Suspense fallback={<div className="p-8 text-sm">Загрузка…</div>}>
        <StrategyWorkspaceView projectId={projectId} />
      </Suspense>
    </LegacyProjectPipelineGuard>
  );
}
