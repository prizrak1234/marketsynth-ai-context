"use client";

import { CommercialAlert } from "@/components/commercial/commercial-alert";
import { useIntakeDraft } from "@/components/project-intake/intake-draft-context";
import {
  FieldHint,
  FieldLabel,
  StepSection,
  TextInput,
  TextTextarea,
} from "@/components/project-intake/intake-fields";
import { useIntakeStepCopy, useIntakeWizardCopy } from "@/lib/project-intake/use-intake-wizard-copy";
import type { MockMaterialKind } from "@/lib/project-intake/types";

const KIND_OPTIONS: Array<{ kind: MockMaterialKind; label: string }> = [
  { kind: "document", label: "Документ" },
  { kind: "spreadsheet", label: "Таблица" },
  { kind: "presentation", label: "Презентация" },
  { kind: "website_url", label: "Website URL" },
  { kind: "social_profile", label: "Соцпрофиль" },
  { kind: "research", label: "Существующее исследование" },
  { kind: "customer_interview", label: "Интервью с клиентами" },
  { kind: "analytics_export", label: "Выгрузка аналитики" },
  { kind: "competitor_list", label: "Список конкурентов" },
];

export function StepMaterialsForm() {
  const stepCopy = useIntakeStepCopy("materials");
  const materialsCopy = useIntakeWizardCopy().steps.materials;
  const { draft, setDraft } = useIntakeDraft();
  const m = draft.materials;

  const patch = (partial: Partial<typeof m>) => {
    setDraft((prev) => ({
      ...prev,
      materials: { ...prev.materials, ...partial },
    }));
  };

  const addMaterialNote = (kind: MockMaterialKind, label: string) => {
    patch({
      items: [
        ...m.items,
        {
          id: `mat_${Math.random().toString(36).slice(2, 9)}`,
          kind,
          label,
          note: materialsCopy.itemSavedLocally,
        },
      ],
    });
  };

  return (
    <StepSection
      title={stepCopy.title}
      description={stepCopy.description}
      data-testid="intake-step-materials"
    >
      <CommercialAlert
        tone="info"
        title={materialsCopy.localDraftNotice}
        testId="intake-materials-draft-notice"
      />

      <div>
        <FieldLabel htmlFor="websiteUrl">Website URL</FieldLabel>
        <TextInput
          id="websiteUrl"
          value={m.websiteUrl}
          onChange={(websiteUrl) => patch({ websiteUrl })}
          placeholder="https://"
        />
      </div>
      <div>
        <FieldLabel htmlFor="socialProfiles">Социальные профили</FieldLabel>
        <TextTextarea
          id="socialProfiles"
          value={m.socialProfiles}
          onChange={(socialProfiles) => patch({ socialProfiles })}
          rows={2}
          placeholder="По одному URL на строку"
        />
      </div>

      <div>
        <p className="mb-2 text-sm font-medium" style={{ color: "var(--ms-text-primary)" }}>
          {materialsCopy.addMaterialLabel}
        </p>
        <FieldHint>{materialsCopy.addMaterialHint}</FieldHint>
        <div className="mt-3 flex flex-wrap gap-2" data-testid="intake-materials-add-buttons">
          {KIND_OPTIONS.map((opt) => (
            <button
              key={opt.kind}
              type="button"
              className="min-h-[44px] rounded-md px-3 py-2 text-xs font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--ms-brand-primary)]"
              style={{
                background: "var(--ms-bg-elevated)",
                color: "var(--ms-text-secondary)",
                boxShadow: "inset 0 0 0 1px var(--ms-border-default)",
              }}
              onClick={() => addMaterialNote(opt.kind, opt.label)}
            >
              + {opt.label}
            </button>
          ))}
        </div>
      </div>

      {m.items.length > 0 ? (
        <ul className="space-y-2" data-testid="intake-materials-list">
          {m.items.map((item) => (
            <li
              key={item.id}
              className="flex items-center justify-between gap-3 rounded-md border px-3 py-2 text-sm"
              style={{
                borderColor: "var(--ms-border-default)",
                background: "var(--ms-bg-elevated)",
              }}
            >
              <div>
                <p style={{ color: "var(--ms-text-primary)" }}>{item.label}</p>
                <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                  {item.note}
                </p>
              </div>
              <button
                type="button"
                className="min-h-[44px] text-xs"
                style={{ color: "var(--ms-text-muted)" }}
                onClick={() =>
                  patch({ items: m.items.filter((i) => i.id !== item.id) })
                }
              >
                Убрать
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm" style={{ color: "var(--ms-text-muted)" }} data-testid="intake-materials-empty">
          {materialsCopy.emptyList}
        </p>
      )}
    </StepSection>
  );
}
