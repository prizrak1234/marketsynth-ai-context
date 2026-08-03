import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { createEmptyDraft } from "@/lib/project-intake/schema";
import { buildSubmissionFingerprint } from "@/lib/integration/intake-project-mapping";

describe("project identity contract", () => {
  it("fresh draft has no backend binding", () => {
    const draft = createEmptyDraft("review");
    assert.equal(draft.backendSync?.backendProjectId, null);
    assert.equal(draft.backendSync?.backendSyncState, "local_only");
  });

  it("stale binding fingerprint does not imply alreadyLinked", () => {
    const draft = createEmptyDraft("review");
    draft.projectBasics.name = "Test";
    draft.projectBasics.ideaDescription = "SaaS for small business reporting automation";
    const fp = buildSubmissionFingerprint(draft);
    draft.backendSync = {
      backendProjectId: "00000000-0000-0000-0000-000000000099",
      backendSyncState: "partially_synced",
      backendSyncedAt: "2026-01-01T00:00:00.000Z",
      backendUpdatedAt: "2026-01-01T00:00:00.000Z",
      lastSyncError: "Проект не найден на backend.",
      submissionFingerprint: "fp_old",
      localDraftVersion: draft.updatedAt,
    };
    assert.notEqual(draft.backendSync.submissionFingerprint, fp);
  });
});
