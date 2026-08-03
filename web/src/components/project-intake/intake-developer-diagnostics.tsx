"use client";

import { useState } from "react";
import { isHomeDeveloperMode } from "@/lib/home/developer-mode";
import {
  LOCAL_ONLY_INTAKE_SECTIONS,
  PERSISTED_INTAKE_FIELDS,
} from "@/lib/integration/intake-project-mapping";
import { getIntegrationMode, integrationModeLabel } from "@/lib/integration/mode";
import type { ProjectIntakeDraft } from "@/lib/project-intake/types";

function DevLine({ label, value }: { label: string; value: string }) {
  return (
    <p className="font-mono text-xs leading-relaxed" style={{ color: "var(--ms-text-secondary)" }}>
      <span style={{ color: "var(--ms-text-muted)" }}>{label}: </span>
      {value.trim() ? value : "—"}
    </p>
  );
}

type Props = {
  draft: ProjectIntakeDraft;
  onReconcile?: () => void;
  reconcileBusy?: boolean;
  showReconcile?: boolean;
};

/** Collapsed developer diagnostics — never rendered in production commercial mode. */
export function IntakeDeveloperDiagnostics({
  draft,
  onReconcile,
  reconcileBusy = false,
  showReconcile = false,
}: Props) {
  const [open, setOpen] = useState(false);
  if (!isHomeDeveloperMode()) return null;

  const mode = getIntegrationMode();
  const sync = draft.backendSync;
  const brief = draft.briefSync;

  return (
    <section
      className="rounded-lg border"
      style={{ borderColor: "var(--ms-border-default)", background: "var(--ms-bg-surface)" }}
      data-testid="intake-developer-diagnostics"
    >
      <button
        type="button"
        className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium"
        style={{ color: "var(--ms-text-muted)" }}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span>Диагностика (developer mode)</span>
        <span aria-hidden>{open ? "▾" : "▸"}</span>
      </button>
      {open ? (
        <div className="space-y-2 border-t px-4 py-3" style={{ borderColor: "var(--ms-border-default)" }}>
          <DevLine label="Integration mode" value={integrationModeLabel(mode)} />
          <DevLine
            label="Backend Project ID"
            value={
              mode === "mock"
                ? "mock"
                : sync?.backendProjectId
                  ? `${sync.backendProjectId} · ${sync.backendSyncState ?? ""}`
                  : `local · ${sync?.backendSyncState ?? "local_only"}`
            }
          />
          <DevLine label="Local draft id" value={draft.id} />
          <DevLine
            label="Brief"
            value={
              brief?.backendBriefId
                ? `v${brief.backendBriefVersion} · ${brief.backendBriefStatus} · ${brief.briefSyncState}`
                : "not persisted"
            }
          />
          <DevLine
            label="Brief fingerprint"
            value={brief?.backendBriefFingerprint?.slice(0, 16) ?? "—"}
          />
          <DevLine label="Persisted fields" value={PERSISTED_INTAKE_FIELDS.join(", ")} />
          <DevLine label="Local-only" value={[...LOCAL_ONLY_INTAKE_SECTIONS, "currentStep"].join(", ")} />
          {sync?.lastSyncError ? <DevLine label="Project sync error" value={sync.lastSyncError} /> : null}
          {brief?.lastBriefSyncError ? <DevLine label="Brief sync error" value={brief.lastBriefSyncError} /> : null}
          {showReconcile && onReconcile ? (
            <button
              type="button"
              onClick={onReconcile}
              disabled={reconcileBusy}
              className="mt-2 rounded-md px-3 py-2 text-xs font-medium disabled:opacity-40"
              style={{
                background: "var(--ms-bg-elevated)",
                color: "var(--ms-text-secondary)",
                boxShadow: "inset 0 0 0 1px var(--ms-border-default)",
              }}
            >
              Сверить с backend
            </button>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
