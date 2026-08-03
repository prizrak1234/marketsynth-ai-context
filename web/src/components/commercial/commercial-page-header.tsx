import type { ReactNode } from "react";

type CommercialPageHeaderProps = {
  title: string;
  description?: string;
  eyebrow?: ReactNode;
  actions?: ReactNode;
  /** Page title (h1) or panel title (h2) — DESIGN.md §4 */
  level?: "page" | "panel";
  testId?: string;
};

/** Canonical page/panel header (DESIGN.md §6). */
export function CommercialPageHeader({
  title,
  description,
  eyebrow,
  actions,
  level = "page",
  testId,
}: CommercialPageHeaderProps) {
  const TitleTag = level === "page" ? "h1" : "h2";
  const titleClass =
    level === "page" ? "text-2xl font-semibold" : "text-lg font-semibold";

  return (
    <header
      className="flex flex-wrap items-start justify-between gap-4"
      data-testid={testId}
    >
      <div className="min-w-0 space-y-2">
        {eyebrow ? <div>{eyebrow}</div> : null}
        <TitleTag className={titleClass} style={{ color: "var(--ms-text-primary)" }}>
          {title}
        </TitleTag>
        {description ? (
          <p className="max-w-3xl text-sm" style={{ color: "var(--ms-text-secondary)" }}>
            {description}
          </p>
        ) : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap gap-2">{actions}</div> : null}
    </header>
  );
}
