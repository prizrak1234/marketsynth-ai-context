import type { ReactNode } from "react";

import { CommercialButton } from "@/components/commercial/commercial-button";
import { CommercialCard } from "@/components/commercial/commercial-card";

type CommercialEmptyStateProps = {
  title: string;
  body?: string;
  ctaLabel?: string;
  ctaHref?: string;
  onCtaClick?: () => void;
  testId?: string;
  footer?: ReactNode;
};

/** Unified empty state for commercial list surfaces (DESIGN.md §5). */
export function CommercialEmptyState({
  title,
  body,
  ctaLabel,
  ctaHref,
  onCtaClick,
  testId = "commercial-empty-state",
  footer,
}: CommercialEmptyStateProps) {
  return (
    <CommercialCard padding="lg" testId={testId} className="text-center">
      <p className="font-medium" style={{ color: "var(--ms-text-primary)" }}>
        {title}
      </p>
      {body ? (
        <p className="mt-2 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
          {body}
        </p>
      ) : null}
      {ctaLabel && (ctaHref || onCtaClick) ? (
        <div className="mt-4">
          <CommercialButton
            href={ctaHref}
            onClick={onCtaClick}
            testId={`${testId}-cta`}
          >
            {ctaLabel}
          </CommercialButton>
        </div>
      ) : null}
      {footer ? <div className="mt-4">{footer}</div> : null}
    </CommercialCard>
  );
}
