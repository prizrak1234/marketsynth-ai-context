/**
 * Capability registry selectors — single filtering layer for UI and routes.
 */

import { isDeveloperEnvironmentAllowed } from "@/lib/home/developer-environment";
import type {
  CapabilityNavItem,
  CapabilityRole,
  ProductCapability,
} from "./contracts";
import { PRODUCT_CAPABILITY_REGISTRY } from "./registry";

export type CapabilityRouteContext = {
  projectId?: string;
  role?: CapabilityRole;
  developerMode?: boolean;
  nodeEnv?: string;
};

const PUBLIC_NAV_ORDER = [
  "workspace.home",
  "workspace.projects",
  "settings.general",
] as const;

function navOrderIndex(capabilityId: string): number {
  const index = PUBLIC_NAV_ORDER.indexOf(capabilityId as (typeof PUBLIC_NAV_ORDER)[number]);
  return index === -1 ? PUBLIC_NAV_ORDER.length : index;
}
const REGISTRY_BY_ID = new Map(
  PRODUCT_CAPABILITY_REGISTRY.map((capability) => [capability.id, capability]),
);

export function getCapability(id: string): ProductCapability | undefined {
  return REGISTRY_BY_ID.get(id);
}

export function getAllCapabilities(): readonly ProductCapability[] {
  return PRODUCT_CAPABILITY_REGISTRY;
}

function roleAllowed(
  capability: ProductCapability,
  role: CapabilityRole = "owner",
): boolean {
  return capability.allowedRoles.includes(role);
}

export function isCapabilityPubliclyAvailable(
  id: string,
  role: CapabilityRole = "owner",
): boolean {
  const capability = getCapability(id);
  if (!capability) return false;
  if (capability.availability !== "available") return false;
  if (!capability.publicVisible) return false;
  if (capability.surfaceClass !== "CANONICAL_PUBLIC") return false;
  if (!roleAllowed(capability, role)) return false;
  return true;
}

export function isDeveloperCapabilityVisible(
  id: string,
  options?: Pick<CapabilityRouteContext, "developerMode" | "nodeEnv" | "role">,
): boolean {
  const capability = getCapability(id);
  if (!capability) return false;
  if (capability.availability !== "internal") return false;
  if (!capability.developerVisible) return false;
  if (capability.surfaceClass !== "INTERNAL_ONLY") return false;
  const envAllowed = isDeveloperEnvironmentAllowed(options?.nodeEnv);
  if (!envAllowed) return false;
  if (!options?.developerMode) return false;
  return roleAllowed(capability, options?.role ?? "owner");
}

function toNavItem(capability: ProductCapability): CapabilityNavItem | null {
  if (!capability.route) return null;
  return {
    capabilityId: capability.id,
    href: capability.route,
    key: capability.labelKey,
    exact: capability.navExact,
    surfaceClass: capability.surfaceClass,
  };
}

export function getPublicNavigationCapabilities(
  role: CapabilityRole = "owner",
): CapabilityNavItem[] {
  return PRODUCT_CAPABILITY_REGISTRY.filter(
    (capability) =>
      capability.category === "workspace" || capability.category === "settings",
  )
    .filter((capability) => isCapabilityPubliclyAvailable(capability.id, role))
    .filter((capability) => capability.route && capability.entryAction === "route")
    .map(toNavItem)
    .filter((item): item is CapabilityNavItem => item !== null)
    .sort((a, b) => navOrderIndex(a.capabilityId) - navOrderIndex(b.capabilityId));
}

export function getDeveloperNavigationCapabilities(
  options: CapabilityRouteContext,
): CapabilityNavItem[] {
  return PRODUCT_CAPABILITY_REGISTRY.filter((capability) =>
    isDeveloperCapabilityVisible(capability.id, options),
  )
    .map(toNavItem)
    .filter((item): item is CapabilityNavItem => item !== null)
    .sort((a, b) => a.href.localeCompare(b.href));
}

export function getWorkspaceNavigationCapabilities(
  options: CapabilityRouteContext = {},
): CapabilityNavItem[] {
  const role = options.role ?? "owner";
  const publicItems = getPublicNavigationCapabilities(role);
  if (!options.developerMode) return publicItems;
  const devItems = getDeveloperNavigationCapabilities(options);
  const seen = new Set(publicItems.map((item) => item.href));
  return [
    ...publicItems,
    ...devItems.filter((item) => !seen.has(item.href)),
  ];
}

export function getProjectStageCapabilities(
  role: CapabilityRole = "owner",
): ProductCapability[] {
  return PRODUCT_CAPABILITY_REGISTRY.filter(
    (capability) => capability.category === "project" || capability.category === "launch",
  ).filter((capability) => {
    if (capability.availability === "available" && capability.publicVisible) {
      return roleAllowed(capability, role);
    }
    return false;
  });
}

export function getReservedCapabilities(): ProductCapability[] {
  return PRODUCT_CAPABILITY_REGISTRY.filter(
    (capability) => capability.reserved || capability.availability === "reserved",
  );
}

export function getDeveloperCapabilities(): ProductCapability[] {
  return PRODUCT_CAPABILITY_REGISTRY.filter(
    (capability) => capability.availability === "internal",
  );
}

export function getPublicHomeDirectionIntentIds(
  role: CapabilityRole = "owner",
): string[] {
  return PRODUCT_CAPABILITY_REGISTRY.filter(
    (capability) => capability.homeIntentId && isCapabilityPubliclyAvailable(capability.id, role),
  ).map((capability) => capability.homeIntentId as string);
}

export function resolveCapabilityRoute(
  id: string,
  context: CapabilityRouteContext = {},
): string | null {
  const capability = getCapability(id);
  if (!capability) return null;

  if (capability.entryAction === "redirect" && capability.redirectTarget) {
    return capability.redirectTarget;
  }

  if (capability.entryAction === "panel" && capability.requiresProject && context.projectId) {
    const params = new URLSearchParams({ project: context.projectId });
    return `/workspace?${params.toString()}`;
  }

  if (capability.route) {
    if (capability.requiresProject && context.projectId) {
      const url = new URL(capability.route, "http://local.invalid");
      url.searchParams.set("project", context.projectId);
      return `${url.pathname}${url.search}`;
    }
    return capability.route;
  }
  return null;
}

export function resolveLegacyRedirectFromRegistry(pathname: string): string | null {
  const redirectCapability = PRODUCT_CAPABILITY_REGISTRY.find(
    (capability) =>
      capability.surfaceClass === "REDIRECT" &&
      capability.route === pathname &&
      capability.redirectTarget,
  );
  if (redirectCapability?.redirectTarget) return redirectCapability.redirectTarget;
  if (pathname.startsWith("/workspace/tasks")) {
    return resolveCapabilityRoute("legacy.tasks");
  }
  return null;
}

export function isHrefPubliclyNavVisible(
  href: string,
  options?: CapabilityRouteContext,
): boolean {
  if (options?.developerMode && isDeveloperEnvironmentAllowed(options.nodeEnv)) {
    return getWorkspaceNavigationCapabilities(options).some((item) => item.href === href);
  }
  return getPublicNavigationCapabilities(options?.role).some((item) => item.href === href);
}

export function getCapabilityForHomeIntent(homeIntentId: string): ProductCapability | undefined {
  return PRODUCT_CAPABILITY_REGISTRY.find(
    (capability) => capability.homeIntentId === homeIntentId,
  );
}

export function isHomeIntentPubliclyAvailable(homeIntentId: string): boolean {
  const capability = getCapabilityForHomeIntent(homeIntentId);
  if (!capability) return false;
  return isCapabilityPubliclyAvailable(capability.id);
}
