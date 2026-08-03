"use client";

import type { PipelineStage, PipelineStageId } from "@/lib/workspace/types";

type Props = {
  stages: PipelineStage[];
  activeStage: PipelineStageId;
};

export function InvestigationPipeline({ stages, activeStage }: Props) {
  return (
    <section
      className="rounded-xl border p-5"
      style={{
        borderColor: "var(--ms-border-default)",
        background: "var(--ms-bg-surface)",
      }}
    >
      <h2
        className="text-sm font-semibold uppercase tracking-[0.14em]"
        style={{ color: "var(--ms-brand-secondary)" }}
      >
        Investigation Pipeline
      </h2>
      <p className="mt-1 text-sm" style={{ color: "var(--ms-text-muted)" }}>
        Этапы работы агентства над идеей
      </p>

      <ol className="mt-5 flex flex-col gap-0">
        {stages.map((stage, index) => {
          const active = stage.id === activeStage;
          const past =
            stages.findIndex((s) => s.id === activeStage) > index;
          return (
            <li key={stage.id} className="flex flex-col items-start">
              <div className="flex items-center gap-3">
                <span
                  className="flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold"
                  style={
                    active
                      ? {
                          background: "var(--ms-brand-primary)",
                          color: "var(--ms-text-primary)",
                          boxShadow:
                            "0 0 0 2px color-mix(in srgb, var(--brand-blue-light) 40%, transparent)",
                        }
                      : past
                        ? {
                            background:
                              "color-mix(in srgb, var(--ms-status-success) 25%, transparent)",
                            color: "var(--ms-status-success)",
                          }
                        : {
                            background: "var(--ms-bg-elevated)",
                            color: "var(--ms-text-muted)",
                          }
                  }
                >
                  {index + 1}
                </span>
                <span
                  className="text-sm font-medium"
                  style={{
                    color: active
                      ? "var(--ms-text-primary)"
                      : past
                        ? "var(--ms-text-secondary)"
                        : "var(--ms-text-muted)",
                  }}
                >
                  {stage.label}
                </span>
              </div>
              {index < stages.length - 1 ? (
                <div
                  className="ml-3.5 h-4 w-px"
                  style={{ background: "var(--ms-border-default)" }}
                  aria-hidden
                />
              ) : null}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
