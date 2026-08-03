/** Commercial MVP P0.1 — ProjectBrief API types */

export type ProjectBriefStatus = "draft" | "submitted" | "superseded" | "archived";

export type ProjectBriefReadinessStatus =
  | "ready"
  | "conditionally_ready"
  | "insufficient_data";

export type MoneyValueMode = "exact" | "range" | "unknown";

export type MoneyValueDto = {
  mode: MoneyValueMode;
  exact?: string | null;
  min?: string | null;
  max?: string | null;
};

export type ProjectBriefDto = {
  id: string;
  owner_id: string;
  project_id: string;
  version: number;
  status: ProjectBriefStatus;
  language: string;
  project_basics: Record<string, unknown>;
  product: Record<string, unknown>;
  market: Record<string, unknown>;
  audience: Record<string, unknown>;
  economics: Record<string, unknown>;
  materials_summary: Record<string, unknown>;
  assumptions: string[];
  missing_data: string[];
  readiness_status: ProjectBriefReadinessStatus;
  readiness_reasons: string[];
  input_fingerprint: string;
  supersedes_brief_id: string | null;
  submitted_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ProjectBriefCreateBody = {
  language?: string;
  project_basics: Record<string, unknown>;
  product: Record<string, unknown>;
  market: Record<string, unknown>;
  audience: Record<string, unknown>;
  economics: Record<string, unknown>;
  materials_summary: Record<string, unknown>;
  assumptions: string[];
  missing_data: string[];
  readiness_status: ProjectBriefReadinessStatus;
  readiness_reasons: string[];
};
