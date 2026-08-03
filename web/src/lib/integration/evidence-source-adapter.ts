/**
 * P0.4 — Evidence ↔ Source stance / locator mapping.
 */

import type { EvidenceDto, EvidenceSourceLinkDto } from "@/lib/api/types/evidence";

export type EvidenceSourceTrace = {
  sourceId: string;
  stance: EvidenceSourceLinkDto["stance"];
  locator: string;
  excerpt: string | null;
};

export function mapEvidenceSourceTraces(dto: EvidenceDto): EvidenceSourceTrace[] {
  return dto.source_links.map((link) => ({
    sourceId: link.source_id,
    stance: link.stance,
    locator: [link.locator_type, link.locator_value].filter(Boolean).join(": "),
    excerpt: link.excerpt,
  }));
}
