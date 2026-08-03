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

export function StepEconomicsForm() {
  const stepCopy = useIntakeStepCopy("economics");
  const { draft, setDraft } = useIntakeDraft();
  const errors = useStepErrors();
  const e = draft.economics;

  const patch = (partial: Partial<typeof e>) => {
    setDraft((prev) => ({
      ...prev,
      economics: { ...prev.economics, ...partial },
    }));
  };

  return (
    <StepSection
      title={stepCopy.title}
      description={stepCopy.description}
      data-testid="intake-step-economics"
    >
      <MoneyField
        id="launchBudget"
        label="Бюджет запуска"
        required
        value={e.launchBudget}
        onChange={(launchBudget) => patch({ launchBudget })}
        error={errors.launchBudget}
      />
      <MoneyField
        id="monthlyMarketingBudget"
        label="Месячный маркетинговый бюджет"
        required
        value={e.monthlyMarketingBudget}
        onChange={(monthlyMarketingBudget) => patch({ monthlyMarketingBudget })}
        error={errors.monthlyMarketingBudget}
      />
      <MoneyField
        id="targetRevenue"
        label="Целевая выручка"
        value={e.targetRevenue}
        onChange={(targetRevenue) => patch({ targetRevenue })}
      />
      <MoneyField
        id="averageOrderValue"
        label="Ожидаемый средний чек"
        value={e.averageOrderValue}
        onChange={(averageOrderValue) => patch({ averageOrderValue })}
      />

      <div>
        <FieldLabel htmlFor="paybackPeriod">Целевой срок окупаемости</FieldLabel>
        <TextInput
          id="paybackPeriod"
          value={e.paybackPeriod}
          onChange={(paybackPeriod) => patch({ paybackPeriod })}
          placeholder="Например: 6–9 месяцев"
        />
        <div className="mt-2">
          <CheckboxRow
            id="paybackUnknown"
            checked={e.paybackUnknown}
            onChange={(paybackUnknown) => patch({ paybackUnknown })}
          >
            Срок окупаемости неизвестен
          </CheckboxRow>
        </div>
      </div>

      <div>
        <FieldLabel htmlFor="grossMargin">Валовая маржа (если известна)</FieldLabel>
        <TextInput
          id="grossMargin"
          value={e.grossMargin}
          onChange={(grossMargin) => patch({ grossMargin })}
        />
        <div className="mt-2">
          <CheckboxRow
            id="grossMarginUnknown"
            checked={e.grossMarginUnknown}
            onChange={(grossMarginUnknown) => patch({ grossMarginUnknown })}
          >
            Маржа неизвестна
          </CheckboxRow>
        </div>
      </div>

      <div>
        <FieldLabel htmlFor="teamSize">Размер команды</FieldLabel>
        <TextInput
          id="teamSize"
          value={e.teamSize}
          onChange={(teamSize) => patch({ teamSize })}
        />
        <div className="mt-2">
          <CheckboxRow
            id="teamSizeUnknown"
            checked={e.teamSizeUnknown}
            onChange={(teamSizeUnknown) => patch({ teamSizeUnknown })}
          >
            Размер команды неизвестен
          </CheckboxRow>
        </div>
      </div>

      <div>
        <FieldLabel htmlFor="internalResources">Внутренние ресурсы</FieldLabel>
        <TextTextarea
          id="internalResources"
          value={e.internalResources}
          onChange={(internalResources) => patch({ internalResources })}
          rows={3}
        />
      </div>
      <div>
        <FieldLabel htmlFor="launchDeadline">Дедлайн запуска</FieldLabel>
        <TextInput
          id="launchDeadline"
          value={e.launchDeadline}
          onChange={(launchDeadline) => patch({ launchDeadline })}
        />
        <div className="mt-2">
          <CheckboxRow
            id="launchDeadlineUnknown"
            checked={e.launchDeadlineUnknown}
            onChange={(launchDeadlineUnknown) => patch({ launchDeadlineUnknown })}
          >
            Дедлайн неизвестен / гибкий
          </CheckboxRow>
        </div>
      </div>
      <div>
        <FieldLabel htmlFor="criticalConstraints">Критические ограничения</FieldLabel>
        <TextTextarea
          id="criticalConstraints"
          value={e.criticalConstraints}
          onChange={(criticalConstraints) => patch({ criticalConstraints })}
          rows={3}
        />
      </div>
    </StepSection>
  );
}
