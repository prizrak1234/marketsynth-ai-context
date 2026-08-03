import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  resolvePostAuthHref,
  workspaceEntryHrefFromProjects,
} from "@/lib/routes/workspace-entry";

describe("workspaceEntryHrefFromProjects", () => {
  it("routes single project to PCC", () => {
    assert.equal(workspaceEntryHrefFromProjects([{ id: "p1" }]), "/workspace?project=p1");
  });

  it("routes many projects to list", () => {
    assert.equal(
      workspaceEntryHrefFromProjects([{ id: "a" }, { id: "b" }]),
      "/workspace/projects",
    );
  });

  it("routes zero projects to intake", () => {
    assert.equal(workspaceEntryHrefFromProjects([]), "/workspace/projects/new");
  });
});

describe("resolvePostAuthHref", () => {
  it("keeps deep-link next when not bare workspace", async () => {
    const href = await resolvePostAuthHref(
      "/workspace?project=abc&view=content_director",
    );
    assert.equal(href, "/workspace?project=abc&view=content_director");
  });
});
