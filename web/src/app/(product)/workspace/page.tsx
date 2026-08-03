import { Suspense } from "react";
import { WorkspaceHomeView } from "@/components/workspace/home/workspace-home-view";

export default function WorkspacePage() {
  return (
    <Suspense fallback={null}>
      <WorkspaceHomeView />
    </Suspense>
  );
}
