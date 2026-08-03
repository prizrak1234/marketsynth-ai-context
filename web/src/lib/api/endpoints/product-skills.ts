import { apiJson } from "@/lib/api/client";

export type ProductSkillIndexItem = {
  skill_id: string;
  name: string;
  version: string;
  description: string;
  type: string;
  triggers: string[];
  accepted_input_types: string[];
  output_types: string[];
  install_status: string;
  configured: boolean;
  enabled: boolean;
  required_secret_aliases: string[];
  permissions_summary: string;
  last_run_status: string | null;
  last_run_at: string | null;
  safe_error: string | null;
};

export function fetchProductSkills() {
  return apiJson<ProductSkillIndexItem[]>("/skills");
}

export function fetchProductSkillsWorkspace() {
  return apiJson<{ skills: ProductSkillIndexItem[]; next_action: string }>(
    "/skills/workspace",
  );
}
