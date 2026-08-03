"use client";

import { CommercialOptionalSection } from "@/components/commercial/form/commercial-optional-section";
import { useIntakeDraft } from "@/components/project-intake/intake-draft-context";
import {
  CheckboxRow,
  FieldHint,
  FieldError,
  FieldLabel,
  StepSection,
  TextInput,
  TextTextarea,
} from "@/components/project-intake/intake-fields";
import { useStepErrors } from "@/components/project-intake/intake-wizard-shell";
import { useIntakeStepCopy, useIntakeWizardCopy } from "@/lib/project-intake/use-intake-wizard-copy";

export function StepMarketForm() {
  const stepCopy = useIntakeStepCopy("market");
  const marketCopy = useIntakeWizardCopy().steps.market;
  const { draft, setDraft } = useIntakeDraft();
  const errors = useStepErrors();
  const m = draft.market;

  const patch = (partial: Partial<typeof m>) => {
    setDraft((prev) => ({
      ...prev,
      market: { ...prev.market, ...partial },
    }));
  };

  const hasOptionalValues =
    Boolean(m.knownCompetitors.trim()) ||
    Boolean(m.competitorUrls.trim()) ||
    Boolean(m.marketAssumptions.trim()) ||
    Boolean(m.demandEvidence.trim()) ||
    Boolean(m.seasonality.trim()) ||
    Boolean(m.restrictions.trim());

  return (
    <StepSection
      title={stepCopy.title}
      description={stepCopy.description}
      data-testid="intake-step-market"
    >
      <div>
        <FieldLabel htmlFor="targetMarket" required>
          Целевой рынок
        </FieldLabel>
        <TextTextarea
          id="targetMarket"
          value={m.targetMarket}
          onChange={(targetMarket) => patch({ targetMarket })}
          error={errors.targetMarket}
          required
        />
      </div>
      <div>
        <FieldLabel htmlFor="geography">География рынка</FieldLabel>
        <TextInput
          id="geography"
          value={m.geography}
          onChange={(geography) => patch({ geography })}
          error={errors.geography}
          placeholder={
            draft.projectBasics.geography
              ? `По умолчанию из проекта: ${draft.projectBasics.geography}`
              : "Регион рынка"
          }
        />
        <FieldHint>Можно оставить пустым, если совпадает с географией проекта.</FieldHint>
      </div>

      <div
        className="space-y-2 rounded-lg border p-3"
        style={{ borderColor: "var(--ms-border-default)" }}
      >
        <CheckboxRow
          id="competitorsUnknown"
          checked={m.competitorsUnknown}
          onChange={(competitorsUnknown) => patch({ competitorsUnknown })}
        >
          Конкуренты неизвестны
        </CheckboxRow>
        <CheckboxRow
          id="demandUnavailable"
          checked={m.demandUnavailable}
          onChange={(demandUnavailable) => patch({ demandUnavailable })}
        >
          Данных о спросе нет
        </CheckboxRow>
        <CheckboxRow
          id="marketSizeUnknown"
          checked={m.marketSizeUnknown}
          onChange={(marketSizeUnknown) => patch({ marketSizeUnknown })}
        >
          Размер рынка неизвестен
        </CheckboxRow>
      </div>

      {m.competitorsUnknown ? (
        <FieldHint>{marketCopy.competitorsHiddenHint}</FieldHint>
      ) : (
        <>
          <div>
            <FieldLabel htmlFor="knownCompetitors">Известные конкуренты</FieldLabel>
            <TextTextarea
              id="knownCompetitors"
              value={m.knownCompetitors}
              onChange={(knownCompetitors) => patch({ knownCompetitors })}
              rows={3}
            />
          </div>
          <div>
            <FieldLabel htmlFor="competitorUrls">URL конкурентов</FieldLabel>
            <TextTextarea
              id="competitorUrls"
              value={m.competitorUrls}
              onChange={(competitorUrls) => patch({ competitorUrls })}
              rows={2}
              placeholder="По одному URL на строку"
            />
            <FieldError id="competitors-error" message={errors.competitors} />
          </div>
        </>
      )}

      <CommercialOptionalSection defaultOpen={hasOptionalValues} testId="intake-market-optional">
        <div>
          <FieldLabel htmlFor="marketAssumptions">Гипотезы о рынке</FieldLabel>
          <TextTextarea
            id="marketAssumptions"
            value={m.marketAssumptions}
            onChange={(marketAssumptions) => patch({ marketAssumptions })}
            rows={3}
          />
        </div>
        <div>
          <FieldLabel htmlFor="demandEvidence">Уже имеющиеся доказательства спроса</FieldLabel>
          <TextTextarea
            id="demandEvidence"
            value={m.demandEvidence}
            onChange={(demandEvidence) => patch({ demandEvidence })}
            rows={3}
          />
        </div>
        <div>
          <FieldLabel htmlFor="seasonality">Сезонность</FieldLabel>
          <TextInput
            id="seasonality"
            value={m.seasonality}
            onChange={(seasonality) => patch({ seasonality })}
          />
        </div>
        <div>
          <FieldLabel htmlFor="restrictions">Юридические / отраслевые ограничения</FieldLabel>
          <TextTextarea
            id="restrictions"
            value={m.restrictions}
            onChange={(restrictions) => patch({ restrictions })}
            rows={3}
          />
        </div>
      </CommercialOptionalSection>
    </StepSection>
  );
}
