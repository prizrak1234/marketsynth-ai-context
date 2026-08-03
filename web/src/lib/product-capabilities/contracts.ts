/**
 * PRODUCT-01.5 — executable product capability contract.
 * Maps approved IA + Journey Map to a machine-readable registry (not a security boundary).
 */

export type CapabilityAvailability =
  | "available"
  | "internal"
  | "planned"
  | "reserved"
  | "disabled";

export type CapabilitySurfaceClass =
  | "CANONICAL_PUBLIC"
  | "INTERNAL_ONLY"
  | "LEGACY_HIDDEN"
  | "REDIRECT"
  | "RESERVED";

export type CapabilityCategory =
  | "workspace"
  | "project"
  | "launch"
  | "settings";

export type CapabilityRole = "owner" | "manager" | "employee" | "team_member";

export type CapabilityEntryAction = "route" | "panel" | "redirect";

export type ProductCapability = {
  id: string;
  canonicalName: string;
  labelKey: string;
  descriptionKey?: string;
  parentId?: string;
  category: CapabilityCategory;
  surfaceClass: CapabilitySurfaceClass;
  availability: CapabilityAvailability;
  route?: string;
  redirectTarget?: string;
  entryAction: CapabilityEntryAction;
  allowedRoles: readonly CapabilityRole[];
  requiresProject?: boolean;
  requiresApproval?: boolean;
  publicVisible: boolean;
  developerVisible: boolean;
  reserved: boolean;
  dependencies?: readonly string[];
  journeyIds: readonly string[];
  iaScreenIds: readonly string[];
  /** Links home direction cards (developer intent catalog) to this capability. */
  homeIntentId?: string;
  navExact?: boolean;
  /** Owner-approved commercial activation — required before public `available`. */
  ownerApproved?: boolean;
};

export type CapabilityNavItem = {
  capabilityId: string;
  href: string;
  key: string;
  exact?: boolean;
  surfaceClass: CapabilitySurfaceClass;
};

export type CapabilityRegistryValidationIssue = {
  code: string;
  capabilityId?: string;
  message: string;
};
