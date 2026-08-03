import { AssetsPageView } from "@/components/workspace/sections/assets-page-view";
import { LegacyCommercialGuard } from "@/components/routing/legacy-commercial-guard";

export default function Page() {
  return (
    <LegacyCommercialGuard featureKey="commercial.surface.features.assets">
      <AssetsPageView />
    </LegacyCommercialGuard>
  );
}
