import assert from "node:assert/strict";
import { afterEach, beforeEach, describe, it, mock } from "node:test";

import { fetchProjectLatestBivRun } from "./business-idea-validation";

describe("fetchProjectLatestBivRun (PRODUCT-01.3B)", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:8000";
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    mock.restoreAll();
  });

  it("returns found for HTTP 200", async () => {
    globalThis.fetch = mock.fn(async () =>
      Response.json({
        project_id: "p1",
        run_id: "r1",
        user_request_id: "u1",
        status: "failed",
        created_at: "2026-01-01T00:00:00Z",
        has_output: true,
        retry_allowed: true,
        result_kind: "partial_research",
      }),
    ) as typeof fetch;

    const result = await fetchProjectLatestBivRun("p1");
    assert.equal(result.kind, "found");
    if (result.kind === "found") {
      assert.equal(result.summary.run_id, "r1");
      assert.equal(result.summary.result_kind, "partial_research");
    }
  });

  it("returns not_found for HTTP 404", async () => {
    globalThis.fetch = mock.fn(async () =>
      new Response(JSON.stringify({ detail: "not found" }), { status: 404 }),
    ) as typeof fetch;

    const result = await fetchProjectLatestBivRun("p1");
    assert.equal(result.kind, "not_found");
  });

  it("returns server_error for HTTP 500 instead of null", async () => {
    globalThis.fetch = mock.fn(async () =>
      new Response(JSON.stringify({ detail: "internal" }), { status: 500 }),
    ) as typeof fetch;

    const result = await fetchProjectLatestBivRun("p1");
    assert.equal(result.kind, "server_error");
    if (result.kind === "server_error") {
      assert.equal(result.status, 500);
    }
  });

  it("returns auth_error for HTTP 403", async () => {
    globalThis.fetch = mock.fn(async () =>
      new Response(JSON.stringify({ detail: "forbidden" }), { status: 403 }),
    ) as typeof fetch;

    const result = await fetchProjectLatestBivRun("p1");
    assert.equal(result.kind, "auth_error");
  });
});
