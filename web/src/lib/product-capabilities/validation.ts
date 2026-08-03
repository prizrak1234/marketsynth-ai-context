/**
 * Registry invariants + future module activation contract validation.
 */

import type {
  CapabilityRegistryValidationIssue,
  ProductCapability,
} from "./contracts";
import { PRODUCT_CAPABILITY_REGISTRY } from "./registry";

export type ActivationRequirement =
  | "journey_entry"
  | "ia_slot"
  | "working_route_or_panel"
  | "owner_approval"
  | "public_surface_class";

const ACTIVATION_REQUIREMENTS: readonly ActivationRequirement[] = [
  "journey_entry",
  "ia_slot",
  "working_route_or_panel",
  "owner_approval",
  "public_surface_class",
];

export function validateCapabilityActivation(
  capability: ProductCapability,
): CapabilityRegistryValidationIssue[] {
  if (capability.availability !== "available") return [];

  const issues: CapabilityRegistryValidationIssue[] = [];

  if (capability.journeyIds.length === 0) {
    issues.push({
      code: "activation.missing_journey",
      capabilityId: capability.id,
      message: "Available capability must reference at least one journey stage.",
    });
  }

  if (capability.iaScreenIds.length === 0) {
    issues.push({
      code: "activation.missing_ia",
      capabilityId: capability.id,
      message: "Available capability must reference at least one IA screen id.",
    });
  }

  const hasRouteOrPanel =
    Boolean(capability.route) ||
    (capability.entryAction === "panel" && capability.requiresProject);
  if (!hasRouteOrPanel) {
    issues.push({
      code: "activation.missing_route",
      capabilityId: capability.id,
      message: "Available capability must define a route or project panel entry.",
    });
  }

  if (capability.publicVisible && capability.ownerApproved !== true) {
    issues.push({
      code: "activation.missing_owner_approval",
      capabilityId: capability.id,
      message: "Public available capability requires ownerApproved=true.",
    });
  }

  if (capability.publicVisible && capability.surfaceClass !== "CANONICAL_PUBLIC") {
    issues.push({
      code: "activation.invalid_surface_class",
      capabilityId: capability.id,
      message: "Public available capability must use CANONICAL_PUBLIC surface class.",
    });
  }

  return issues;
}

function detectCycles(
  byId: Map<string, ProductCapability>,
): CapabilityRegistryValidationIssue[] {
  const issues: CapabilityRegistryValidationIssue[] = [];

  for (const capability of byId.values()) {
    const visited = new Set<string>();
    let current: ProductCapability | undefined = capability;
    while (current?.parentId) {
      if (visited.has(current.id)) {
        issues.push({
          code: "hierarchy.circular",
          capabilityId: capability.id,
          message: `Circular parentId chain detected for ${capability.id}.`,
        });
        break;
      }
      visited.add(current.id);
      current = byId.get(current.parentId);
    }
  }

  return issues;
}

export function validateCapabilityRegistry(): CapabilityRegistryValidationIssue[] {
  const issues: CapabilityRegistryValidationIssue[] = [];
  const byId = new Map(PRODUCT_CAPABILITY_REGISTRY.map((cap) => [cap.id, cap]));
  const routeOwners = new Map<string, string>();

  for (const capability of PRODUCT_CAPABILITY_REGISTRY) {
    if (!capability.labelKey.trim()) {
      issues.push({
        code: "label.missing",
        capabilityId: capability.id,
        message: "Capability labelKey is required.",
      });
    }

    if (capability.parentId && !byId.has(capability.parentId)) {
      issues.push({
        code: "hierarchy.orphan_parent",
        capabilityId: capability.id,
        message: `Unknown parentId ${capability.parentId}.`,
      });
    }

    if (
      capability.availability === "available" &&
      capability.publicVisible &&
      capability.surfaceClass === "CANONICAL_PUBLIC" &&
      capability.entryAction === "route" &&
      !capability.route
    ) {
      issues.push({
        code: "route.missing_public_available",
        capabilityId: capability.id,
        message: "Public available route capability must define route.",
      });
    }

    if (
      (capability.reserved || capability.availability === "reserved") &&
      capability.publicVisible
    ) {
      issues.push({
        code: "visibility.reserved_public",
        capabilityId: capability.id,
        message: "Reserved capability must not be publicVisible.",
      });
    }

    if (
      capability.availability === "internal" &&
      capability.publicVisible
    ) {
      issues.push({
        code: "visibility.internal_public",
        capabilityId: capability.id,
        message: "Internal capability must not be publicVisible.",
      });
    }

    if (capability.route) {
      const owner = routeOwners.get(capability.route);
      if (
        owner &&
        owner !== capability.id &&
        capability.surfaceClass !== "REDIRECT"
      ) {
        issues.push({
          code: "route.duplicate",
          capabilityId: capability.id,
          message: `Route ${capability.route} already owned by ${owner}.`,
        });
      } else if (capability.surfaceClass !== "REDIRECT") {
        routeOwners.set(capability.route, capability.id);
      }
    }

    issues.push(...validateCapabilityActivation(capability));
  }

  const ids = PRODUCT_CAPABILITY_REGISTRY.map((cap) => cap.id);
  const duplicateIds = ids.filter((id, index) => ids.indexOf(id) !== index);
  for (const duplicateId of new Set(duplicateIds)) {
    issues.push({
      code: "id.duplicate",
      capabilityId: duplicateId,
      message: `Duplicate capability id ${duplicateId}.`,
    });
  }

  issues.push(...detectCycles(byId));

  return issues;
}

export function assertValidCapabilityRegistry(): void {
  const issues = validateCapabilityRegistry();
  if (issues.length > 0) {
    const summary = issues.map((issue) => `${issue.code}:${issue.capabilityId}`).join(", ");
    throw new Error(`Invalid product capability registry: ${summary}`);
  }
}

export function getActivationRequirements(): readonly ActivationRequirement[] {
  return ACTIVATION_REQUIREMENTS;
}

export {
  ACTIVATION_REQUIREMENTS,
};
