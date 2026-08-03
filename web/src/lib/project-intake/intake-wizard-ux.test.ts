import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  customerReadinessLabel,
  readinessStatusTone,
} from "@/lib/project-intake/customer-readiness";
import { intakeWizardCopyRu } from "@/lib/i18n/translations/intake-wizard-copy";
import { createEmptyDraft } from "@/lib/project-intake/schema";
import { validateStep } from "@/lib/project-intake/validation";

describe("intake wizard UX (Slice E)", () => {
  it("uses unified required/optional markers in RU copy", () => {
    assert.equal(intakeWizardCopyRu.field.requiredMarker, "Обязательно");
    assert.equal(intakeWizardCopyRu.field.optionalMarker, "Дополнительно, если известно");
    assert.doesNotMatch(intakeWizardCopyRu.field.optionalMarker, /необязательно/i);
  });

  it("maps readiness to customer-safe labels", () => {
    assert.equal(customerReadinessLabel("ready"), "Готово к исследованию");
    assert.equal(customerReadinessLabel("conditionally_ready"), "Можно начинать, но есть вопросы");
    assert.equal(customerReadinessLabel("insufficient_data"), "Нужно дополнить данные");
    assert.equal(readinessStatusTone("ready"), "success");
    assert.equal(readinessStatusTone("conditionally_ready"), "warning");
    assert.equal(readinessStatusTone("insufficient_data"), "danger");
  });

  it("keeps market competitors validation when not unknown", () => {
    const draft = createEmptyDraft();
    draft.market.targetMarket = "Online education";
    draft.market.competitorsUnknown = false;
    draft.market.knownCompetitors = "";
    draft.market.competitorUrls = "";
    const errors = validateStep("market", draft);
    assert.ok(errors.competitors);
  });

  it("allows market step when competitors marked unknown", () => {
    const draft = createEmptyDraft();
    draft.market.targetMarket = "Online education";
    draft.market.competitorsUnknown = true;
    const errors = validateStep("market", draft);
    assert.equal(errors.competitors, undefined);
  });

  it("provides step context copy for all seven steps", () => {
    const ids = ["basics", "product", "market", "audience", "economics", "materials", "review"] as const;
    for (const id of ids) {
      assert.ok(intakeWizardCopyRu.steps[id].title.length > 0);
      assert.ok(intakeWizardCopyRu.steps[id].description.length > 0);
    }
    assert.doesNotMatch(intakeWizardCopyRu.steps.materials.localDraftNotice, /Product Alpha/i);
  });
});
