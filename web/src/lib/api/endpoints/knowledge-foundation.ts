import { apiJson } from "@/lib/api/client";

export type KnowledgeItemDto = {
  id: string;
  title: string;
  knowledge_type: string;
  domain: string;
  status: string;
  version: string;
  source_uri: string;
  source_hash: string | null;
  authority: string;
  tenant_scope: string;
  locale: string;
  specialist_roles: string[];
  tags: string[];
  citation_required: boolean;
  supersedes_id: string | null;
  notes: string | null;
};

export type SpecialistSkillDto = {
  id: string;
  code: string;
  version: string;
  title: string;
  domain: string;
  status: string;
  specialist_roles: string[];
  clarification_schema: string[];
  knowledge_scopes: string[];
  required_tools: string[];
  optional_tools: string[];
  quality_gates: string[];
  execution_policy: string;
};

export type CapabilityPackDto = {
  specialist_role: string;
  version: string;
  allowed_skills: string[];
  default_skill: string | null;
  knowledge_scopes: string[];
  tool_profile: string[];
  forbidden_tools: string[];
  output_policy: string;
  approval_policy: string;
  quality_profile: string[];
};

export function listKnowledgeInventory(params?: {
  status?: string;
  domain?: string;
  knowledge_type?: string;
  locale?: string;
}) {
  const q = new URLSearchParams();
  if (params?.status) q.set("status", params.status);
  if (params?.domain) q.set("domain", params.domain);
  if (params?.knowledge_type) q.set("knowledge_type", params.knowledge_type);
  if (params?.locale) q.set("locale", params.locale);
  const suffix = q.toString() ? `?${q}` : "";
  return apiJson<KnowledgeItemDto[]>(`/knowledge-foundation/inventory${suffix}`);
}

export function approveKnowledgeItem(id: string, note?: string) {
  return apiJson<KnowledgeItemDto>(`/knowledge-foundation/inventory/${id}/approve`, {
    method: "POST",
    body: { note: note ?? null },
  });
}

export function rejectKnowledgeItem(id: string, note?: string) {
  return apiJson<KnowledgeItemDto>(`/knowledge-foundation/inventory/${id}/reject`, {
    method: "POST",
    body: { note: note ?? null },
  });
}

export function listStoredKnowledge(params?: { status?: string; locale?: string }) {
  const q = new URLSearchParams();
  if (params?.status) q.set("status", params.status);
  if (params?.locale) q.set("locale", params.locale);
  const suffix = q.toString() ? `?${q}` : "";
  return apiJson<
    Array<{
      id: string;
      code: string;
      title: string;
      knowledge_type: string;
      status: string;
      version: string;
      source_uri: string;
      source_hash: string | null;
      authority: string;
      tenant_scope: string;
      locale: string;
      content_hash: string;
    }>
  >(`/knowledge-foundation/items${suffix}`);
}

export function ingestContentPack() {
  return apiJson<unknown[]>("/knowledge-foundation/items/ingest-content-pack", {
    method: "POST",
    body: {},
  });
}

export function getKnowledgePolicy() {
  return apiJson<{
    storage_option: string;
    embeddings_enabled: boolean;
    bulk_repo_ingestion_enabled: boolean;
    execution_enabled: boolean;
    retrieval_order: string[];
    first_approved_pack_ids: string[];
  }>("/knowledge-foundation/policy");
}

export function listSpecialistSkills() {
  return apiJson<{
    skills: SpecialistSkillDto[];
    count: number;
    execution_enabled: boolean;
    prompts_exposed: boolean;
  }>("/specialist-skills");
}

export function listCapabilityPacks() {
  return apiJson<{ packs: CapabilityPackDto[]; count: number }>(
    "/specialist-skills/capability-packs",
  );
}

export function listSkillRouteMatrix() {
  return apiJson<{
    mappings: Array<{
      route_category: string;
      specialist_role: string | null;
      skill_code: string | null;
      notes: string;
      uses_existing_project_path: boolean;
    }>;
  }>("/specialist-skills/route-matrix");
}
