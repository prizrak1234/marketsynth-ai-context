/**

 * RUNTIME-01E + PRODUCT-01.5 — commercial surface helpers backed by capability registry.

 */



import type { IntentNavigationTarget } from "@/lib/home/intent-navigation";

import type { CapabilityNavItem } from "@/lib/product-capabilities";

import {

  getPublicNavigationCapabilities,

  isHrefPubliclyNavVisible,

  resolveLegacyRedirectFromRegistry,

} from "@/lib/product-capabilities/selectors";

import {

  CANONICAL_COMMERCIAL_ROUTES,

  canonicalIntakeHref,

  loginNextHref,

  workspaceProjectHref,

} from "@/lib/routes/commercial-routes";



export { CANONICAL_COMMERCIAL_ROUTES, canonicalIntakeHref, loginNextHref, workspaceProjectHref };



export type CommercialSurfaceClass =

  | "CANONICAL_PUBLIC"

  | "INTERNAL_ONLY"

  | "LEGACY_HIDDEN"

  | "PLACEHOLDER"

  | "REDIRECT"

  | "REMOVE_FROM_NAVIGATION"

  | "RESERVED";



export type CommercialNavItem = {

  href: string;

  key: string;

  exact?: boolean;

  surfaceClass: CommercialSurfaceClass;

  capabilityId?: string;

};



function toCommercialNavItem(item: CapabilityNavItem): CommercialNavItem {

  return {

    href: item.href,

    key: item.key,

    exact: item.exact,

    surfaceClass: item.surfaceClass,

    capabilityId: item.capabilityId,

  };

}



/** Public sidebar entries — derived from capability registry (PRODUCT-01.5). */

export const PUBLIC_WORKSPACE_NAV: ReadonlyArray<CommercialNavItem> =

  getPublicNavigationCapabilities().map(toCommercialNavItem);



/** Frozen from public navigation — internal developer routes in registry. */

export const FROZEN_PUBLIC_NAV_HREFS: ReadonlyArray<string> = [

  "/workspace/review",

  "/workspace/assistant",

  "/workspace/channels",

  "/workspace/assets",

];



export const LEGACY_COMMERCIAL_REDIRECTS: Readonly<Record<string, string>> = {

  "/workspace/tasks": CANONICAL_COMMERCIAL_ROUTES.workspaceHome,

  "/workspace/research": CANONICAL_COMMERCIAL_ROUTES.workspaceHome,

  "/workspace/execution": CANONICAL_COMMERCIAL_ROUTES.workspaceHome,

};



export function isFrozenPublicNavHref(href: string): boolean {

  return FROZEN_PUBLIC_NAV_HREFS.includes(href);

}



export function resolveLegacyCommercialRedirect(pathname: string): string | null {

  const fromRegistry = resolveLegacyRedirectFromRegistry(pathname);

  if (fromRegistry) return fromRegistry;

  if (pathname in LEGACY_COMMERCIAL_REDIRECTS) {

    return LEGACY_COMMERCIAL_REDIRECTS[pathname] ?? null;

  }

  if (pathname.startsWith("/workspace/tasks")) {

    return CANONICAL_COMMERCIAL_ROUTES.workspaceHome;

  }

  return null;

}



export function isLegacyProjectPipelinePath(pathname: string): boolean {

  return /^\/workspace\/projects\/[^/]+\/(investigation|verdict|strategy|pivot|implementation|execution-package)(\/|$)/.test(

    pathname,

  );

}



export function projectIdFromLegacyPipelinePath(pathname: string): string | null {

  const match = pathname.match(/^\/workspace\/projects\/([^/]+)\//);

  return match?.[1] ?? null;

}



/** Map legacy BIV / idea intents to canonical 7-step intake (no inline short BIV). */

export function toCanonicalPublicNavigationTarget(

  target: IntentNavigationTarget,

): IntentNavigationTarget {

  if (target.kind === "biv") {

    return { kind: "canonical_intake", task: target.task, scenario: target.scenario };

  }

  return target;

}



export function isPublicWorkspaceNavVisible(
  href: string,
  options?: { developerMode?: boolean; nodeEnv?: string },
): boolean {
  return isHrefPubliclyNavVisible(href, {
    developerMode: options?.developerMode,
    // Default production so a lone developerMode flag cannot bypass the env gate in tests/CI.
    nodeEnv: options?.nodeEnv ?? "production",
    role: "owner",
  });
}


