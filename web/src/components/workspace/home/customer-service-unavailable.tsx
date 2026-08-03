"use client";

import { useLocale } from "@/lib/i18n";

type Props = {
  /** Dev-only expandable diagnostics */
  showDevDiagnostics?: boolean;
  diagnostics?: {
    apiBaseConfigured?: boolean;
    authConfigured?: boolean;
    statusCode?: number;
    requestId?: string;
  };
};

/** Customer-safe API unavailable banner — no env var names or secrets. */
export function CustomerServiceUnavailable({
  showDevDiagnostics = false,
  diagnostics,
}: Props) {
  const { t } = useLocale();

  return (
    <div
      role="alert"
      className="rounded-lg border px-4 py-4 text-sm"
      style={{
        borderColor: "color-mix(in srgb, var(--ms-danger, #b42318) 35%, transparent)",
        background: "color-mix(in srgb, var(--ms-danger, #b42318) 8%, transparent)",
      }}
      data-testid="customer-service-unavailable"
    >
      <p className="font-semibold">{t("intent.apiUnavailableTitle")}</p>
      <p className="mt-1 leading-relaxed" style={{ color: "var(--ms-text-secondary)" }}>
        {t("intent.apiUnavailableBody")}
      </p>
      {showDevDiagnostics && diagnostics ? (
        <details className="mt-3 text-xs" style={{ color: "var(--ms-text-muted)" }}>
          <summary>{t("intent.devDiagnostics")}</summary>
          <ul className="mt-2 space-y-1">
            <li>
              API base URL configured: {diagnostics.apiBaseConfigured ? "yes" : "no"}
            </li>
            <li>authentication configured: {diagnostics.authConfigured ? "yes" : "no"}</li>
            {diagnostics.statusCode != null ? (
              <li>request status code: {diagnostics.statusCode}</li>
            ) : null}
            {diagnostics.requestId ? <li>request ID: {diagnostics.requestId}</li> : null}
          </ul>
        </details>
      ) : null}
    </div>
  );
}
