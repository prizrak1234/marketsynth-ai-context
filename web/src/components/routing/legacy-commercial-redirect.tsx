"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { canBypassCommercialSurfaceFreeze } from "@/lib/home/developer-mode";
import {
  CANONICAL_COMMERCIAL_ROUTES,
  resolveLegacyCommercialRedirect,
} from "@/lib/routes/commercial-surface";

type LegacyCommercialRedirectProps = {
  children: React.ReactNode;
  featureKey?: string;
};

/** Client redirect for legacy commercial routes (developer mode bypass). */
export function LegacyCommercialRedirect({ children }: LegacyCommercialRedirectProps) {
  const router = useRouter();
  const allowed = canBypassCommercialSurfaceFreeze();

  useEffect(() => {
    if (allowed) return;
    const redirectTarget =
      resolveLegacyCommercialRedirect("/workspace/tasks") ??
      CANONICAL_COMMERCIAL_ROUTES.workspaceHome;
    router.replace(redirectTarget);
  }, [allowed, router]);

  if (!allowed) {
    return null;
  }

  return children;
}
