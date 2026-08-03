"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { PRODUCT_BRAND } from "@/lib/brand/product-brand";
import {
  completePasswordReset,
  fetchResetStatus,
  type ResetTokenState,
} from "@/lib/auth/password-reset-client";

const STATE_COPY: Record<Exclude<ResetTokenState, "valid">, string> = {
  invalid: "Ссылка сброса недействительна.",
  expired: "Срок действия ссылки истёк. Запросите сброс снова.",
  used: "Эта ссылка уже использована. Войдите или запросите новую.",
  revoked: "Ссылка отозвана. Запросите сброс снова.",
  backend_unavailable: "Сервис временно недоступен. Попробуйте позже.",
};

function errorMessage(code: string): string {
  switch (code) {
    case "password_mismatch":
      return "Пароли не совпадают.";
    case "password_too_short":
      return "Пароль должен быть не короче 10 символов.";
    case "password_too_weak":
      return "Выберите более стойкий пароль.";
    case "token_expired":
      return STATE_COPY.expired;
    case "token_used":
      return STATE_COPY.used;
    case "token_revoked":
      return STATE_COPY.revoked;
    case "invalid_token":
      return STATE_COPY.invalid;
    case "rate_limited":
      return "Слишком много попыток. Подождите и повторите.";
    case "backend_unavailable":
      return STATE_COPY.backend_unavailable;
    default:
      return "Не удалось обновить пароль.";
  }
}

export function ResetPasswordForm() {
  const router = useRouter();
  const params = useSearchParams();
  const token = (params.get("token") || "").trim();

  const [state, setState] = useState<ResetTokenState | "loading">("loading");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (!token) {
      setState("invalid");
      return;
    }
    void fetchResetStatus(token).then((s) => {
      if (!cancelled) setState(s);
    });
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (password !== passwordConfirm) {
      setError(errorMessage("password_mismatch"));
      return;
    }
    if (password.length < 10) {
      setError(errorMessage("password_too_short"));
      return;
    }
    setSubmitting(true);
    const res = await completePasswordReset(token, password, passwordConfirm);
    setSubmitting(false);
    if (!res.ok) {
      setError(errorMessage(res.code));
      if (
        res.code === "token_expired" ||
        res.code === "token_used" ||
        res.code === "token_revoked" ||
        res.code === "invalid_token"
      ) {
        setState(
          res.code === "token_expired"
            ? "expired"
            : res.code === "token_used"
              ? "used"
              : res.code === "token_revoked"
                ? "revoked"
                : "invalid",
        );
      }
      return;
    }
    router.replace("/login?passwordReset=success");
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
          <h1 className="mt-2 text-2xl font-semibold">Новый пароль</h1>
          <p className="mt-1 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
            Задайте пароль вручную. Старые сессии будут завершены.
          </p>
        </header>

        {state === "loading" ? (
          <p className="text-sm" data-testid="reset-password-loading">
            Проверка ссылки…
          </p>
        ) : null}

        {state !== "loading" && state !== "valid" ? (
          <div className="space-y-3" data-testid="reset-password-state" data-state={state}>
            <p
              className="text-sm"
              style={{ color: "var(--ms-status-danger)" }}
              role="alert"
            >
              {STATE_COPY[state]}
            </p>
            <p className="text-sm space-x-3">
              <a href="/forgot-password" className="underline font-medium">
                Запросить снова
              </a>
              <a href="/login" className="underline font-medium">
                Войти
              </a>
            </p>
          </div>
        ) : null}

        {state === "valid" ? (
          <form
            onSubmit={onSubmit}
            className="space-y-4"
            noValidate
            data-testid="reset-password-form"
          >
            <div>
              <label htmlFor="reset-password" className="block text-sm font-medium">
                Новый пароль
              </label>
              <input
                id="reset-password"
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
                data-testid="reset-password-input"
              />
            </div>
            <div>
              <label
                htmlFor="reset-password-confirm"
                className="block text-sm font-medium"
              >
                Подтверждение пароля
              </label>
              <input
                id="reset-password-confirm"
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
                data-testid="reset-password-confirm"
              />
            </div>
            {error ? (
              <p
                className="text-sm"
                style={{ color: "var(--ms-status-danger)" }}
                role="alert"
                data-testid="reset-password-error"
              >
                {error}
              </p>
            ) : null}
            <button
              type="submit"
              disabled={submitting}
              data-testid="reset-password-submit"
              aria-busy={submitting}
              className="w-full rounded-md px-4 py-2.5 text-sm font-semibold disabled:opacity-50"
              style={{
                background: "var(--ms-brand-primary)",
                color: "var(--ms-text-on-brand, #fff)",
              }}
            >
              {submitting ? "Сохранение…" : "Сохранить пароль"}
            </button>
          </form>
        ) : null}
      </div>
    </div>
  );
}
