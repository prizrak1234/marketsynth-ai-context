"use client";

import { useIntakeDraft } from "@/components/project-intake/intake-draft-context";
import {
  FieldError,
  FieldHint,
  FieldLabel,
  StepSection,
  TextInput,
  TextSelect,
  TextTextarea,
} from "@/components/project-intake/intake-fields";
import { useStepErrors } from "@/components/project-intake/intake-wizard-shell";
import { CUSTOMER_MODEL_OPTIONS, newSegment } from "@/lib/project-intake/schema";
import type { CustomerModel } from "@/lib/project-intake/types";

import { useIntakeStepCopy } from "@/lib/project-intake/use-intake-wizard-copy";

export function StepAudienceForm() {
  const stepCopy = useIntakeStepCopy("audience");
  const { draft, setDraft } = useIntakeDraft();
  const errors = useStepErrors();
  const a = draft.audience;

  const patch = (partial: Partial<typeof a>) => {
    setDraft((prev) => ({
      ...prev,
      audience: { ...prev.audience, ...partial },
    }));
  };

  return (
    <StepSection
      title={stepCopy.title}
      description={stepCopy.description}
      data-testid="intake-step-audience"
    >
      <div>
        <FieldLabel htmlFor="customerModel">Модель клиентов</FieldLabel>
        <TextSelect
          id="customerModel"
          value={a.customerModel}
          onChange={(v) => patch({ customerModel: v as CustomerModel })}
          options={CUSTOMER_MODEL_OPTIONS}
          placeholder="Модель"
        />
      </div>

      <div className="space-y-3">
        <p className="text-sm font-medium" style={{ color: "var(--ms-text-primary)" }}>
          Гипотезы сегментов <span style={{ color: "var(--ms-status-danger)" }}>*</span>
        </p>
        <FieldHint>
          Это гипотезы для исследования, не финальные сегменты агентства.
        </FieldHint>
        <FieldError id="segments-error" message={errors.segments} />
        {a.segments.map((seg, index) => (
          <div
            key={seg.id}
            className="space-y-2 rounded-md border p-3"
            style={{ borderColor: "var(--ms-border-default)" }}
          >
            <FieldLabel htmlFor={`seg-label-${seg.id}`}>
              Сегмент {index + 1}
            </FieldLabel>
            <TextInput
              id={`seg-label-${seg.id}`}
              value={seg.label}
              onChange={(label) =>
                patch({
                  segments: a.segments.map((s) =>
                    s.id === seg.id ? { ...s, label } : s,
                  ),
                })
              }
              placeholder="Например: владельцы клиник 1–3 кресла"
            />
            <TextTextarea
              id={`seg-notes-${seg.id}`}
              value={seg.notes}
              onChange={(notes) =>
                patch({
                  segments: a.segments.map((s) =>
                    s.id === seg.id ? { ...s, notes } : s,
                  ),
                })
              }
              rows={2}
              placeholder="Кратко: кто это и зачем им продукт"
            />
            {a.segments.length > 1 ? (
              <button
                type="button"
                className="text-xs"
                style={{ color: "var(--ms-text-muted)" }}
                onClick={() =>
                  patch({ segments: a.segments.filter((s) => s.id !== seg.id) })
                }
              >
                Удалить сегмент
              </button>
            ) : null}
          </div>
        ))}
        <button
          type="button"
          className="rounded-md px-3 py-2 text-xs font-semibold"
          style={{
            background: "var(--ms-bg-elevated)",
            color: "var(--ms-text-secondary)",
            boxShadow: "inset 0 0 0 1px var(--ms-border-default)",
          }}
          onClick={() => patch({ segments: [...a.segments, newSegment()] })}
        >
          Добавить сегмент
        </button>
      </div>

      <div>
        <FieldLabel htmlFor="decisionMaker">ЛПР / decision maker</FieldLabel>
        <TextInput
          id="decisionMaker"
          value={a.decisionMaker}
          onChange={(decisionMaker) => patch({ decisionMaker })}
        />
      </div>
      <div>
        <FieldLabel htmlFor="buyerUserDistinction">Покупатель vs пользователь</FieldLabel>
        <TextTextarea
          id="buyerUserDistinction"
          value={a.buyerUserDistinction}
          onChange={(buyerUserDistinction) => patch({ buyerUserDistinction })}
          rows={2}
        />
      </div>
      <div>
        <FieldLabel htmlFor="customerLocation">Локация клиентов</FieldLabel>
        <TextInput
          id="customerLocation"
          value={a.customerLocation}
          onChange={(customerLocation) => patch({ customerLocation })}
        />
      </div>
      <div>
        <FieldLabel htmlFor="expectedPains">Ожидаемые боли</FieldLabel>
        <TextTextarea
          id="expectedPains"
          value={a.expectedPains}
          onChange={(expectedPains) => patch({ expectedPains })}
          rows={3}
        />
      </div>
      <div>
        <FieldLabel htmlFor="expectedObjections">Ожидаемые возражения</FieldLabel>
        <TextTextarea
          id="expectedObjections"
          value={a.expectedObjections}
          onChange={(expectedObjections) => patch({ expectedObjections })}
          rows={3}
        />
      </div>
      <div>
        <FieldLabel htmlFor="currentResearch">Уже проведённое исследование аудитории</FieldLabel>
        <TextTextarea
          id="currentResearch"
          value={a.currentResearch}
          onChange={(currentResearch) => patch({ currentResearch })}
          rows={3}
        />
      </div>
    </StepSection>
  );
}
