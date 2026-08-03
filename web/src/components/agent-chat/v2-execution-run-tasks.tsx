"use client";

import { Button } from "@/components/ui/button";
import type { MarketingPlanExecutionRun } from "@/lib/api/types/marketing-plan-execution";
import type { MarketingSpecialistOutput } from "@/lib/api/types/marketing-specialist-outputs";
import {
  PIPELINE_GROUPS,
  firstMissingDependencyMessage,
  isExecutableSpecialist,
  specialistDisplayName,
} from "@/lib/marketing/specialist-pipelines";

type TaskSnapshot = MarketingPlanExecutionRun["task_snapshots"][number];

type V2ExecutionRunTasksProps = {
  run: MarketingPlanExecutionRun;
  outputByTask: Map<number, MarketingSpecialistOutput>;
  busy: boolean;
  onExecute: (taskIndex: number) => void;
  onPlaceholder: (taskIndex: number) => void;
};

function completedSpecialists(
  run: MarketingPlanExecutionRun,
  outputByTask: Map<number, MarketingSpecialistOutput>,
): Set<string> {
  const completed = new Set<string>();
  for (const task of run.task_snapshots) {
    if (task.status === "specialist_completed") {
      completed.add(task.specialist);
    }
  }
  for (const output of outputByTask.values()) {
    completed.add(output.specialist);
  }
  return completed;
}

function TaskRow({
  index,
  task,
  linked,
  runStatus,
  completed,
  busy,
  onExecute,
  onPlaceholder,
}: {
  index: number;
  task: TaskSnapshot;
  linked: MarketingSpecialistOutput | undefined;
  runStatus: MarketingPlanExecutionRun["status"];
  completed: Set<string>;
  busy: boolean;
  onExecute: (taskIndex: number) => void;
  onPlaceholder: (taskIndex: number) => void;
}) {
  const executable = isExecutableSpecialist(task.specialist);
  const missingMessage =
    runStatus === "running" && !linked
      ? firstMissingDependencyMessage(task.specialist, completed)
      : null;
  const canExecute =
    executable && runStatus === "running" && !linked && missingMessage === null;

  return (
    <li className="rounded border border-border/50 px-2 py-1.5">
      <p className="font-medium">
        #{index} {specialistDisplayName(task.specialist)} · {task.status}
      </p>
      {linked ? (
        <p className="text-[10px] text-muted-foreground">
          Output · {linked.output_type} · {linked.status}
        </p>
      ) : null}
      <p className="text-muted-foreground line-clamp-2">{task.objective}</p>
      {canExecute ? (
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="mt-1 h-5 text-[9px]"
          disabled={busy}
          onClick={() => onExecute(index)}
        >
          Execute {specialistDisplayName(task.specialist)}
        </Button>
      ) : null}
      {missingMessage ? (
        <p className="mt-1 text-[10px] text-muted-foreground">{missingMessage}</p>
      ) : null}
      {!executable && runStatus === "running" && !linked ? (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="mt-1 h-5 text-[9px]"
          disabled={busy}
          onClick={() => onPlaceholder(index)}
        >
          Create placeholder output
        </Button>
      ) : null}
      {task.safe_notes ? (
        <p className="mt-0.5 line-clamp-3 text-muted-foreground">{task.safe_notes}</p>
      ) : null}
    </li>
  );
}

export function V2ExecutionRunTasks({
  run,
  outputByTask,
  busy,
  onExecute,
  onPlaceholder,
}: V2ExecutionRunTasksProps) {
  const completed = completedSpecialists(run, outputByTask);
  const tasksBySpecialist = new Map(
    run.task_snapshots.map((task, index) => [task.specialist, { task, index }]),
  );

  return (
    <div className="space-y-3">
      <p className="text-[10px] font-medium text-amber-700 dark:text-amber-400">
        14-role department: execute specialists manually while the run is running. Frozen
        pipeline unchanged; v2 roles use separate dependency matrix.
      </p>
      {PIPELINE_GROUPS.map((group) => {
        const groupTasks = group.specialists
          .map((slug) => tasksBySpecialist.get(slug))
          .filter((entry): entry is { task: TaskSnapshot; index: number } => Boolean(entry));
        if (!groupTasks.length) return null;
        return (
          <div key={group.id}>
            <p className="text-[10px] font-semibold text-foreground">{group.label}</p>
            <ul className="mt-1 flex flex-col gap-1.5">
              {groupTasks.map(({ task, index }) => (
                <TaskRow
                  key={`${run.id}-${group.id}-${index}`}
                  index={index}
                  task={task}
                  linked={outputByTask.get(index)}
                  runStatus={run.status}
                  completed={completed}
                  busy={busy}
                  onExecute={onExecute}
                  onPlaceholder={onPlaceholder}
                />
              ))}
            </ul>
          </div>
        );
      })}
      {run.task_snapshots
        .map((task, index) => ({ task, index }))
        .filter(({ task }) => !PIPELINE_GROUPS.some((g) => (g.specialists as readonly string[]).includes(task.specialist)))
        .map(({ task, index }) => (
          <ul key={`${run.id}-other-${index}`} className="flex flex-col gap-1.5">
            <TaskRow
              index={index}
              task={task}
              linked={outputByTask.get(index)}
              runStatus={run.status}
              completed={completed}
              busy={busy}
              onExecute={onExecute}
              onPlaceholder={onPlaceholder}
            />
          </ul>
        ))}
    </div>
  );
}
