/**
 * Lightweight assertions for the intent catalog (no new test framework).
 * Run: npx tsx web/src/lib/home/user-intent-catalog.test.ts
 */

import assert from "node:assert/strict";
import { USER_INTENTS, getIntentById } from "./user-intent-catalog";

assert.equal(USER_INTENTS.length, 6, "expected six primary intents");

const content = getIntentById("create-content");
assert.ok(content?.subIntents?.length, "create-content must have sub-intents");
assert.ok(
  content?.subIntents?.some((s) => s.id === "telegram-post"),
  "telegram sub-intent required",
);
assert.ok(
  content?.subIntents?.some((s) => s.id === "youtube-script"),
  "youtube sub-intent required",
);
assert.ok(
  content?.subIntents?.some((s) => s.id === "content-plan"),
  "content-plan sub-intent required",
);

const validate = getIntentById("validate-idea");
assert.equal(validate?.triggersBiv, true, "validate-idea must trigger BIV");

console.log("user-intent-catalog.test.ts: ok");
