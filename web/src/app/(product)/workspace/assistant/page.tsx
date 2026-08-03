import { WorkspaceAssistantView } from "@/components/workspace/sections/assistant-page-view";
import { LegacyCommercialGuard } from "@/components/routing/legacy-commercial-guard";

export default function Page() {
  return (
    <LegacyCommercialGuard featureKey="commercial.surface.features.assistant">
      <WorkspaceAssistantView />
    </LegacyCommercialGuard>
  );
}
