/**
 * Per-step field validation for Product Alpha intake.
 */

import type { IntakeStepId, ProjectIntakeDraft } from "@/lib/project-intake/types";

export type FieldErrors = Record<string, string>;

function req(value: string | undefined, label: string): string | undefined {
  if (!value || !value.trim()) return `${label} — обязательное поле`;
  return undefined;
}

export function validateStep(
  step: IntakeStepId,
  draft: ProjectIntakeDraft,
): FieldErrors {
  const errors: FieldErrors = {};

  if (step === "basics") {
    const b = draft.projectBasics;
    const name = req(b.name, "Название проекта");
    if (name) errors.name = name;
    const idea = req(b.ideaDescription, "Описание идеи");
    if (idea) errors.ideaDescription = idea;
    else if (b.ideaDescription.trim().split(/\s+/).length < 5) {
      errors.ideaDescription = "Опишите идею чуть подробнее (минимум несколько слов)";
    }
    if (!b.businessType) errors.businessType = "Выберите тип бизнеса";
    if (!b.projectStage) errors.projectStage = "Выберите стадию проекта";
    const geo = req(b.geography, "География");
    if (geo) errors.geography = geo;
  }

  if (step === "product") {
    const p = draft.product;
    const sold = req(p.whatIsSold, "Что продаётся");
    if (sold) errors.whatIsSold = sold;
    const problem = req(p.primaryProblem, "Проблема клиента");
    if (problem) errors.primaryProblem = problem;
    const value = req(p.valueProposition, "Ценностное предложение");
    if (value) errors.valueProposition = value;
    if (!p.deliveryUnknown && !p.deliveryModel.trim()) {
      errors.deliveryModel = "Укажите модель доставки или отметьте «пока неизвестно»";
    }
    if (!p.priceUnknown && p.price.mode === "exact" && !p.price.exact?.trim()) {
      errors.price = "Укажите цену или отметьте unknown";
    }
    if (
      !p.priceUnknown &&
      p.price.mode === "range" &&
      !p.price.min?.trim() &&
      !p.price.max?.trim()
    ) {
      errors.price = "Укажите диапазон цены или отметьте unknown";
    }
  }

  if (step === "market") {
    const m = draft.market;
    const target = req(m.targetMarket, "Целевой рынок");
    if (target) errors.targetMarket = target;
    if (!m.geography.trim() && !draft.projectBasics.geography.trim()) {
      errors.geography = "Укажите географию рынка";
    }
    if (
      !m.competitorsUnknown &&
      !m.knownCompetitors.trim() &&
      !m.competitorUrls.trim()
    ) {
      errors.competitors =
        "Укажите конкурентов / URL или отметьте, что конкуренты неизвестны";
    }
  }

  if (step === "audience") {
    const hasSegment = draft.audience.segments.some(
      (s) => s.label.trim() || s.notes.trim(),
    );
    if (!hasSegment) {
      errors.segments = "Добавьте хотя бы одну гипотезу сегмента";
    }
  }

  if (step === "economics") {
    const e = draft.economics;
    if (e.launchBudget.mode === "exact" && !e.launchBudget.exact?.trim()) {
      errors.launchBudget = "Укажите бюджет запуска, диапазон или unknown";
    }
    if (
      e.launchBudget.mode === "range" &&
      !e.launchBudget.min?.trim() &&
      !e.launchBudget.max?.trim()
    ) {
      errors.launchBudget = "Укажите диапазон бюджета запуска или unknown";
    }
    if (
      e.monthlyMarketingBudget.mode === "exact" &&
      !e.monthlyMarketingBudget.exact?.trim()
    ) {
      errors.monthlyMarketingBudget =
        "Укажите месячный бюджет, диапазон или unknown";
    }
  }

  // materials & review — no hard block on materials
  return errors;
}

export function firstErrorFieldId(errors: FieldErrors): string | null {
  const keys = Object.keys(errors);
  return keys[0] ?? null;
}
