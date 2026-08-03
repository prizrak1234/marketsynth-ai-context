/** Shared email normalization — login, register, invite. */

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function normalizeLoginEmail(raw: string): string {
  return raw.trim().toLowerCase();
}

export function isCompleteLoginEmail(raw: string): boolean {
  const normalized = normalizeLoginEmail(raw);
  if (!normalized || normalized.length < 5) return false;
  if (!normalized.includes("@")) return false;
  const [local, domain] = normalized.split("@", 2);
  if (!local || !domain) return false;
  if (!domain.includes(".")) return false;
  return EMAIL_RE.test(normalized);
}

export const INCOMPLETE_EMAIL_MESSAGE =
  "Введите полный email, например name@example.com";
