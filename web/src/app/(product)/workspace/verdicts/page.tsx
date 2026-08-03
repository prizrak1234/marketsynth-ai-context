import { LegacyCommercialGuard } from "@/components/routing/legacy-commercial-guard";
import { VerdictsPageView } from "@/components/workspace/sections/verdicts-page-view";

export default function Page() {
  return (
    <LegacyCommercialGuard featureKey="commercial.surface.features.projectPipeline">
      <VerdictsPageView />
    </LegacyCommercialGuard>
  );
}
