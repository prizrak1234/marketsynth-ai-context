/**
 * P0.1 — Local draft ↔ backend ProjectBrief reconciliation.
 */

import type { ProjectBriefDto } from "@/lib/api/types/project-briefs";

export type BriefReconciliationCase =
  | "equal_fingerprint"
  | "local_newer"
  | "backend_newer"
  | "different_fingerprints"
  | "backend_missing"
  | "local_unlinked"
  | "version_conflict"
  | "ownership_error";

export type BriefConflictOption =
  | "keep_local"
  | "load_backend"
  | "create_new_backend_version"
  | "cancel";

export type BriefReconciliationResult = {
  case: BriefReconciliationCase;
  message: string;
  options: BriefConflictOption[];
  autoMerge: false;
};

export function reconcileBriefFingerprints(input: {
  localFingerprint: string | null;
  backend: ProjectBriefDto | null;
  localUpdatedAt: string | null;
}): BriefReconciliationResult {
  if (!input.backend) {
    return {
      case: "backend_missing",
      message: "Backend ProjectBrief отсутствует.",
      options: ["create_new_backend_version", "keep_local", "cancel"],
      autoMerge: false,
    };
  }
  if (!input.localFingerprint) {
    return {
      case: "local_unlinked",
      message: "Локальный fingerprint отсутствует — сверьте явно.",
      options: ["load_backend", "keep_local", "cancel"],
      autoMerge: false,
    };
  }
  if (input.localFingerprint === input.backend.input_fingerprint) {
    return {
      case: "equal_fingerprint",
      message: "Локальный и backend fingerprints совпадают.",
      options: ["keep_local", "load_backend", "cancel"],
      autoMerge: false,
    };
  }
  const localTs = input.localUpdatedAt ? Date.parse(input.localUpdatedAt) : 0;
  const backendTs = Date.parse(input.backend.updated_at);
  if (localTs > backendTs) {
    return {
      case: "local_newer",
      message: "Локальный draft новее backend Brief.",
      options: ["keep_local", "create_new_backend_version", "load_backend", "cancel"],
      autoMerge: false,
    };
  }
  if (backendTs > localTs) {
    return {
      case: "backend_newer",
      message: "Backend Brief новее локального draft.",
      options: ["load_backend", "keep_local", "create_new_backend_version", "cancel"],
      autoMerge: false,
    };
  }
  return {
    case: "different_fingerprints",
    message: "Fingerprints различаются.",
    options: ["keep_local", "load_backend", "create_new_backend_version", "cancel"],
    autoMerge: false,
  };
}
