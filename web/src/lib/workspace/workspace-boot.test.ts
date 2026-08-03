import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { ApiError } from "@/lib/api/errors";
import {
  classifyProjectsFetchError,
  loadWorkspaceBootDestination,
  workspaceBootFromProjects,
  workspaceUrlsEquivalent,
  WORKSPACE_BOOT_PROJECTS_TIMEOUT_MS,
} from "@/lib/workspace/workspace-boot";

describe("workspaceBootFromProjects", () => {
  it("single → PCC href", () => {
    const r = workspaceBootFromProjects([{ id: "p1" }]);
    assert.equal(r.status, "single_project");
    if (r.status === "single_project") {
      assert.equal(r.projectId, "p1");
      assert.equal(r.href, "/workspace?project=p1");
    }
  });

  it("multi → projects list", () => {
    const r = workspaceBootFromProjects([{ id: "a" }, { id: "b" }]);
    assert.equal(r.status, "multi_projects");
    if (r.status === "multi_projects") {
      assert.equal(r.href, "/workspace/projects");
    }
  });

  it("empty → intake", () => {
    const r = workspaceBootFromProjects([]);
    assert.equal(r.status, "no_projects");
    if (r.status === "no_projects") {
      assert.equal(r.href, "/workspace/projects/new");
    }
  });
});

describe("workspaceUrlsEquivalent", () => {
  it("treats trailing slash as same path", () => {
    assert.equal(
      workspaceUrlsEquivalent("/workspace", "/workspace/"),
      true,
    );
  });

  it("distinguishes query", () => {
    assert.equal(
      workspaceUrlsEquivalent("/workspace", "/workspace?project=p1"),
      false,
    );
  });

  it("same project url is equivalent", () => {
    assert.equal(
      workspaceUrlsEquivalent(
        "/workspace?project=p1",
        "/workspace?project=p1",
      ),
      true,
    );
  });
});

describe("classifyProjectsFetchError", () => {
  it("maps AbortError to timeout", () => {
    const e = classifyProjectsFetchError(
      new DOMException("projects_timeout", "AbortError"),
    );
    assert.equal(e.kind, "timeout");
    assert.equal(e.retryable, true);
  });

  it("maps 401 to unauthorized", () => {
    const e = classifyProjectsFetchError(
      new ApiError("no", 401, {}, "authentication_required"),
    );
    assert.equal(e.kind, "unauthorized");
    assert.equal(e.retryable, false);
  });

  it("maps 500 to retryable http", () => {
    const e = classifyProjectsFetchError(
      new ApiError("boom", 500, {}, "server_error"),
    );
    assert.equal(e.kind, "http");
    assert.equal(e.retryable, true);
  });
});

describe("loadWorkspaceBootDestination", () => {
  it("returns single_project from fetch", async () => {
    const r = await loadWorkspaceBootDestination({
      fetchProjectsFn: async () => [{ id: "x" }] as never,
    });
    assert.equal(r.status, "single_project");
  });

  it("returns error on timeout", async () => {
    const r = await loadWorkspaceBootDestination({
      timeoutMs: 30,
      fetchProjectsFn: () =>
        new Promise(() => {
          /* never resolves */
        }),
    });
    assert.equal(r.status, "error");
    if (r.status === "error") {
      assert.equal(r.kind, "timeout");
      assert.equal(r.retryable, true);
    }
  });

  it("returns unauthorized on 401", async () => {
    const r = await loadWorkspaceBootDestination({
      fetchProjectsFn: async () => {
        throw new ApiError("no", 401, {}, "authentication_required");
      },
    });
    assert.equal(r.status, "error");
    if (r.status === "error") {
      assert.equal(r.kind, "unauthorized");
    }
  });

  it("default timeout is bounded", () => {
    assert.ok(WORKSPACE_BOOT_PROJECTS_TIMEOUT_MS <= 15_000);
    assert.ok(WORKSPACE_BOOT_PROJECTS_TIMEOUT_MS >= 1_000);
  });
});
