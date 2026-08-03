import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  commercialTimelineStageColor,
  commercialTimelineStageMark,
} from "./commercial-timeline-utils";

describe("CommercialTimeline utils", () => {
  it("maps stage marks", () => {
    assert.equal(commercialTimelineStageMark("done"), "✓");
    assert.equal(commercialTimelineStageMark("running"), "…");
    assert.equal(commercialTimelineStageMark("pending"), "○");
  });

  it("uses design tokens for stage colors", () => {
    assert.equal(commercialTimelineStageColor("done"), "var(--ms-status-success)");
    assert.equal(commercialTimelineStageColor("running"), "var(--ms-brand-primary)");
    assert.equal(commercialTimelineStageColor("pending"), "var(--ms-text-muted)");
  });
});
