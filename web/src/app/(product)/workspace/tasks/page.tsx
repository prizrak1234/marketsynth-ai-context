import { Suspense } from "react";
import { LegacyCommercialRedirect } from "@/components/routing/legacy-commercial-redirect";
import { WorkspaceTasksRoute } from "@/components/workspace/sections/tasks-route";

export default function Page() {
  return (
    <Suspense fallback={<div className="p-8 text-sm">Загрузка…</div>}>
      <LegacyCommercialRedirect featureKey="commercial.surface.features.tasks">
        <WorkspaceTasksRoute />
      </LegacyCommercialRedirect>
    </Suspense>
  );
}
