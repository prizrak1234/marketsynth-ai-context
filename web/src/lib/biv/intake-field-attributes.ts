/** Stable HTML semantics for BIV intake fields — prevents browser email/login autofill. */

export type IntakeFieldKey =
  | "idea_description"
  | "product_or_service"
  | "target_customer"
  | "geography"
  | "analysis_goal"
  | "pricing_or_revenue_model"
  | "known_competitors"
  | "current_stage"
  | "budget_context";

export type IntakeFieldHtmlAttrs = {
  id: string;
  name: string;
  autoComplete: string;
  inputMode?: "text" | "decimal" | "search" | "none";
  type?: "text";
};

export const INTAKE_FIELD_HTML_ATTRS: Record<IntakeFieldKey, IntakeFieldHtmlAttrs> = {
  idea_description: {
    id: "project-idea-description",
    name: "project_idea_description",
    autoComplete: "off",
    type: "text",
  },
  product_or_service: {
    id: "project-product",
    name: "project_product",
    autoComplete: "off",
    type: "text",
  },
  target_customer: {
    id: "project-audience",
    name: "project_target_audience",
    autoComplete: "off",
    type: "text",
  },
  geography: {
    id: "project-geography",
    name: "project_geography",
    autoComplete: "off",
    type: "text",
  },
  analysis_goal: {
    id: "project-analysis-goal",
    name: "project_analysis_goal",
    autoComplete: "off",
    type: "text",
  },
  pricing_or_revenue_model: {
    id: "project-pricing",
    name: "project_pricing",
    autoComplete: "off",
    inputMode: "text",
    type: "text",
  },
  known_competitors: {
    id: "project-competitors",
    name: "project_competitors",
    autoComplete: "off",
    type: "text",
  },
  current_stage: {
    id: "project-stage",
    name: "project_stage",
    autoComplete: "off",
    type: "text",
  },
  budget_context: {
    id: "project-budget",
    name: "project_budget",
    autoComplete: "off",
    inputMode: "decimal",
    type: "text",
  },
};
