import type { ReactNode } from "react";

type PublicPageShellProps = {
  children: ReactNode;
  skipLabel: string;
};

/** Public marketing shell — no Workspace AppShell. */
export function PublicPageShell({ children, skipLabel }: PublicPageShellProps) {
  return (
    <div
      className="min-h-screen"
      style={{
        background: "var(--ms-bg-canvas)",
        color: "var(--ms-text-primary)",
      }}
      data-testid="public-landing-page"
    >
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-[var(--ms-bg-elevated)] focus:px-3 focus:py-2 focus:text-sm"
      >
        {skipLabel}
      </a>
      {children}
    </div>
  );
}
