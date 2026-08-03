"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { PRODUCT_BRAND } from "@/lib/brand/product-brand";
import { useAuth } from "@/lib/auth/auth-context";
import {
  acceptInvite,
  fetchInviteStatus,
  type InvitePublicState,
} from "@/lib/auth/invite-client";
import {
  extractInviteToken,
  inviteStateMessage,
  type InviteUiState,
} from "@/lib/auth/invite-token";
import { resolveWorkspaceEntryHref } from "@/lib/routes/workspace-entry";

const CANONICAL_HOST = "localhost";
const CANONICAL_PORT = "3000";

function useCanonicalLocalHostRedirect() {
  useEffect(() => {
    if (typeof window === "undefined") return;
    const { hostname, port, protocol, pathname, search, hash } = window.location;
    if (hostname === "127.0.0.1" && (port === CANONICAL_PORT || port === "")) {
      const targetPort = port || CANONICAL_PORT;
      const next = `${protocol}//${CANONICAL_HOST}:${targetPort}${pathname}${search}${hash}`;
      window.location.replace(next);
    }
  }, []);
}

export function ActivateInviteForm() {
  useCanonicalLocalHostRedirect();
  const router = useRouter();
  const params = useSearchParams();
  const queryToken = useMemo(
    () => extractInviteToken(params.get("token") || "") || "",
    [params],
  );
  const { refresh } = useAuth();

  const [activeToken, setActiveToken] = useState(queryToken);
  const [pasteValue, setPasteValue] = useState("");
  const [loading, setLoading] = useState(Boolean(queryToken));
  const [state, setState] = useState<InviteUiState>(
    queryToken ? "loading" : "token_missing",
  );
  const [email, setEmail] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [acceptNotice, setAcceptNotice] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const applyTokenToUrl = useCallback(
    (token: string) => {
      const url = new URL(window.location.href);
      url.searchParams.set("token", token);
      // Preserve path; use replace so refresh keeps token without history clutter.
      router.replace(`${url.pathname}?${url.searchParams.toString()}`);
    },
    [router],
  );

  const loadStatus = useCallback(async (token: string) => {
    setLoading(true);
    setError(null);
    setState("loading");
    const res = await fetchInviteStatus(token);
    if (!res.ok) {
      setState(res.state as InviteUiState);
      setLoading(false);
      return;
    }
    const next = res.status.state as InvitePublicState;
    setState(next as InviteUiState);
    setEmail(res.status.email);
    if (res.status.email) {
      setDisplayName(res.status.email.split("@")[0] || "");
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    const fromQuery = extractInviteToken(params.get("token") || "") || "";
    if (!fromQuery) {
      setActiveToken("");
      setLoading(false);
      setState("token_missing");
      return;
    }
    setActiveToken(fromQuery);
    void loadStatus(fromQuery);
  }, [params, loadStatus]);

  function onPasteSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const token = extractInviteToken(pasteValue);
    if (!token) {
      setError("Вставьте полный URL с ?token=… или код, начинающийся с mpi_.");
      setState("token_missing");
      return;
    }
    setActiveToken(token);
    applyTokenToUrl(token);
    void loadStatus(token);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!activeToken) return;
    setSubmitting(true);
    const res = await acceptInvite({
      token: activeToken,
      displayName,
      password,
      passwordConfirm,
      acceptPilotNotice: acceptNotice,
    });
    setSubmitting(false);
    if (!res.ok) {
      setError(res.error.message);
      if (res.error.code === "account_exists") setState("account_exists");
      else if (res.error.code === "invite_used") setState("already_used");
      else if (res.error.code === "invite_expired") setState("expired");
      else if (res.error.code === "invite_revoked") setState("revoked");
      else if (res.error.code === "invalid_token") setState("invalid");
      else if (res.error.code === "backend_unavailable") setState("backend_unavailable");
      return;
    }
    // Drop token from address bar after success; land on commercial entry.
    await refresh();
    const dest = await resolveWorkspaceEntryHref();
    router.replace(dest);
  }

  const blocked =
    !loading &&
    state !== "valid" &&
    state !== "token_missing" &&
    state !== "loading";

  return (
    <div
      className="flex min-h-screen items-center justify-center px-4"
      style={{ background: "var(--ms-bg-canvas)", color: "var(--ms-text-primary)" }}
    >
      <div className="w-full max-w-md space-y-6">
        <header>
          <p
            className="text-[11px] font-semibold uppercase tracking-[0.22em]"
            style={{ color: "var(--ms-brand-secondary)" }}
          >
            {PRODUCT_BRAND.displayName}
          </p>
          <h1 className="mt-2 text-2xl font-semibold">Активация приглашения</h1>
          <p className="mt-1 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
            Регистрация только по одноразовому приглашению оператора. Публичная
            регистрация отключена.
          </p>
        </header>

        {!loading && state === "token_missing" ? (
          <form
            onSubmit={onPasteSubmit}
            className="space-y-4"
            noValidate
            data-testid="invite-token-entry"
            data-invite-state="token_missing"
          >
            <p className="text-sm" style={{ color: "var(--ms-text-secondary)" }}>
              У вас должна быть одноразовая ссылка или код от оператора пилота.
              Вставьте их ниже — страница сама не создаёт приглашение.
            </p>
            <div>
              <label htmlFor="invite-token-input" className="block text-sm font-medium">
                Код или полная ссылка приглашения
              </label>
              <textarea
                id="invite-token-input"
                rows={3}
                value={pasteValue}
                onChange={(e) => {
                  setError(null);
                  setPasteValue(e.target.value);
                }}
                placeholder="http://localhost:3000/activate-invite?token=mpi_… или mpi_…"
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
                style={{
                  borderColor: "var(--ms-border-default)",
                  background: "var(--ms-bg-surface)",
                }}
                data-testid="invite-token-input"
              />
            </div>
            {error ? (
              <p
                className="text-sm"
                style={{ color: "var(--ms-status-danger)" }}
                role="alert"
                data-testid="invite-token-entry-error"
              >
                {error}
              </p>
            ) : null}
            <button
              type="submit"
              data-testid="invite-token-continue"
              className="w-full rounded-md px-4 py-2.5 text-sm font-semibold"
              style={{
                background: "var(--ms-brand-primary)",
                color: "var(--ms-text-on-brand, #fff)",
              }}
            >
              Продолжить
            </button>
          </form>
        ) : null}

        {loading ? (
          <p className="text-sm" data-testid="invite-loading">
            Проверка приглашения…
          </p>
        ) : null}

        {blocked ? (
          <div
            className="space-y-4"
            data-testid="invite-blocked"
            data-invite-state={state}
          >
            <p
              className="text-sm"
              style={{ color: "var(--ms-status-danger)" }}
              role="alert"
            >
              {inviteStateMessage(state)}
            </p>
            {(state === "already_used" || state === "account_exists") && (
              <a
                href="/login"
                className="inline-block text-sm font-semibold underline"
                data-testid="invite-go-login"
              >
                Перейти ко входу
              </a>
            )}
            {(state === "invalid" ||
              state === "expired" ||
              state === "revoked") && (
              <button
                type="button"
                className="text-sm font-semibold underline"
                data-testid="invite-retry-token"
                onClick={() => {
                  setState("token_missing");
                  setActiveToken("");
                  setPasteValue("");
                  setError(null);
                  router.replace("/activate-invite");
                }}
              >
                Ввести другой код или ссылку
              </button>
            )}
          </div>
        ) : null}

        {!loading && state === "valid" ? (
          <form onSubmit={onSubmit} className="space-y-4" noValidate data-testid="invite-form">
            <div>
              <label htmlFor="invite-email" className="block text-sm font-medium">
                Email приглашения
              </label>
              <input
                id="invite-email"
                type="email"
                readOnly
                value={email || ""}
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm opacity-90"
                style={{
                  borderColor: "var(--ms-border-default)",
                  background: "var(--ms-bg-surface)",
                }}
                data-testid="invite-email"
              />
            </div>
            <div>
              <label htmlFor="invite-display-name" className="block text-sm font-medium">
                Отображаемое имя
              </label>
              <input
                id="invite-display-name"
                required
                maxLength={255}
                value={displayName}
                onChange={(e) => {
                  setError(null);
                  setDisplayName(e.target.value);
                }}
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
                style={{
                  borderColor: "var(--ms-border-default)",
                  background: "var(--ms-bg-surface)",
                }}
                data-testid="invite-display-name"
              />
            </div>
            <div>
              <label htmlFor="invite-password" className="block text-sm font-medium">
                Пароль
              </label>
              <input
                id="invite-password"
                type="password"
                autoComplete="new-password"
                required
                minLength={10}
                value={password}
                onChange={(e) => {
                  setError(null);
                  setPassword(e.target.value);
                }}
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
                style={{
                  borderColor: "var(--ms-border-default)",
                  background: "var(--ms-bg-surface)",
                }}
                data-testid="invite-password"
              />
            </div>
            <div>
              <label htmlFor="invite-password-confirm" className="block text-sm font-medium">
                Подтверждение пароля
              </label>
              <input
                id="invite-password-confirm"
                type="password"
                autoComplete="new-password"
                required
                minLength={10}
                value={passwordConfirm}
                onChange={(e) => {
                  setError(null);
                  setPasswordConfirm(e.target.value);
                }}
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
                style={{
                  borderColor: "var(--ms-border-default)",
                  background: "var(--ms-bg-surface)",
                }}
                data-testid="invite-password-confirm"
              />
            </div>
            <label
              className="flex items-start gap-2 text-sm"
              style={{ color: "var(--ms-text-secondary)" }}
            >
              <input
                type="checkbox"
                checked={acceptNotice}
                onChange={(e) => {
                  setError(null);
                  setAcceptNotice(e.target.checked);
                }}
                className="mt-1"
                data-testid="invite-notice"
              />
              <span>
                Понимаю, что это контролируемый пилот Marketsynth: данные обрабатываются для
                тестирования продукта, исполнение рекламы и публичная регистрация отключены.
              </span>
            </label>
            {error ? (
              <p
                className="text-sm"
                style={{ color: "var(--ms-status-danger)" }}
                role="alert"
                data-testid="invite-error"
              >
                {error}
              </p>
            ) : null}
            <button
              type="submit"
              disabled={submitting}
              data-testid="invite-submit"
              aria-busy={submitting}
              className="w-full rounded-md px-4 py-2.5 text-sm font-semibold disabled:opacity-50"
              style={{
                background: "var(--ms-brand-primary)",
                color: "var(--ms-text-on-brand, #fff)",
              }}
            >
              {submitting ? "Активация…" : "Создать аккаунт"}
            </button>
          </form>
        ) : null}

        <p className="text-sm" style={{ color: "var(--ms-text-secondary)" }}>
          Уже есть аккаунт?{" "}
          <a href="/login" className="underline font-medium">
            Войти
          </a>
        </p>
      </div>
    </div>
  );
}
