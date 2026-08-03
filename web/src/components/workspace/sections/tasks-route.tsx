"use client";

import { useSearchParams } from "next/navigation";
import { WorkspaceTaskFlowView } from "@/components/workspace/home/workspace-task-flow-view";
import { WorkspaceTasksPageView } from "@/components/workspace/sections/tasks-page-view";

/** List index by default; ?intent= preserves specialist task entry. */
export function WorkspaceTasksRoute() {
  const params = useSearchParams();
  const intent = params.get("intent");
  if (intent) return <WorkspaceTaskFlowView />;
  return <WorkspaceTasksPageView />;
}
