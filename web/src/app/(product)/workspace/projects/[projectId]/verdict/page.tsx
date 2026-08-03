"use client";

import { Suspense, use } from "react";
import { LegacyProjectPipelineGuard } from "@/components/routing/legacy-commercial-guard";
import { VerdictWorkspaceView } from "@/components/verdict/verdict-workspace-view";

export default function VerdictPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  return (
    <LegacyProjectPipelineGuard projectId={projectId}>
      <Suspense fallback={<div className="p-8 text-sm">Загрузка…</div>}>
        <VerdictWorkspaceView projectId={projectId} />
      </Suspense>
    </LegacyProjectPipelineGuard>
  );
}
