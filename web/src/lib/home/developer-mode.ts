/** Developer Workspace toggle — off by default. Service console, not Commercial Home. */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { isDeveloperEnvironmentAllowed } from "@/lib/home/developer-environment";

export const HOME_DEVELOPER_MODE_KEY = "marketsynth.home.developer_mode.v1";

/**
 * True when the client bundle targets a non-production environment (development/test).
 * Inlined at build time — localStorage cannot override this.
 */
export { isDeveloperEnvironmentAllowed } from "@/lib/home/developer-environment";

/** Raw localStorage preference — never use alone for route or authorization decisions. */
export function readHomeDeveloperModeLocalFlag(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(HOME_DEVELOPER_MODE_KEY) === "1";
  } catch {
    return false;
  }
}

/**
 * Effective developer/diagnostics mode: non-production environment AND explicit local flag.
 * In production builds this is always false regardless of localStorage.
 */
export function isHomeDeveloperMode(
  nodeEnv: string | undefined = process.env.NODE_ENV,
): boolean {
  if (!isDeveloperEnvironmentAllowed(nodeEnv)) return false;
  return readHomeDeveloperModeLocalFlag();
}

/** Route guards — legacy commercial bypass only in developer environment with local flag. */
export function canBypassCommercialSurfaceFreeze(
  nodeEnv: string | undefined = process.env.NODE_ENV,
): boolean {
  return isHomeDeveloperMode(nodeEnv);
}

export function setHomeDeveloperMode(on: boolean): void {
  if (typeof window === "undefined") return;
  try {
    if (on) window.localStorage.setItem(HOME_DEVELOPER_MODE_KEY, "1");
    else window.localStorage.removeItem(HOME_DEVELOPER_MODE_KEY);
  } catch {
    /* ignore */
  }
}

/** Redirect commercial users away from developer-only workspace routes. */
export function useCommercialPathGuard(): boolean {
  const router = useRouter();
  const allowed = canBypassCommercialSurfaceFreeze();

  useEffect(() => {
    if (!allowed) router.replace("/workspace");
  }, [allowed, router]);

  return allowed;
}
