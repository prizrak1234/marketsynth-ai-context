import { ReviewQueuePageView } from "@/components/workspace/sections/review-queue-page-view";
import { LegacyCommercialGuard } from "@/components/routing/legacy-commercial-guard";

export default function Page() {
  return (
    <LegacyCommercialGuard featureKey="commercial.surface.features.review">
      <ReviewQueuePageView />
    </LegacyCommercialGuard>
  );
}
