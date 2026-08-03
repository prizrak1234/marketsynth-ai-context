import { PublicLandingView } from "@/components/brand/public-landing-view";
import { getLandingPageMetadata } from "@/lib/landing/landing-metadata";
import type { Metadata } from "next";

export const metadata: Metadata = getLandingPageMetadata("ru");

/**
 * Canonical public landing — PRODUCT-01.4 Slice F.
 * Server-rendered root route; no AppShell, no client-only redirect.
 */
export default function PublicLandingPage() {
  return <PublicLandingView />;
}
