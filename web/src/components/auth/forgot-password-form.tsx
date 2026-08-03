"use client";

import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { PRODUCT_BRAND } from "@/lib/brand/product-brand";
import {
  INCOMPLETE_EMAIL_MESSAGE,
  isCompleteLoginEmail,
  normalizeLoginEmail,
} from "@/lib/auth/normalize-email";
import { requestPasswordReset } from "@/lib/auth/password-reset-client";

export function ForgotPasswordForm() {
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [clientError, setClientError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const preset = params.get("email");
    if (preset) setEmail(normalizeLoginEmail(preset));
  }, [params]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setClientError(null);
    const normalized = normalizeLoginEmail(email);
    if (!isCompleteLoginEmail(normalized)) {
      setClientError(INCOMPLETE_EMAIL_MESSAGE);
      return;
    }
    setSubmitting(true);
    const res = await requestPasswordReset(normalized);
    setSubmitting(false);
    if (!res.ok) {
      if (res.code === "rate_limited") {
        setClientError("Слишком много запросов. Подождите и повторите.");
      } else if (res.code === "backend_unavailable") {
        setClientError("Сервис временно недоступен. Попробуйте позже.");
      } else {
        setClientError("Не удалось отправить запрос. Попробуйте позже.");
      }
      return;
    }
    setDone(true);
    setMessage(res.message);
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
          <h1 className="mt-2 text-2xl font-semibold">Сброс пароля</h1>
          <p className="mt-1 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
            Укажите email аккаунта. Мы не сообщаем, существует ли он.
          </p>
        </header>

        {done ? (
          <div className="space-y-4" data-testid="forgot-password-done">
            <p className="text-sm" role="status">
              {message ||
                "If an account exists, password reset instructions have been created."}
            </p>
            <p className="text-sm" style={{ color: "var(--ms-text-secondary)" }}>
              В локальном пилоте оператор откроет одноразовую ссылку сброса. Не
              вводите команды в поля формы.
            </p>
            <a href="/login" className="text-sm font-medium underline">
              Вернуться ко входу
            </a>
          </div>
        ) : (
          <form
            onSubmit={onSubmit}
            className="space-y-4"
            noValidate
            data-testid="forgot-password-form"
          >
            <div>
              <label htmlFor="forgot-email" className="block text-sm font-medium">
                Email
              </label>
              <input
                id="forgot-email"
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={(e) => {
                  setClientError(null);
                  setEmail(e.target.value);
                }}
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
                style={{
                  borderColor: "var(--ms-border-default)",
                  background: "var(--ms-bg-surface)",
                }}
                data-testid="forgot-password-email"
              />
            </div>
            {clientError ? (
              <p
                className="text-sm"
                style={{ color: "var(--ms-status-danger)" }}
                role="alert"
                data-testid="forgot-password-error"
              >
                {clientError}
              </p>
            ) : null}
            <button
              type="submit"
              disabled={submitting}
              data-testid="forgot-password-submit"
              aria-busy={submitting}
              className="w-full rounded-md px-4 py-2.5 text-sm font-semibold disabled:opacity-50"
              style={{
                background: "var(--ms-brand-primary)",
                color: "var(--ms-text-on-brand, #fff)",
              }}
            >
              {submitting ? "Отправка…" : "Запросить сброс"}
            </button>
          </form>
        )}

        <p className="text-sm" style={{ color: "var(--ms-text-secondary)" }}>
          <a href="/login" className="underline font-medium">
            Войти
          </a>
        </p>
      </div>
    </div>
  );
}
