import { InvestigationsPageView } from "@/components/workspace/sections/investigations-page-view";
import { LegacyCommercialGuard } from "@/components/routing/legacy-commercial-guard";

export default function Page() {
  return (
    <LegacyCommercialGuard featureKey="commercial.surface.features.projectPipeline">
      <InvestigationsPageView />
    </LegacyCommercialGuard>
  );
}
