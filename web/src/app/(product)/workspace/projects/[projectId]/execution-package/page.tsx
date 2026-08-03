"use client";

import { Suspense, use } from "react";
import { LegacyProjectPipelineGuard } from "@/components/routing/legacy-commercial-guard";
import { ExecutionPackageWorkspaceView } from "@/components/execution-package/execution-package-workspace-view";

export default function ExecutionPackagePage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  return (
    <LegacyProjectPipelineGuard projectId={projectId}>
      <Suspense fallback={<div className="p-8 text-sm">Загрузка…</div>}>
        <ExecutionPackageWorkspaceView projectId={projectId} />
      </Suspense>
    </LegacyProjectPipelineGuard>
  );
}
