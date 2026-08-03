"use client";

import { AuthProvider } from "@/lib/auth/auth-context";
import { RequireAuth } from "@/lib/auth/route-guard";
import { useAuth } from "@/lib/auth/auth-context";
import { LocaleProvider, useLocale } from "@/lib/i18n";

function SessionBar({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const { t } = useLocale();
  const who = user?.display_name || user?.email || "—";
  return (
    <div className="flex min-h-screen flex-col">
      <div
        className="flex items-center justify-between border-b px-4 py-2 text-xs"
        style={{
          borderColor: "var(--ms-border-default)",
          background: "var(--ms-bg-elevated)",
          color: "var(--ms-text-secondary)",
        }}
      >
        <span>{t("session.bar", { who })}</span>
        <button
          type="button"
          data-testid="logout-button"
          onClick={() =>
            void logout().then(() => {
              window.location.href = "/login";
            })
          }
          className="font-medium underline-offset-2 hover:underline"
          style={{ color: "var(--brand-blue-light)" }}
        >
          {t("session.logout")}
        </button>
      </div>
      <div className="min-h-0 flex-1">{children}</div>
    </div>
  );
}

export function WorkspaceAuthShell({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <LocaleProvider>
        <RequireAuth>
          <SessionBar>{children}</SessionBar>
        </RequireAuth>
      </LocaleProvider>
    </AuthProvider>
  );
}
