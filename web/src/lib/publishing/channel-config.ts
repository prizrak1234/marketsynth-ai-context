import type { PublishingChannelCreateBody } from "@/lib/api/types/publishing";

const FORBIDDEN_CONFIG_KEYS = new Set([
  "bot_token",
  "token",
  "api_key",
  "secret",
]);

export function assertNoSecretConfigKeys(
  config: Record<string, unknown>,
): void {
  for (const key of Object.keys(config)) {
    if (FORBIDDEN_CONFIG_KEYS.has(key.trim().toLowerCase())) {
      throw new Error(
        "Bot token and secrets are not allowed in channel config. Set TELEGRAM_PUBLICATION_BOT_TOKEN in server env.",
      );
    }
  }
}

export function buildTelegramChannelConfig(input: {
  chatId: string;
  parseMode: "" | "HTML" | "MarkdownV2";
  disableWebPagePreview: boolean;
}): PublishingChannelCreateBody["config"] {
  const config: Record<string, unknown> = {
    chat_id: input.chatId.trim(),
    disable_web_page_preview: input.disableWebPagePreview,
  };
  if (input.parseMode) {
    config.parse_mode = input.parseMode;
  }
  assertNoSecretConfigKeys(config);
  return config as PublishingChannelCreateBody["config"];
}
