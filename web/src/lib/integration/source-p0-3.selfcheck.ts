/**
 * P0.3 Source domain selfcheck.
 * Run: npx --yes tsx src/lib/integration/source-p0-3.selfcheck.ts
 */

import {
  createsEvidenceFromSource,
  fetchesUrlOnRegister,
  mapBackendSourceToView,
} from "@/lib/integration/source-api-adapter";
import { buildInvestigationSourcesPanel } from "@/lib/integration/investigation-source-adapter";
import { normalizeSourceError, unsupportedFetchError } from "@/lib/integration/source-errors";
import type { SourceDto } from "@/lib/api/types/sources";
import { ApiError } from "@/lib/api/errors";

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}

{
  assert(createsEvidenceFromSource() === false, "no evidence");
  assert(fetchesUrlOnRegister() === false, "no fetch");
  assert(unsupportedFetchError().kind === "unsupported_fetch", "fetch blocked");
}

{
  const dto: SourceDto = {
    id: "s1",
    owner_id: "o",
    project_id: "p",
    source_type: "website",
    provenance_type: "secondary",
    title: "Site",
    origin: "public",
    url: "https://example.com",
    domain: "example.com",
    publisher: null,
    language: "ru",
    country: null,
    published_at: null,
    captured_at: "2026-01-01T00:00:00Z",
    accessed_at: null,
    freshness_status: "unknown",
    reliability_level: "unverified",
    status: "registered",
    fingerprint: "a".repeat(64),
    content_hash: null,
    etag: null,
    version: 1,
    supersedes_source_id: null,
    license_type: null,
    capabilities: ["webpage", "text"],
    reusable_within_project: true,
    metadata: { stores_content: false },
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
  const view = mapBackendSourceToView(dto);
  assert(view.noEvidence === true, "noEvidence");
  assert(!("conclusion" in view), "no conclusion");
  assert(view.notes.includes("P0.4"), "defers evidence");
}

{
  const panel = buildInvestigationSourcesPanel({
    mode: "backend",
    backend: [],
    local: [
      {
        id: "local-1",
        title: "Mock",
        sourceType: "website",
        origin: "mock",
        accessedAtLabel: "—",
        freshness: "unknown",
        reliability: "unverified",
        relevance: "low",
        status: "available",
        notes: "x",
      },
    ],
  });
  assert(panel.allowMockFallback === false, "no mock fallback");
  assert(panel.backendSources.length === 0, "empty backend");
  assert(panel.localPreviewSources.length === 0, "no local in backend");
  assert(panel.provenanceOnlyNotice.includes("происхождении"), "copy");
}

{
  const err = normalizeSourceError(
    new ApiError("x", 409, { safe_message: "duplicate_source" }),
  );
  assert(err.kind === "duplicate_source", "dup kind");
}

console.log("source-p0-3.selfcheck: OK");
