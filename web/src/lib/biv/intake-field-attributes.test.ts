import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { INTAKE_FIELD_HTML_ATTRS } from "./intake-field-attributes";

describe("INTAKE_FIELD_HTML_ATTRS", () => {
  it("budget field uses business semantics that block email/login autofill", () => {
    const budget = INTAKE_FIELD_HTML_ATTRS.budget_context;
    assert.equal(budget.id, "project-budget");
    assert.equal(budget.name, "project_budget");
    assert.equal(budget.autoComplete, "off");
    assert.equal(budget.inputMode, "decimal");
    assert.equal(budget.type, "text");
    assert.notEqual(budget.name, "email");
    assert.notEqual(budget.name, "username");
  });

  it("optional business fields avoid credential autofill names", () => {
    for (const key of [
      "pricing_or_revenue_model",
      "known_competitors",
      "current_stage",
    ] as const) {
      const attrs = INTAKE_FIELD_HTML_ATTRS[key];
      assert.equal(attrs.autoComplete, "off");
      assert.ok(!/email|password|username|login/i.test(attrs.name));
    }
  });
});
