"use client";

import { PRODUCT_BRAND } from "@/lib/brand/product-brand";
import type { WorkspaceProject, WorkspaceUser } from "@/lib/workspace/types";

type Props = {
  project: WorkspaceProject | null;
  user: WorkspaceUser;
  onCreateProject?: () => void;
};

export function WorkspaceHeader({ project, user, onCreateProject }: Props) {
  return (
    <header
      className="flex flex-wrap items-center justify-between gap-4 border-b px-6 py-4"
      style={{
        borderColor: "var(--ms-border-default)",
        background: "color-mix(in srgb, var(--ms-bg-surface) 92%, transparent)",
      }}
    >
      <div className="min-w-0">
        <p
          className="text-[11px] font-semibold uppercase tracking-[0.22em]"
          style={{ color: "var(--ms-brand-secondary)" }}
        >
          {PRODUCT_BRAND.displayName}
        </p>
        <div className="mt-1 flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h1
            className="truncate text-lg font-semibold"
            style={{ color: "var(--ms-text-primary)" }}
          >
            {project?.name ?? "Нет активного проекта"}
          </h1>
          {project ? (
            <span
              className="rounded-full px-2.5 py-0.5 text-xs font-medium"
              style={{
                background: "color-mix(in srgb, var(--brand-blue) 18%, transparent)",
                color: "var(--brand-blue-light)",
              }}
            >
              {project.statusLabel}
            </span>
          ) : null}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={onCreateProject}
          className="rounded-md px-3 py-2 text-xs font-semibold"
          style={{
            background: "var(--ms-brand-primary)",
            color: "var(--ms-text-primary)",
          }}
        >
          Создать проект
        </button>
        <div className="text-right">
          <p className="text-sm font-medium" style={{ color: "var(--ms-text-primary)" }}>
            {user.displayName}
          </p>
          <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
            {user.roleLabel}
          </p>
        </div>
      </div>
    </header>
  );
}
