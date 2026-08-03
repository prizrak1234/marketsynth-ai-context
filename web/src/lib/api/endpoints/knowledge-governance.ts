import { apiJson } from "@/lib/api/client";

export type KgObjectSummary = {
  id: string;
  code: string;
  title: string;
  domain: string;
  status: string;
  current_version_id: string | null;
  visibility: string;
};

export type KgObjectDetail = {
  id: string;
  code: string;
  title: string;
  domain: string;
  status: string;
  current_version_id: string | null;
  versions: Array<{
    id: string;
    version: string;
    status: string;
    freshness: string;
    owner_user_id: string | null;
    reviewer_user_id: string | null;
    review_date: string | null;
    next_review_at: string | null;
    source_uri: string;
    lock_version: number;
    replacement_version_id: string | null;
  }>;
  semantic_chunks: Array<{
    id: string;
    title: string;
    intent: string;
    rule: string;
    source_location: string | null;
  }>;
};

export function listKgCandidates() {
  return apiJson<{ candidates: KgObjectSummary[]; count: number }>(
    "/knowledge-governance/candidates",
  );
}

export function listKgObjects(status?: string) {
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiJson<{ objects: KgObjectSummary[]; count: number }>(
    `/knowledge-governance/objects${q}`,
  );
}

export function getKgObject(id: string) {
  return apiJson<KgObjectDetail>(`/knowledge-governance/objects/${id}`);
}

export function assignKgOwner(
  objectId: string,
  body: { owner_user_id: string; reviewer_user_id?: string | null },
) {
  return apiJson(`/knowledge-governance/objects/${objectId}/assign-owner`, {
    method: "POST",
    body,
  });
}

export function validateKgVersion(
  versionId: string,
  body?: { decision?: string; rationale?: string; next_review_days?: number },
) {
  return apiJson(`/knowledge-governance/versions/${versionId}/validate`, {
    method: "POST",
    body: body ?? { decision: "approve" },
  });
}

export function publishKgVersion(versionId: string) {
  return apiJson(`/knowledge-governance/versions/${versionId}/publish`, {
    method: "POST",
    body: {},
  });
}

export function deprecateKgVersion(versionId: string) {
  return apiJson(`/knowledge-governance/versions/${versionId}/deprecate`, {
    method: "POST",
    body: {},
  });
}

export function archiveKgVersion(versionId: string) {
  return apiJson(`/knowledge-governance/versions/${versionId}/archive`, {
    method: "POST",
    body: {},
  });
}

export function getKgFreshness() {
  return apiJson<{
    checks: Array<{
      version_id: string;
      freshness: string;
      expired: boolean;
      deprecated: boolean;
      owner_review_task: boolean;
      safe_message: string;
    }>;
    count: number;
  }>("/knowledge-governance/freshness");
}

export function listKgBenchmarks() {
  return apiJson<{
    datasets: Array<{
      id: string;
      name: string;
      version: string;
      domain: string;
      case_count: number;
    }>;
    count: number;
  }>("/knowledge-governance/benchmarks");
}
