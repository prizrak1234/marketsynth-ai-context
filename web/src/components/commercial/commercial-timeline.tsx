import type { CommercialTimelineStage } from "./commercial-timeline-types";
import {
  commercialTimelineStageColor,
  commercialTimelineStageMark,
} from "./commercial-timeline-utils";

type CommercialTimelineProps = {
  stages: CommercialTimelineStage[];
  title?: string;
  working?: boolean;
  testId?: string;
  /** When embedded inside CommercialCard, omit outer border. */
  embedded?: boolean;
};

/** Research / workflow progress timeline (DESIGN.md §7.1). */
export function CommercialTimeline({
  stages,
  title,
  working = false,
  testId = "commercial-timeline",
  embedded = false,
}: CommercialTimelineProps) {
  return (
    <section
      className={embedded ? "space-y-3" : "space-y-3 rounded-xl border p-4"}
      style={
        embedded
          ? undefined
          : {
              borderColor: "var(--ms-border-default)",
              background: "var(--ms-bg-surface)",
            }
      }
      data-testid={testId}
      aria-busy={working || undefined}
    >
      {title ? (
        <h3
          className="text-sm font-semibold uppercase tracking-wide"
          style={{ color: "var(--ms-text-muted)" }}
        >
          {title}
        </h3>
      ) : null}
      <ol className="space-y-2">
        {stages.map((stage) => (
          <li
            key={stage.id}
            className="flex items-center gap-2 text-sm"
            style={{ color: commercialTimelineStageColor(stage.status) }}
            data-testid={`commercial-timeline-stage-${stage.id}`}
            data-status={stage.status}
          >
            <span aria-hidden className="w-4 text-center font-semibold">
              {commercialTimelineStageMark(stage.status)}
            </span>
            <span>{stage.label}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}

export type { CommercialTimelineStage } from "./commercial-timeline-types";
