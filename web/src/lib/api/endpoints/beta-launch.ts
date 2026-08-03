import { apiJson } from "@/lib/api/client";
import type { BetaAccess } from "@/lib/api/types/beta-guide";
import type { BetaGuide } from "@/lib/api/types/beta-guide";

export function fetchBetaAccess() {
  return apiJson<BetaAccess>("/me/beta-access");
}

export function fetchBetaGuide() {
  return apiJson<BetaGuide>("/me/beta-guide");
}
