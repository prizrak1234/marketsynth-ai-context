"use client";

import { IntakeDraftProvider } from "@/components/project-intake/intake-draft-context";

/**
 * Project intake wizard layout — local draft provider for all /new steps.
 */
export default function ProjectIntakeLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return <IntakeDraftProvider>{children}</IntakeDraftProvider>;
}
