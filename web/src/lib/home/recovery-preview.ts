"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/auth-context";

/** Owner-only Recovery acceptance preview — not indexed, not commercial Home. */
export const RECOVERY_PREVIEW_R3_PATH = "/workspace/recovery-preview/r3";

export function isRecoveryPreviewRole(role: string | null | undefined): boolean {
  return role === "owner" || role === "admin";
}

/** Redirect non-owner roles away from recovery preview routes. */
export function useRecoveryPreviewAccess(): { allowed: boolean; loading: boolean } {
  const { user, loading } = useAuth();
  const router = useRouter();
  const allowed = isRecoveryPreviewRole(user?.role);

  useEffect(() => {
    if (loading) return;
    if (!allowed) router.replace("/workspace");
  }, [loading, allowed, router]);

  return { allowed, loading };
}
