"use client";

import type { AgencyStage } from "@/lib/home/agency-analysis-flow";
import { CommercialTimeline } from "@/components/commercial/commercial-timeline";
import { useLocale } from "@/lib/i18n";

type Props = {
  stages: AgencyStage[];
  working?: boolean;
  embedded?: boolean;
};

/** BIV stage list — delegates to CommercialTimeline (UNIFICATION-01). */
export function AgencyAnalysisStages({ stages, working, embedded = false }: Props) {
  const { t } = useLocale();
  return (
    <CommercialTimeline
      title={embedded ? undefined : t("agency.stagesTitle")}
      working={working}
      embedded={embedded}
      testId="agency-analysis-stages"
      stages={stages.map((s) => ({
        id: s.id,
        label: t(s.labelKey),
        status: s.status,
      }))}
    />
  );
}
