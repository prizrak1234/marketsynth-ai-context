import type { AnalysisContextFields } from "@/lib/api/endpoints/analysis-contexts";

/** Mirrors backend BLOCKING_FIELDS (PRODUCT-01.3A.3). */
export const BLOCKING_FIELD_KEYS = [
  "idea_description",
  "product_or_service",
  "target_customer",
  "geography",
  "analysis_goal",
] as const;

export type BlockingFieldKey = (typeof BLOCKING_FIELD_KEYS)[number];

export const OPTIONAL_RESEARCH_GAP_FIELDS = [
  "pricing_or_revenue_model",
  "known_competitors",
  "current_stage",
  "budget_context",
] as const;

const PLACEHOLDER_PATTERNS = [
  /^бизнес$/i,
  /^business$/i,
  /^идея$/i,
  /^idea$/i,
  /^test$/i,
  /^тест$/i,
  /^example$/i,
  /^пример$/i,
  /^lorem ipsum/i,
  /^your idea here/i,
  /^опишите идею/i,
  /^например:/i,
];

const EXPLICIT_UNKNOWN = new Set(["неизвестно", "unknown", "не знаю", "n/a", "нет данных"]);

function sanitize(value: string | null | undefined): string {
  return (value ?? "").trim();
}

function isExplicitUnknown(value: string | null | undefined): boolean {
  return EXPLICIT_UNKNOWN.has(sanitize(value).toLowerCase());
}

function ideaInvalid(idea: string): boolean {
  if (!idea) return true;
  if (idea.split(/\s+/).length <= 1 && idea.length < 12) return true;
  if (PLACEHOLDER_PATTERNS.some((re) => re.test(idea))) return true;
  return /^https?:\/\/\S+$/i.test(idea);
}

export type SpecificityEvaluation = {
  missing_fields: string[];
  warnings: string[];
  can_confirm: boolean;
};

export function evaluateAnalysisContextSpecificity(
  fields: AnalysisContextFields & { idea_description?: string },
): SpecificityEvaluation {
  const missing: string[] = [];
  const warnings: string[] = [];

  const idea = sanitize(fields.idea_description);
  let product = sanitize(fields.product_or_service);
  const target = sanitize(fields.target_customer);
  const geo = sanitize(fields.geography);
  const goal = sanitize(fields.analysis_goal);

  if (ideaInvalid(idea)) {
    missing.push("idea_description");
  }

  if (!product && idea.split(/\s+/).length >= 2 && !PLACEHOLDER_PATTERNS.some((re) => re.test(idea))) {
    product = idea;
  }
  if (!product) {
    missing.push("product_or_service");
  }

  const audienceUnknown =
    Boolean(fields.target_customer_unknown) || isExplicitUnknown(fields.target_customer);
  if (!target && !audienceUnknown) {
    missing.push("target_customer");
  } else if (audienceUnknown) {
    warnings.push("target_customer_unknown");
  }

  const geoUnknown = Boolean(fields.geography_unknown) || isExplicitUnknown(fields.geography);
  if (!geo && !geoUnknown) {
    missing.push("geography");
  } else if (geoUnknown) {
    warnings.push("geography_unknown");
  }

  if (!goal) {
    missing.push("analysis_goal");
  }

  for (const fieldName of OPTIONAL_RESEARCH_GAP_FIELDS) {
    const raw = fields[fieldName as keyof AnalysisContextFields];
    const value = sanitize(typeof raw === "string" ? raw : null);
    if (!value || isExplicitUnknown(value)) {
      warnings.push(`research_gap_${fieldName}`);
    }
  }

  return {
    missing_fields: missing,
    warnings,
    can_confirm: missing.length === 0,
  };
}

export function mergeContextSpecificity<T extends AnalysisContextFields & Record<string, unknown>>(
  context: T,
): T & { missing_fields: string[]; warnings: string[] } {
  const evalResult = evaluateAnalysisContextSpecificity(context);
  return {
    ...context,
    missing_fields: evalResult.missing_fields,
    warnings: evalResult.warnings,
  };
}
