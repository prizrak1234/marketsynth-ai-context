/**
 * P0.3 — Investigation Sources panel adapter (backend + hybrid labels).
 */

import type { SourceDto } from "@/lib/api/types/sources";
import { mapBackendSourceToView } from "@/lib/integration/source-api-adapter";
import type { IntegrationMode } from "@/lib/integration/mode";
import type { InvestigationSource } from "@/lib/investigation/types";

export type InvestigationSourcesPanelModel = {
  mode: IntegrationMode;
  backendSources: InvestigationSource[];
  localPreviewSources: InvestigationSource[];
  emptyBackend: boolean;
  provenanceOnlyNotice: string;
  allowMockFallback: boolean;
};

export function buildInvestigationSourcesPanel(args: {
  mode: IntegrationMode;
  backend: SourceDto[];
  local: InvestigationSource[];
}): InvestigationSourcesPanelModel {
  const { mode, backend, local } = args;
  const backendViews = backend.map((s) => mapBackendSourceToView(s, "backend"));
  if (mode === "mock") {
    return {
      mode,
      backendSources: [],
      localPreviewSources: local,
      emptyBackend: true,
      provenanceOnlyNotice:
        "Mock: локальные Sources. Durable provenance — в hybrid/backend.",
      allowMockFallback: true,
    };
  }
  if (mode === "backend") {
    return {
      mode,
      backendSources: backendViews,
      localPreviewSources: [],
      emptyBackend: backendViews.length === 0,
      provenanceOnlyNotice:
        "На этом этапе Marketsynth сохраняет только сведения о происхождении источника. Анализ и доказательства создаются отдельно.",
      allowMockFallback: false,
    };
  }
  // hybrid
  const backendIds = new Set(backendViews.map((s) => s.id));
  const localOnly = local
    .filter((s) => !backendIds.has(s.id))
    .map((s) => ({
      ...s,
      notes: `[local preview] ${s.notes}`,
    }));
  return {
    mode,
    backendSources: backendViews,
    localPreviewSources: localOnly,
    emptyBackend: backendViews.length === 0,
    provenanceOnlyNotice:
      "Hybrid: backend Sources — SoT; local preview помечен отдельно. Без silent merge.",
    allowMockFallback: true,
  };
}
