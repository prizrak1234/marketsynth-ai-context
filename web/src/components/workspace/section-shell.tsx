"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { WorkspaceNav } from "@/components/workspace/workspace-nav";
import { BrandLogoMark } from "@/components/brand/brand-logo";
import { useLocale } from "@/lib/i18n";

type Props = {
  title: string;
  description?: string;
  children: ReactNode;
  actions?: ReactNode;
  testId?: string;
};

export function WorkspaceSectionShell({
  title,
  description,
  children,
  actions,
  testId,
}: Props) {
  const { t } = useLocale();
  return (
    <div
      className="flex min-h-screen flex-col md:flex-row"
      style={{
        background: "var(--ms-bg-canvas)",
        color: "var(--ms-text-primary)",
      }}
      data-testid={testId}
    >
      <WorkspaceNav />
      <main className="mx-auto flex w-full max-w-[1360px] min-w-0 flex-1 flex-col px-6 py-8 sm:px-8">
        <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <BrandLogoMark size={26} />
            <h1 className="mt-4 text-2xl font-semibold">{title}</h1>
            {description ? (
              <p
                className="mt-2 max-w-3xl text-sm"
                style={{ color: "var(--ms-text-secondary)" }}
              >
                {description}
              </p>
            ) : null}
          </div>
          {actions}
        </div>
        {children}
        <p className="mt-10 text-xs" style={{ color: "var(--ms-text-muted)" }}>
          <Link href="/workspace" className="underline">
            {t("common.backHome")}
          </Link>
        </p>
      </main>
    </div>
  );
}

export function SectionLoading({ label }: { label?: string }) {
  const { t } = useLocale();
  return (
    <p className="text-sm" style={{ color: "var(--ms-text-muted)" }} data-testid="section-loading">
      {label || t("common.loading")}
    </p>
  );
}

export function SectionEmpty({
  message,
  testId = "section-empty",
}: {
  message: string;
  testId?: string;
}) {
  return (
    <p
      className="rounded-lg border px-4 py-6 text-sm"
      style={{
        borderColor: "var(--ms-border-default)",
        background: "var(--ms-bg-elevated)",
        color: "var(--ms-text-secondary)",
      }}
      data-testid={testId}
    >
      {message}
    </p>
  );
}

export function SectionError({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  const { t } = useLocale();
  return (
    <div
      className="rounded-lg border px-4 py-4 text-sm"
      style={{
        borderColor: "var(--ms-border-default)",
        color: "var(--ms-text-secondary)",
      }}
      role="alert"
      data-testid="section-error"
    >
      <p>{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 text-sm font-medium underline"
          data-testid="section-retry"
        >
          {t("common.retry")}
        </button>
      ) : null}
    </div>
  );
}
