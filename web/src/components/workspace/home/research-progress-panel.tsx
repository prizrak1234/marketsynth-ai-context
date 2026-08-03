"use client";

import type { AgencyStage } from "@/lib/home/agency-analysis-flow";
import { AgencyAnalysisStages } from "@/components/workspace/home/agency-analysis-stages";
import { CommercialCard } from "@/components/commercial/commercial-card";
import { CommercialPageHeader } from "@/components/commercial/commercial-page-header";

type ResearchProgressPanelProps = {
  title: string;
  stages: AgencyStage[];
  working?: boolean;
};

/** Research running state — J2.1/J2.2 (IA: research.panel). */
export function ResearchProgressPanel({
  title,
  stages,
  working = true,
}: ResearchProgressPanelProps) {
  return (
    <CommercialCard testId="biv-research-progress-panel" className="space-y-4">
      <CommercialPageHeader level="panel" title={title} testId="biv-research-progress-header" />
      <AgencyAnalysisStages stages={stages} working={working} embedded />
    </CommercialCard>
  );
}
