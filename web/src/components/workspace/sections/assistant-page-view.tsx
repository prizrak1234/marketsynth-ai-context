"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { HomeExecutionPanel } from "@/components/workspace/home/home-execution-panel";
import { WorkspaceNav } from "@/components/workspace/workspace-nav";
import { loadIntentTask } from "@/lib/home/intent-navigation";
import type { IntentCategory } from "@/lib/home/intent-routing";

function AssistantInner() {
  const params = useSearchParams();
  const stored = loadIntentTask();
  const taskParam = params.get("task") || "";
  const task = taskParam || stored?.task || "";
  const scenarioParam = params.get("scenario");
  const scenario = (scenarioParam || stored?.scenario || null) as IntentCategory | null;

  return (
    <div
      className="flex min-h-screen flex-col md:flex-row"
      style={{ background: "var(--ms-bg-canvas)", color: "var(--ms-text-primary)" }}
      data-testid="workspace-assistant"
    >
      <WorkspaceNav />
      <div className="min-w-0 flex-1 px-4 py-6 sm:px-8">
        <HomeExecutionPanel seedText={task} initialScenario={scenario} />
      </div>
    </div>
  );
}

export function WorkspaceAssistantView() {
  return (
    <Suspense fallback={<div className="p-8 text-sm">Загрузка…</div>}>
      <AssistantInner />
    </Suspense>
  );
}
