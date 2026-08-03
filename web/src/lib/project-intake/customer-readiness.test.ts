import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  customerReadinessLabel,
  formatMoneyValue,
} from "./customer-readiness";

describe("customer intake readiness labels", () => {
  it("maps internal statuses to Russian customer copy", () => {
    assert.equal(customerReadinessLabel("ready"), "Готово к исследованию");
    assert.equal(customerReadinessLabel("conditionally_ready"), "Можно начинать, но есть вопросы");
    assert.equal(customerReadinessLabel("insufficient_data"), "Нужно дополнить данные");
  });

  it("formats money without raw enum tokens", () => {
    assert.equal(formatMoneyValue({ mode: "unknown" }), "Пока не указано");
    assert.equal(formatMoneyValue({ mode: "exact", exact: "500000" }), "500000");
    assert.equal(formatMoneyValue({ mode: "range", min: "100", max: "200" }), "100 – 200");
  });
});
