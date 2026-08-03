"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/auth-context";

type Props = {
  children: React.ReactNode;
};

/**
 * UX-only guard. Server-side API auth + ownership remain authoritative.
 */
export function RequireAuth({ children }: Props) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (loading) return;
    if (!user) {
      const next = encodeURIComponent(pathname || "/workspace");
      router.replace(`/login?next=${next}`);
    }
  }, [loading, user, router, pathname]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm" style={{ color: "var(--ms-text-secondary)" }}>
        Проверка сессии…
      </div>
    );
  }
  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm" style={{ color: "var(--ms-text-secondary)" }}>
        Перенаправление на вход…
      </div>
    );
  }
  return <>{children}</>;
}
