"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PRODUCT_BRAND } from "@/lib/brand/product-brand";
import { useAuth } from "@/lib/auth/auth-context";
import {
  fetchSignupStatus,
  registerAccount,
} from "@/lib/auth/register-client";
import { resolveWorkspaceEntryHref } from "@/lib/routes/workspace-entry";
import {
  INCOMPLETE_EMAIL_MESSAGE,
  isCompleteLoginEmail,
  normalizeLoginEmail,
} from "@/lib/auth/normalize-email";

export function RegisterForm() {
  const router = useRouter();
  const { refresh } = useAuth();
  const [signupEnabled, setSignupEnabled] = useState<boolean | null>(null);
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [acceptNotice, setAcceptNotice] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);

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
    setError(null);
    setErrorCode(null);
    const normalized = normalizeLoginEmail(email);
    if (!isCompleteLoginEmail(normalized)) {
      setError(INCOMPLETE_EMAIL_MESSAGE);
      setErrorCode("invalid_email");
      return;
    }
    if (password !== passwordConfirm) {
      setError("Пароли не совпадают.");
      setErrorCode("password_mismatch");
      return;
    }
    setSubmitting(true);
    const res = await registerAccount({
      email: normalized,
      displayName: displayName.trim() || normalized.split("@")[0] || "User",
      password,
      passwordConfirmation: passwordConfirm,
      acceptedPilotNotice: acceptNotice,
    });
    setSubmitting(false);
    if (!res.ok) {
      setError(res.error.message);
      setErrorCode(res.error.code);
      return;
    }
    await refresh();
    const dest = await resolveWorkspaceEntryHref();
    router.replace(dest);
  }

  if (signupEnabled === null) {
    return (
      <p className="p-8 text-sm" data-testid="register-loading">
        Загрузка…
      </p>
    );
  }

  if (!signupEnabled) {
    return (
      <div
        className="flex min-h-screen items-center justify-center px-4"
        style={{ background: "var(--ms-bg-canvas)", color: "var(--ms-text-primary)" }}
      >
        <div className="w-full max-w-md space-y-4" data-testid="register-disabled">
          <h1 className="text-2xl font-semibold">Регистрация недоступна</h1>
          <p className="text-sm" style={{ color: "var(--ms-text-secondary)" }}>
            Публичная регистрация отключена. Войдите или активируйте приглашение.
          </p>
          <p className="text-sm space-x-3">
            <a href="/login" className="underline font-medium">
              Войти
            </a>
            <a href="/activate-invite" className="underline font-medium">
              Активировать приглашение
            </a>
          </p>
        </div>
      </div>
    );
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
          <h1 className="mt-2 text-2xl font-semibold">Регистрация</h1>
          <p className="mt-1 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
            Локальный / контролируемый пилот. Новый аккаунт получает роль участника
            (member), не владельца.
          </p>
        </header>
        <form onSubmit={onSubmit} className="space-y-4" noValidate data-testid="register-form">
          <div>
            <label htmlFor="register-email" className="block text-sm font-medium">
              Email
            </label>
            <input
              id="register-email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => {
                setError(null);
                setErrorCode(null);
                setEmail(e.target.value);
              }}
              className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
              style={{
                borderColor: "var(--ms-border-default)",
                background: "var(--ms-bg-surface)",
              }}
              data-testid="register-email"
            />
          </div>
          <div>
            <label htmlFor="register-display-name" className="block text-sm font-medium">
              Отображаемое имя
            </label>
            <input
              id="register-display-name"
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
              data-testid="register-display-name"
            />
          </div>
          <div>
            <label htmlFor="register-password" className="block text-sm font-medium">
              Пароль
            </label>
            <input
              id="register-password"
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
              data-testid="register-password"
            />
          </div>
          <div>
            <label htmlFor="register-password-confirm" className="block text-sm font-medium">
              Подтверждение пароля
            </label>
            <input
              id="register-password-confirm"
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
              data-testid="register-password-confirm"
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
              data-testid="register-notice"
            />
            <span>
              Соглашаюсь с условиями контролируемого пилота Marketsynth: данные для
              тестирования, исполнение рекламы и публичная production-регистрация
              отключены.
            </span>
          </label>
          {error ? (
            <p
              className="text-sm"
              style={{ color: "var(--ms-status-danger)" }}
              role="alert"
              data-testid="register-error"
              data-error-code={errorCode || undefined}
            >
              {error}
              {errorCode === "email_taken" ? (
                <span className="mt-2 flex flex-wrap gap-3" data-testid="register-duplicate-actions">
                  <a
                    href="/login"
                    className="underline font-medium"
                    data-testid="register-duplicate-login"
                  >
                    Войти
                  </a>
                  <a
                    href={`/forgot-password?email=${encodeURIComponent(normalizeLoginEmail(email))}`}
                    className="underline font-medium"
                    data-testid="register-duplicate-reset"
                  >
                    Сбросить пароль
                  </a>
                </span>
              ) : null}
            </p>
          ) : null}
          <button
            type="submit"
            disabled={submitting}
            data-testid="register-submit"
            aria-busy={submitting}
            className="w-full rounded-md px-4 py-2.5 text-sm font-semibold disabled:opacity-50"
            style={{
              background: "var(--ms-brand-primary)",
              color: "var(--ms-text-on-brand, #fff)",
            }}
          >
            {submitting ? "Создание…" : "Создать аккаунт"}
          </button>
        </form>
        <p className="text-sm" style={{ color: "var(--ms-text-secondary)" }}>
          Уже есть аккаунт?{" "}
          <a href="/login" className="underline font-medium">
            Войти
          </a>
          {" · "}
          <a href="/activate-invite" className="underline font-medium">
            Активировать приглашение
          </a>
        </p>
      </div>
    </div>
  );
}
