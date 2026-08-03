import { DeveloperWorkspaceRouteGuard } from "@/components/routing/developer-workspace-route-guard";
import { DeveloperWorkspaceView } from "@/components/workspace/developer/developer-workspace-view";

export default function DeveloperWorkspacePage() {
  return (
    <DeveloperWorkspaceRouteGuard>
      <DeveloperWorkspaceView />
    </DeveloperWorkspaceRouteGuard>
  );
}
