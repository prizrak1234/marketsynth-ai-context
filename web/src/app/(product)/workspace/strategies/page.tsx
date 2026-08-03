import { LegacyCommercialGuard } from "@/components/routing/legacy-commercial-guard";
import { StrategiesPageView } from "@/components/workspace/sections/strategies-page-view";

export default function Page() {
  return (
    <LegacyCommercialGuard featureKey="commercial.surface.features.projectPipeline">
      <StrategiesPageView />
    </LegacyCommercialGuard>
  );
}
