"use client";

import { useEffect, useState } from "react";
import { getApiBaseUrl } from "@/lib/api/config";

export type ApiAvailability = "checking" | "ok" | "unavailable";

export function useApiAvailability(): {
  status: ApiAvailability;
  diagnostics: {
    apiBaseConfigured: boolean;
    authConfigured: boolean;
    statusCode?: number;
    requestId?: string;
  };
} {
  const [status, setStatus] = useState<ApiAvailability>("checking");
  const [diagnostics, setDiagnostics] = useState({
    apiBaseConfigured: Boolean(getApiBaseUrl()),
    authConfigured: true,
    statusCode: undefined as number | undefined,
    requestId: undefined as string | undefined,
  });

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch(`${getApiBaseUrl()}/health/live`, {
          credentials: "include",
          cache: "no-store",
        });
        const requestId = res.headers.get("x-request-id") ?? undefined;
        if (cancelled) return;
        setDiagnostics((d) => ({
          ...d,
          statusCode: res.status,
          requestId,
          authConfigured: res.status !== 401,
        }));
        setStatus(res.ok ? "ok" : "unavailable");
      } catch {
        if (!cancelled) setStatus("unavailable");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return { status, diagnostics };
}
