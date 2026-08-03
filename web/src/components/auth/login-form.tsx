"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { PRODUCT_BRAND } from "@/lib/brand/product-brand";
import { useAuth } from "@/lib/auth/auth-context";
import {
  INCOMPLETE_EMAIL_MESSAGE,
  isCompleteLoginEmail,
  normalizeLoginEmail,
} from "@/lib/auth/normalize-email";
import { fetchSignupStatus } from "@/lib/auth/register-client";
import { resolvePostAuthHref } from "@/lib/routes/workspace-entry";

/** Canonical local frontend host for cookie + CSRF + CORS alignment. */
export const CANONICAL_LOCAL_FRONTEND = "http://localhost:3000";

export function LoginForm() {
  const { login, loading, error, clearError } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [clientError, setClientError] = useState<string | null>(null);
  const [signupEnabled, setSignupEnabled] = useState(false);

  const nonCanonicalHost =
    typeof window !== "undefined" &&
    window.location.hostname === "127.0.0.1" &&
    window.location.port === "3000";

  const passwordResetSuccess = params.get("passwordReset") === "success";

  useEffect(() => {
    // Drop stale login errors when arriving via navigation (e.g. after reset).
    clearError();
    setClientError(null);
  }, [clearError, params]);

  useEffect(() => {
    let cancelled = false;
    void fetchSignupStatus().then((s) => {
      if (!cancelled) setSignupEnabled(s.signupEnabled);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    clearError();
    setClientError(null);
    const normalized = normalizeLoginEmail(email);
    if (!isCompleteLoginEmail(normalized)) {
      setClientError(INCOMPLETE_EMAIL_MESSAGE);
      return;
    }
    setSubmitting(true);
    const ok = await login(normalized, password);
    if (!ok) {
      setSubmitting(false);
      return;
    }
    const dest = await resolvePostAuthHref(params.get("next"));
    setSubmitting(false);
    router.replace(dest);
  }

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
          <h1 className="mt-2 text-2xl font-semibold">Вход в пилот</h1>
          <p className="mt-1 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
            Сессия ограничена по времени. API keys не хранятся в браузере.
          </p>
        </header>
        {passwordResetSuccess ? (
          <p
            className="rounded-md border px-3 py-2 text-sm"
            style={{
              borderColor: "var(--ms-border-default)",
              color: "var(--ms-text-secondary)",
            }}
            role="status"
            data-testid="login-password-reset-success"
          >
            Пароль обновлён. Войдите с новым паролем.
          </p>
        ) : null}
        {nonCanonicalHost ? (
          <p
            className="rounded-md border px-3 py-2 text-sm"
            style={{
              borderColor: "var(--ms-border-default)",
              color: "var(--ms-text-secondary)",
            }}
            data-testid="login-host-hint"
          >
            Для стабильных cookie-сессий используйте{" "}
            <a className="underline" href={`${CANONICAL_LOCAL_FRONTEND}/login`}>
              {CANONICAL_LOCAL_FRONTEND}/login
            </a>
            . Сейчас открыт 127.0.0.1 — вход поддерживается, если API host совпадает.
          </p>
        ) : null}
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          <div>
            <label htmlFor="login-email" className="block text-sm font-medium">
              Email
            </label>
            <input
              id="login-email"
              name="email"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => {
                clearError();
                setClientError(null);
                setEmail(e.target.value);
              }}
              className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
              style={{
                borderColor: "var(--ms-border-default)",
                background: "var(--ms-bg-surface)",
              }}
              aria-invalid={clientError ? true : undefined}
              data-testid="login-email"
            />
            {clientError ? (
              <p
                className="mt-1 text-sm"
                style={{ color: "var(--ms-status-danger)" }}
                role="alert"
                data-testid="login-email-error"
              >
                {clientError}
              </p>
            ) : null}
          </div>
          <div>
            <label htmlFor="login-password" className="block text-sm font-medium">
              Пароль
            </label>
            <input
              id="login-password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              minLength={10}
              value={password}
              onChange={(e) => {
                clearError();
                setPassword(e.target.value);
              }}
              className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
              style={{
                borderColor: "var(--ms-border-default)",
                background: "var(--ms-bg-surface)",
              }}
            />
          </div>
          {error ? (
            <p
              className="text-sm"
              style={{ color: "var(--ms-status-danger)" }}
              role="alert"
              data-testid="login-error"
              data-error-kind={error.kind}
            >
              {error.message} {error.actionHint}
            </p>
          ) : null}
          <button
            type="submit"
            disabled={loading || submitting}
            data-testid="login-submit"
            aria-busy={submitting || loading}
            className="w-full rounded-md px-4 py-2.5 text-sm font-semibold disabled:opacity-50"
            style={{
              background: "var(--ms-brand-primary)",
              color: "var(--ms-text-on-brand, #fff)",
            }}
          >
            {submitting ? "Вход…" : "Войти"}
          </button>
          <p className="text-sm text-center">
            <a
              href={`/forgot-password${email ? `?email=${encodeURIComponent(normalizeLoginEmail(email))}` : ""}`}
              className="font-medium underline"
              data-testid="forgot-password-link"
              onClick={() => clearError()}
            >
              Забыли пароль?
            </a>
          </p>
        </form>
        {signupEnabled ? (
          <p
            className="text-sm text-center"
            style={{ color: "var(--ms-text-secondary)" }}
            data-testid="login-register-cta"
          >
            Нет аккаунта?{" "}
            <a
              href="/register"
              className="font-medium underline"
              data-testid="register-link"
            >
              Зарегистрироваться
            </a>
          </p>
        ) : null}
        <p className="text-sm text-center" style={{ color: "var(--ms-text-secondary)" }}>
          Есть код приглашения?{" "}
          <a
            href="/activate-invite"
            className="font-medium underline"
            data-testid="activate-invite-link"
          >
            Активировать приглашение
          </a>
        </p>
        <p
          className="text-xs text-center"
          style={{ color: "var(--ms-text-secondary)" }}
          data-testid="activate-invite-hint"
        >
          {signupEnabled
            ? "Регистрация доступна для локального/пилот-окружения. Приглашение — для заранее одобренных пользователей."
            : "Регистрация отключена. Нужна одноразовая ссылка или код от оператора пилота."}
        </p>
      </div>
    </div>
  );
}
