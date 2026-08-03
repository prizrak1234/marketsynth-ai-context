import { ChannelsPageView } from "@/components/workspace/sections/channels-page-view";
import { LegacyCommercialGuard } from "@/components/routing/legacy-commercial-guard";

export default function Page() {
  return (
    <LegacyCommercialGuard featureKey="commercial.surface.features.channels">
      <ChannelsPageView />
    </LegacyCommercialGuard>
  );
}
