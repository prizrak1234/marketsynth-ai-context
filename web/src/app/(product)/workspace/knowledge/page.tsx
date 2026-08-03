import { LegacyCommercialGuard } from "@/components/routing/legacy-commercial-guard";
import { KnowledgePageView } from "@/components/workspace/sections/knowledge-page-view";

export default function Page() {
  return (
    <LegacyCommercialGuard featureKey="commercial.surface.features.projectPipeline">
      <KnowledgePageView />
    </LegacyCommercialGuard>
  );
}
