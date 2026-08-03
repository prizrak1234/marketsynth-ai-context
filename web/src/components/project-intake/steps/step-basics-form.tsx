"use client";

import { useIntakeDraft } from "@/components/project-intake/intake-draft-context";
import {
  FieldHint,
  FieldLabel,
  StepSection,
  TextInput,
  TextSelect,
  TextTextarea,
} from "@/components/project-intake/intake-fields";
import { useStepErrors } from "@/components/project-intake/intake-wizard-shell";
import {
  BUSINESS_TYPE_OPTIONS,
  PROJECT_STAGE_OPTIONS,
} from "@/lib/project-intake/schema";
import { useIntakeStepCopy } from "@/lib/project-intake/use-intake-wizard-copy";
import type { BusinessType, InterfaceLanguage, ProjectStage } from "@/lib/project-intake/types";

export function StepBasicsForm() {
  const stepCopy = useIntakeStepCopy("basics");
  const { draft, setDraft } = useIntakeDraft();
  const errors = useStepErrors();
  const b = draft.projectBasics;

  const patch = (partial: Partial<typeof b>) => {
    setDraft((prev) => ({
      ...prev,
      projectBasics: { ...prev.projectBasics, ...partial },
    }));
  };

  return (
    <StepSection
      title={stepCopy.title}
      description={stepCopy.description}
      data-testid="intake-step-basics"
    >
      <div>
        <FieldLabel htmlFor="name" required>
          Название проекта
        </FieldLabel>
        <TextInput
          id="name"
          value={b.name}
          onChange={(name) => patch({ name })}
          error={errors.name}
          required
          placeholder="Например: Dental clinic lead gen"
        />
      </div>

      <div>
        <FieldLabel htmlFor="ideaDescription" required>
          Краткое описание идеи
        </FieldLabel>
        <TextTextarea
          id="ideaDescription"
          value={b.ideaDescription}
          onChange={(ideaDescription) => patch({ ideaDescription })}
          error={errors.ideaDescription}
          required
          rows={4}
          placeholder="Что вы хотите проверить и для кого"
          describedBy="idea-hint"
        />
        <FieldHint id="idea-hint">
          Не пишите роман — достаточно ясной формулировки гипотезы.
        </FieldHint>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <FieldLabel htmlFor="businessType" required>
            Тип бизнеса
          </FieldLabel>
          <TextSelect
            id="businessType"
            value={b.businessType}
            onChange={(v) => patch({ businessType: v as BusinessType | "" })}
            options={BUSINESS_TYPE_OPTIONS}
            error={errors.businessType}
            required
          />
        </div>
        <div>
          <FieldLabel htmlFor="projectStage" required>
            Стадия проекта
          </FieldLabel>
          <TextSelect
            id="projectStage"
            value={b.projectStage}
            onChange={(v) => patch({ projectStage: v as ProjectStage | "" })}
            options={PROJECT_STAGE_OPTIONS}
            error={errors.projectStage}
            required
          />
        </div>
      </div>

      <div>
        <FieldLabel htmlFor="geography" required>
          Регион / география
        </FieldLabel>
        <TextInput
          id="geography"
          value={b.geography}
          onChange={(geography) => patch({ geography })}
          error={errors.geography}
          required
          placeholder="Например: РФ · Москва и МО"
        />
      </div>

      <div>
        <FieldLabel htmlFor="interfaceLanguage">Язык интерфейса</FieldLabel>
        <TextSelect
          id="interfaceLanguage"
          value={b.interfaceLanguage}
          onChange={(v) => patch({ interfaceLanguage: v as InterfaceLanguage })}
          options={[
            { value: "ru", label: "Русский" },
            { value: "en", label: "English" },
          ]}
          placeholder="Язык"
        />
      </div>
    </StepSection>
  );
}
