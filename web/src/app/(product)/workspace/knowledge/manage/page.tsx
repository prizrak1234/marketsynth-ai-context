import { LegacyCommercialGuard } from "@/components/routing/legacy-commercial-guard";
import { KnowledgeManagementView } from "@/components/workspace/sections/knowledge-management-view";

export default function Page() {
  return (
    <LegacyCommercialGuard featureKey="commercial.surface.features.projectPipeline">
      <KnowledgeManagementView />
    </LegacyCommercialGuard>
  );
}
