/**
 * Public landing CTA resolution — Capability Registry backed (PRODUCT-01.4 Slice F).
 */

import {
  getCapability,
  isCapabilityPubliclyAvailable,
  resolveCapabilityRoute,
} from "@/lib/product-capabilities/selectors";
import { loginNextHref } from "@/lib/routes/commercial-routes";

/** Canonical intake capability for public landing primary CTA. */
export const LANDING_INTAKE_CAPABILITY_ID = "project.intake";

export function getLandingIntakeCapabilityId(): string | null {
  if (!isCapabilityPubliclyAvailable(LANDING_INTAKE_CAPABILITY_ID)) return null;
  return LANDING_INTAKE_CAPABILITY_ID;
}

export function resolveLandingIntakeHref(): string | null {
  if (!getLandingIntakeCapabilityId()) return null;
  return resolveCapabilityRoute(LANDING_INTAKE_CAPABILITY_ID);
}

export function resolveLandingPrimaryCtaHref(authenticated: boolean): string | null {
  const intakeHref = resolveLandingIntakeHref();
  if (!intakeHref) return null;
  return authenticated ? intakeHref : loginNextHref(intakeHref);
}

/** Reject open redirects — internal paths only. */
export function isSafeInternalNext(path: string): boolean {
  return path.startsWith("/") && !path.startsWith("//");
}

export function resolveLandingLoginNextHref(): string | null {
  const intakeHref = resolveLandingIntakeHref();
  if (!intakeHref || !isSafeInternalNext(intakeHref)) return null;
  return loginNextHref(intakeHref);
}

export function getReservedLandingCapabilityNames(): string[] {
  return [
    "Launch",
    "Analytics",
    "Billing",
    "Strategy",
    "Content",
    "Visuals",
    "Publication",
    "CRM",
  ];
}

export function isLandingCapabilityActionAvailable(capabilityId: string): boolean {
  const capability = getCapability(capabilityId);
  if (!capability) return false;
  return isCapabilityPubliclyAvailable(capabilityId);
}
