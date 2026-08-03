import { LegacyCommercialGuard } from "@/components/routing/legacy-commercial-guard";
import { ImplementationPageView } from "@/components/workspace/sections/implementation-page-view";

export default function Page() {
  return (
    <LegacyCommercialGuard featureKey="commercial.surface.features.projectPipeline">
      <ImplementationPageView />
    </LegacyCommercialGuard>
  );
}
