/** Extract / normalize pilot invite tokens from raw codes or full URLs. */

const TOKEN_RE = /mpi_[A-Za-z0-9_-]+/;

export function extractInviteToken(input: string): string | null {
  const raw = (input || "").trim();
  if (!raw) return null;
  if (raw.startsWith("mpi_") && TOKEN_RE.test(raw.split(/[\s?#]/)[0] || "")) {
    const only = raw.split(/[\s?#&]/)[0];
    return only || null;
  }
  try {
    const asUrl = raw.includes("://") ? new URL(raw) : null;
    if (asUrl) {
      const fromQuery = asUrl.searchParams.get("token");
      if (fromQuery && TOKEN_RE.test(fromQuery)) return fromQuery.trim();
    }
  } catch {
    /* fall through */
  }
  const match = raw.match(TOKEN_RE);
  return match ? match[0] : null;
}

export type InviteUiState =
  | "token_missing"
  | "loading"
  | "valid"
  | "expired"
  | "revoked"
  | "already_used"
  | "invalid"
  | "account_exists"
  | "backend_unavailable";

export function inviteStateMessage(state: InviteUiState): string {
  switch (state) {
    case "token_missing":
      return "";
    case "expired":
      return "Срок действия приглашения истёк. Запросите новое у оператора пилота.";
    case "revoked":
      return "Приглашение отозвано. Запросите новое у оператора пилота.";
    case "already_used":
      return "Приглашение уже использовано. Войдите со своим паролем.";
    case "account_exists":
      return "Аккаунт для этого email уже существует. Перейдите ко входу.";
    case "invalid":
      return "Код или ссылка приглашения недействительны.";
    case "backend_unavailable":
      return "Сервис временно недоступен. Проверьте API и обновите страницу.";
    default:
      return "";
  }
}
