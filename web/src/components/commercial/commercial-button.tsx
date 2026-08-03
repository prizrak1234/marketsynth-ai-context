import Link from "next/link";
import type { MouseEvent, ReactNode } from "react";

type CommercialButtonProps = {
  children: ReactNode;
  href?: string;
  onClick?: (event: MouseEvent<HTMLAnchorElement | HTMLButtonElement>) => void;
  variant?: "primary" | "secondary";
  disabled?: boolean;
  type?: "button" | "submit";
  testId?: string;
  className?: string;
};

/** Primary/secondary actions on commercial surfaces (DESIGN.md §5). */
export function CommercialButton({
  children,
  href,
  onClick,
  variant = "primary",
  disabled = false,
  type = "button",
  testId,
  className = "",
}: CommercialButtonProps) {
  const base =
    "inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-semibold transition-opacity disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--ms-brand-primary)]";
  const styles =
    variant === "primary"
      ? {
          background: "var(--ms-brand-primary)",
          color: "var(--ms-text-on-brand)",
          border: "none",
        }
      : {
          background: "transparent",
          color: "var(--ms-text-primary)",
          border: "1px solid var(--ms-border-default)",
        };

  if (href && !disabled) {
    return (
      <Link
        href={href}
        onClick={onClick}
        className={`${base} ${className}`.trim()}
        style={styles}
        data-testid={testId}
      >
        {children}
      </Link>
    );
  }

  return (
    <button
      type={type}
      className={`${base} ${className}`.trim()}
      style={styles}
      disabled={disabled}
      onClick={onClick}
      data-testid={testId}
    >
      {children}
    </button>
  );
}
