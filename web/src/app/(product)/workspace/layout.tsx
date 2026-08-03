import { WorkspaceAuthShell } from "@/components/auth/workspace-auth-shell";

/**
 * Product workspace — cookie session required (CPH.3).
 * Frontend guard is UX only; API ownership remains authoritative.
 */
export default function WorkspaceLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return <WorkspaceAuthShell>{children}</WorkspaceAuthShell>;
}
