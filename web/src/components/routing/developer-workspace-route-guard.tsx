"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { isDeveloperEnvironmentAllowed } from "@/lib/home/developer-mode";
import { CANONICAL_COMMERCIAL_ROUTES } from "@/lib/routes/commercial-routes";

/** Block /workspace/developer in production builds — environment-scoped, not localStorage. */
export function DeveloperWorkspaceRouteGuard({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const allowed = isDeveloperEnvironmentAllowed();

  useEffect(() => {
    if (!allowed) {
      router.replace(CANONICAL_COMMERCIAL_ROUTES.workspaceHome);
    }
  }, [allowed, router]);

  if (!allowed) {
    return null;
  }

  return children;
}
