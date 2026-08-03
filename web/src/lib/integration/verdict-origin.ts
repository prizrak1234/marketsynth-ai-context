/**
 * I4 — Business Verdict origin / authority labels.
 * Backend mode must never silently use mock as approved evidence-verified verdict.
 */

export type VerdictOrigin =
  | "mock"
  | "deterministic_local"
  | "backend"
  | "derived"
  | "imported";

export type VerdictAuthorityClaim =
  | "local_preview"
  | "deterministic_demo"
  | "backend_draft"
  | "backend_approved"
  | "evidence_verified"
  | "unsupported";

export type VerdictOriginMeta = {
  origin: VerdictOrigin;
  authority: VerdictAuthorityClaim;
  /** Human-facing restrained label */
  labelRu: string;
  labelEn: string;
  evidenceBasis:
    | "mock_evidence"
    | "projected_investigation"
    | "durable_evidence_sot"
    | "none";
  persistedToBackend: boolean;
  evidenceVerified: boolean;
};

export function mockVerdictOrigin(): VerdictOriginMeta {
  return {
    origin: "mock",
    authority: "deterministic_demo",
    labelRu: "Mock · Product Alpha",
    labelEn: "mock",
    evidenceBasis: "mock_evidence",
    persistedToBackend: false,
    evidenceVerified: false,
  };
}

export function deterministicLocalPreviewOrigin(): VerdictOriginMeta {
  return {
    origin: "deterministic_local",
    authority: "local_preview",
    labelRu: "Локальный предварительный вердикт",
    labelEn: "deterministic_local preview",
    evidenceBasis: "projected_investigation",
    persistedToBackend: false,
    evidenceVerified: false,
  };
}

/** I4 Option C legacy: kept for selfchecks; P0.5 adds durableBackendVerdictOrigin. */
export function unsupportedBackendVerdictOrigin(): VerdictOriginMeta {
  return {
    origin: "derived",
    authority: "unsupported",
    labelRu: "Backend BusinessVerdict SoT отсутствует",
    labelEn: "unsupported_backend",
    evidenceBasis: "none",
    persistedToBackend: false,
    evidenceVerified: false,
  };
}

export function durableBackendVerdictOrigin(approved: boolean): VerdictOriginMeta {
  return {
    origin: "backend",
    authority: approved ? "backend_approved" : "backend_draft",
    labelRu: approved
      ? "Backend · утверждённый BusinessVerdict"
      : "Backend · draft BusinessVerdict",
    labelEn: approved
      ? "Backend · approved BusinessVerdict"
      : "Backend · draft BusinessVerdict",
    evidenceBasis: "durable_evidence_sot",
    persistedToBackend: true,
    evidenceVerified: true,
  };
}

export function originAllowsStrategyFromAuthority(meta: VerdictOriginMeta): boolean {
  // Local/mock can gate Alpha strategy UI; never claim evidence-verified backend authority
  if (meta.evidenceVerified && !meta.persistedToBackend) return false;
  return (
    meta.authority === "local_preview" ||
    meta.authority === "deterministic_demo" ||
    meta.authority === "backend_approved"
  );
}
