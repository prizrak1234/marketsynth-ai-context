import type { ReactNode } from "react";

type PublicSectionProps = {
  id?: string;
  title: string;
  subtitle?: string;
  children: ReactNode;
  testId?: string;
};

/** Semantic section wrapper for public landing blocks. */
export function PublicSection({ id, title, subtitle, children, testId }: PublicSectionProps) {
  return (
    <section
      id={id}
      className="scroll-mt-20 py-10 sm:py-14"
      aria-labelledby={id ? `${id}-heading` : undefined}
      data-testid={testId}
    >
      <div className="mx-auto max-w-4xl">
        <h2
          id={id ? `${id}-heading` : undefined}
          className="text-balance text-xl font-semibold tracking-tight sm:text-2xl"
          style={{ color: "var(--ms-text-primary)" }}
        >
          {title}
        </h2>
        {subtitle ? (
          <p
            className="mt-3 max-w-3xl text-pretty text-sm leading-relaxed sm:text-base"
            style={{ color: "var(--ms-text-secondary)" }}
          >
            {subtitle}
          </p>
        ) : null}
        <div className="mt-8">{children}</div>
      </div>
    </section>
  );
}
