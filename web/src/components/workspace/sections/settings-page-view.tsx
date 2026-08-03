"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { WorkspaceSectionShell } from "@/components/workspace/section-shell";
import { useAuth } from "@/lib/auth/auth-context";
import {
  canShowIntegrationModeSwitcher,
  getIntegrationMode,
  setIntegrationMode,
  type IntegrationMode,
} from "@/lib/integration/mode";
import {
  getTimezoneGroups,
  LOCALE_OPTIONS,
  useLocale,
  type AppLocale,
  type WorkspaceUiPrefs,
} from "@/lib/i18n";

export function SettingsPageView() {
  const { user, logout, loading } = useAuth();
  const router = useRouter();
  const { t, locale, setLocale, prefs, setPrefs } = useLocale();
  const [mode, setMode] = useState<IntegrationMode>("backend");
  const showMode = canShowIntegrationModeSwitcher(user?.role);
  const timezoneGroups = getTimezoneGroups();
  const timezoneKnown = timezoneGroups.some((g) =>
    g.zones.includes(prefs.timezone),
  );

  useEffect(() => {
    setMode(getIntegrationMode());
  }, []);

  async function onLogout() {
    await logout();
    router.replace("/login");
  }

  return (
    <WorkspaceSectionShell
      title={t("settings.title")}
      description={t("settings.description")}
      testId="workspace-settings-page"
    >
      <div className="max-w-2xl space-y-6 text-sm">
        <SectionCard testId="settings-profile" title={t("settings.profile")}>
          {loading ? (
            <p style={{ color: "var(--ms-text-muted)" }}>{t("common.loading")}</p>
          ) : (
            <dl className="space-y-1" style={{ color: "var(--ms-text-secondary)" }}>
              <Row label={t("settings.email")} value={user?.email || "—"} />
              <Row label={t("settings.displayName")} value={user?.display_name || "—"} />
              <Row
                label={t("settings.role")}
                value={user?.role || "—"}
                testId="settings-role"
              />
            </dl>
          )}
        </SectionCard>

        <SectionCard testId="settings-skills-link" title={locale === "en" ? "Skills" : "Навыки"}>
          <p style={{ color: "var(--ms-text-secondary)" }}>
            {locale === "en"
              ? "Copywriter, Wordstat, Avito and other product skills."
              : "Copywriter, Wordstat, Avito и другие навыки платформы."}
          </p>
          <Link
            href="/workspace/settings/skills"
            className="mt-2 inline-block underline"
            data-testid="settings-open-skills"
          >
            {locale === "en" ? "Open skills" : "Открыть навыки"}
          </Link>
        </SectionCard>

        <SectionCard testId="settings-language" title={t("settings.languageRegion")}>
          <label className="block">
            {t("settings.language")}
            <select
              className="mt-1 w-full rounded border px-2 py-2"
              style={{
                background: "var(--ms-bg-surface)",
                borderColor: "var(--ms-border-default)",
              }}
              value={locale}
              onChange={(e) => {
                const next = e.target.value;
                if (next === "ru" || next === "en") setLocale(next as AppLocale);
              }}
              data-testid="settings-locale"
            >
              {LOCALE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value} disabled={!opt.enabled}>
                  {opt.enabled ? opt.label : `${opt.label} · ${t("common.later")}`}
                </option>
              ))}
            </select>
          </label>
          <label className="mt-3 block">
            {t("settings.timezone")}
            <select
              className="mt-1 w-full rounded border px-2 py-2"
              style={{
                background: "var(--ms-bg-surface)",
                borderColor: "var(--ms-border-default)",
              }}
              value={prefs.timezone}
              onChange={(e) => setPrefs({ timezone: e.target.value })}
              data-testid="settings-timezone"
            >
              {!timezoneKnown ? (
                <option value={prefs.timezone}>{prefs.timezone}</option>
              ) : null}
              {timezoneGroups.map((group) => (
                <optgroup key={group.region} label={group.region}>
                  {group.zones.map((zone) => (
                    <option key={zone} value={zone}>
                      {zone}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </label>
          <label className="mt-3 block">
            {t("settings.dateFormat")}
            <select
              className="mt-1 w-full rounded border px-2 py-2"
              style={{
                background: "var(--ms-bg-surface)",
                borderColor: "var(--ms-border-default)",
              }}
              value={prefs.dateFormat}
              onChange={(e) =>
                setPrefs({ dateFormat: e.target.value as WorkspaceUiPrefs["dateFormat"] })
              }
            >
              <option value="locale">locale</option>
              <option value="iso">ISO</option>
            </select>
          </label>
          <label className="mt-3 block">
            {t("settings.timeFormat")}
            <select
              className="mt-1 w-full rounded border px-2 py-2"
              style={{
                background: "var(--ms-bg-surface)",
                borderColor: "var(--ms-border-default)",
              }}
              value={prefs.timeFormat}
              onChange={(e) =>
                setPrefs({ timeFormat: e.target.value as WorkspaceUiPrefs["timeFormat"] })
              }
            >
              <option value="24h">24h</option>
              <option value="12h">12h</option>
            </select>
          </label>
          <p className="mt-2 text-xs" style={{ color: "var(--ms-text-muted)" }}>
            {t("settings.savedLocal")}
          </p>
        </SectionCard>

        <SectionCard testId="settings-security" title={t("settings.security")}>
          <a href="/forgot-password" className="underline font-medium">
            {t("settings.changePassword")}
          </a>
          <p className="mt-3" style={{ color: "var(--ms-text-secondary)" }}>
            <strong>{t("settings.activeSessions")}</strong>
            <br />
            {t("settings.sessionsHint")}
          </p>
          <button
            type="button"
            onClick={() => void onLogout()}
            className="mt-3 rounded-md px-3 py-2 text-sm font-semibold"
            style={{
              background: "var(--ms-brand-primary)",
              color: "var(--ms-text-on-brand, #fff)",
            }}
            data-testid="settings-logout"
          >
            {t("settings.logout")}
          </button>
        </SectionCard>

        <SectionCard testId="settings-notifications" title={t("settings.notifications")}>
          <Toggle
            label={t("settings.notifyEmail")}
            checked={prefs.notifyEmail}
            onChange={(v) => setPrefs({ notifyEmail: v })}
          />
          <Toggle
            label={t("settings.notifyProject")}
            checked={prefs.notifyProject}
            onChange={(v) => setPrefs({ notifyProject: v })}
          />
          <Toggle
            label={t("settings.notifyVerdict")}
            checked={prefs.notifyVerdict}
            onChange={(v) => setPrefs({ notifyVerdict: v })}
          />
          <Toggle
            label={t("settings.notifySecurity")}
            checked={prefs.notifySecurity}
            onChange={(v) => setPrefs({ notifySecurity: v })}
          />
          <p className="mt-2 text-xs" style={{ color: "var(--ms-text-muted)" }}>
            {t("settings.notifyLater")}
          </p>
        </SectionCard>

        <SectionCard testId="settings-workspace" title={t("settings.workspacePrefs")}>
          <label className="block">
            {t("settings.defaultLanding")}
            <select
              className="mt-1 w-full rounded border px-2 py-2"
              style={{
                background: "var(--ms-bg-surface)",
                borderColor: "var(--ms-border-default)",
              }}
              value={prefs.defaultLanding}
              onChange={(e) =>
                setPrefs({
                  defaultLanding: e.target.value as WorkspaceUiPrefs["defaultLanding"],
                })
              }
            >
              <option value="/workspace">{t("nav.home")}</option>
              <option value="/workspace/projects">{t("nav.projects")}</option>
              <option value="/workspace/tasks">{t("nav.tasks")}</option>
            </select>
          </label>
          <label className="mt-3 block">
            {t("settings.density")}
            <select
              className="mt-1 w-full rounded border px-2 py-2"
              style={{
                background: "var(--ms-bg-surface)",
                borderColor: "var(--ms-border-default)",
              }}
              value={prefs.density}
              onChange={(e) =>
                setPrefs({ density: e.target.value as WorkspaceUiPrefs["density"] })
              }
            >
              <option value="comfortable">{t("settings.densityComfortable")}</option>
              <option value="compact">{t("settings.densityCompact")}</option>
            </select>
          </label>
          {showMode ? (
            <label className="mt-3 block" data-testid="settings-integration-mode">
              {t("settings.integrationMode")}
              <select
                className="mt-1 w-full rounded border px-2 py-2"
                style={{
                  background: "var(--ms-bg-surface)",
                  borderColor: "var(--ms-border-default)",
                }}
                value={mode}
                onChange={(e) => {
                  const next = e.target.value as IntegrationMode;
                  setIntegrationMode(next);
                  setMode(next);
                }}
              >
                <option value="backend">backend</option>
                <option value="hybrid">hybrid</option>
                <option value="mock">mock</option>
              </select>
            </label>
          ) : null}
        </SectionCard>

        <SectionCard testId="settings-account" title={t("settings.account")}>
          <p style={{ color: "var(--ms-text-secondary)" }}>{t("settings.accountHint")}</p>
        </SectionCard>
      </div>
    </WorkspaceSectionShell>
  );
}

function SectionCard({
  title,
  children,
  testId,
}: {
  title: string;
  children: React.ReactNode;
  testId: string;
}) {
  return (
    <section
      className="rounded-lg border px-4 py-4"
      style={{ borderColor: "var(--ms-border-default)", background: "var(--ms-bg-surface)" }}
      data-testid={testId}
    >
      <h2 className="font-medium">{title}</h2>
      <div className="mt-3 space-y-2">{children}</div>
    </section>
  );
}

function Row({
  label,
  value,
  testId,
}: {
  label: string;
  value: string;
  testId?: string;
}) {
  return (
    <div>
      <dt className="inline text-xs">{label}: </dt>
      <dd className="inline" data-testid={testId}>
        {value}
      </dd>
    </div>
  );
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-2">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span>{label}</span>
    </label>
  );
}
