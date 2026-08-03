/**
 * Marketsynth semantic design-token names (TypeScript mirror of CSS variables).
 * Prefer CSS variables in components; use these keys for typed references.
 */
export const BRAND_TOKEN_PATHS = {
  brand: {
    primary: "--ms-brand-primary",
    primaryHover: "--ms-brand-primary-hover",
    primaryActive: "--ms-brand-primary-active",
    secondary: "--ms-brand-secondary",
    accent: "--ms-brand-accent",
  },
  background: {
    canvas: "--ms-bg-canvas",
    surface: "--ms-bg-surface",
    elevated: "--ms-bg-elevated",
  },
  text: {
    primary: "--ms-text-primary",
    secondary: "--ms-text-secondary",
    muted: "--ms-text-muted",
    inverse: "--ms-text-inverse",
  },
  border: {
    default: "--ms-border-default",
    strong: "--ms-border-strong",
    focus: "--ms-border-focus",
  },
  status: {
    success: "--ms-status-success",
    warning: "--ms-status-warning",
    danger: "--ms-status-danger",
    info: "--ms-status-info",
  },
  risk: {
    low: "--ms-risk-low",
    medium: "--ms-risk-medium",
    high: "--ms-risk-high",
    critical: "--ms-risk-critical",
  },
  verdict: {
    go: "--ms-verdict-go",
    conditionalGo: "--ms-verdict-conditional-go",
    noGo: "--ms-verdict-no-go",
    insufficientData: "--ms-verdict-insufficient-data",
  },
  evidence: {
    confirmed: "--ms-evidence-confirmed",
    partial: "--ms-evidence-partial",
    conflicting: "--ms-evidence-conflicting",
    missing: "--ms-evidence-missing",
    outdated: "--ms-evidence-outdated",
  },
  approval: {
    pending: "--ms-approval-pending",
    approved: "--ms-approval-approved",
    rejected: "--ms-approval-rejected",
    expired: "--ms-approval-expired",
  },
  execution: {
    ready: "--ms-execution-ready",
    blocked: "--ms-execution-blocked",
    running: "--ms-execution-running",
    verifying: "--ms-execution-verifying",
    succeeded: "--ms-execution-succeeded",
    failed: "--ms-execution-failed",
  },
} as const;
