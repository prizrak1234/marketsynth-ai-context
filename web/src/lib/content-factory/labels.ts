import type { AppLocale } from "@/lib/i18n/config";
import { translate } from "@/lib/i18n/domain-labels";

/** Product channel options — backend enum values stay internal. */
export const CONTENT_FACTORY_CHANNEL_OPTIONS = [
  { productId: "telegram", backendChannel: "telegram" },
  { productId: "youtube", backendChannel: "blog" },
  { productId: "social", backendChannel: "instagram" },
  { productId: "blog", backendChannel: "blog" },
] as const;

export type ContentFactoryProductChannelId =
  (typeof CONTENT_FACTORY_CHANNEL_OPTIONS)[number]["productId"];

export function backendChannelForProduct(
  productId: ContentFactoryProductChannelId,
): string {
  return (
    CONTENT_FACTORY_CHANNEL_OPTIONS.find((row) => row.productId === productId)
      ?.backendChannel ?? "telegram"
  );
}

export function labelMaterialStatus(locale: AppLocale, status: string): string {
  const key = `contentFactory.materialStatus.${status}`;
  const translated = translate(locale, key);
  return translated === key ? translate(locale, "contentFactory.materialStatus.unknown") : translated;
}

export function labelPackageStatus(locale: AppLocale, status: string): string {
  const key = `contentFactory.packageStatus.${status}`;
  const translated = translate(locale, key);
  return translated === key ? translate(locale, "contentFactory.packageStatus.unknown") : translated;
}

export function labelJobStatus(locale: AppLocale, status: string): string {
  const key = `contentFactory.jobStatus.${status}`;
  const translated = translate(locale, key);
  return translated === key ? translate(locale, "contentFactory.jobStatus.unknown") : translated;
}

export function labelScheduleStatus(locale: AppLocale, status: string): string {
  const key = `contentFactory.scheduleStatus.${status}`;
  const translated = translate(locale, key);
  return translated === key
    ? translate(locale, "contentFactory.scheduleStatus.unknown")
    : translated;
}

export function labelProductChannel(locale: AppLocale, productId: string): string {
  const key = `contentFactory.channel.${productId}`;
  const translated = translate(locale, key);
  return translated === key ? productId : translated;
}

export function isDemoMaterial(metadata: Record<string, unknown> | undefined): boolean {
  if (!metadata) return false;
  const marker = metadata.demo_seed ?? metadata.e2e_v1 ?? metadata.recovery_r3_demo;
  return marker != null && marker !== false && marker !== "";
}

export function planDraftLineage(
  metadata: Record<string, unknown> | undefined,
): { draftId: string; slotIndex: number } | null {
  if (!metadata) return null;
  const draftId = metadata.source_plan_draft_id;
  const slotIndex = metadata.plan_item_index;
  if (typeof draftId !== "string" || !draftId.trim()) return null;
  if (typeof slotIndex !== "number" || Number.isNaN(slotIndex)) return null;
  return { draftId, slotIndex: slotIndex + 1 };
}
