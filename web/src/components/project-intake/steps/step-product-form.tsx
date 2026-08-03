"use client";

import { useIntakeDraft } from "@/components/project-intake/intake-draft-context";
import {
  CheckboxRow,
  FieldLabel,
  MoneyField,
  StepSection,
  TextInput,
  TextTextarea,
} from "@/components/project-intake/intake-fields";
import { useStepErrors } from "@/components/project-intake/intake-wizard-shell";

import { useIntakeStepCopy } from "@/lib/project-intake/use-intake-wizard-copy";

export function StepProductForm() {
  const stepCopy = useIntakeStepCopy("product");
  const { draft, setDraft } = useIntakeDraft();
  const errors = useStepErrors();
  const p = draft.product;

  const patch = (partial: Partial<typeof p>) => {
    setDraft((prev) => ({
      ...prev,
      product: { ...prev.product, ...partial },
    }));
  };

  return (
    <StepSection
      title={stepCopy.title}
      description={stepCopy.description}
      data-testid="intake-step-product"
    >
      <div>
        <FieldLabel htmlFor="whatIsSold" required>
          Что именно продаётся
        </FieldLabel>
        <TextTextarea
          id="whatIsSold"
          value={p.whatIsSold}
          onChange={(whatIsSold) => patch({ whatIsSold })}
          error={errors.whatIsSold}
          required
        />
      </div>
      <div>
        <FieldLabel htmlFor="primaryProblem" required>
          Главная проблема клиента
        </FieldLabel>
        <TextTextarea
          id="primaryProblem"
          value={p.primaryProblem}
          onChange={(primaryProblem) => patch({ primaryProblem })}
          error={errors.primaryProblem}
          required
        />
      </div>
      <div>
        <FieldLabel htmlFor="valueProposition" required>
          Ценностное предложение
        </FieldLabel>
        <TextTextarea
          id="valueProposition"
          value={p.valueProposition}
          onChange={(valueProposition) => patch({ valueProposition })}
          error={errors.valueProposition}
          required
        />
      </div>

      <MoneyField
        id="price"
        label="Ожидаемая цена / диапазон"
        value={p.priceUnknown ? { ...p.price, mode: "unknown" } : p.price}
        onChange={(price) =>
          patch({
            price,
            priceUnknown: price.mode === "unknown",
          })
        }
        error={errors.price}
        hint="Не выдумывайте цифры — лучше отметьте unknown."
      />

      <div>
        <FieldLabel htmlFor="deliveryModel">Модель доставки</FieldLabel>
        <TextInput
          id="deliveryModel"
          value={p.deliveryModel}
          onChange={(deliveryModel) => patch({ deliveryModel })}
          error={errors.deliveryModel}
          placeholder="Онлайн, клиника, доставка, SaaS…"
        />
        <div className="mt-2">
          <CheckboxRow
            id="deliveryUnknown"
            checked={p.deliveryUnknown}
            onChange={(deliveryUnknown) => patch({ deliveryUnknown })}
          >
            Модель доставки пока неизвестна
          </CheckboxRow>
        </div>
      </div>

      <div>
        <FieldLabel htmlFor="differentiators">Известные отличия</FieldLabel>
        <TextTextarea
          id="differentiators"
          value={p.differentiators}
          onChange={(differentiators) => patch({ differentiators })}
          rows={3}
        />
      </div>
      <div>
        <FieldLabel htmlFor="knownLimitations">Известные ограничения</FieldLabel>
        <TextTextarea
          id="knownLimitations"
          value={p.knownLimitations}
          onChange={(knownLimitations) => patch({ knownLimitations })}
          rows={3}
        />
      </div>
    </StepSection>
  );
}
