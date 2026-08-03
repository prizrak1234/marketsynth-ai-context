import type { ContentAsset, ContentAssetVersion } from "@/lib/api/types/content-assets";

type RawContentAsset = ContentAsset & {
  content?: string | null;
  asset_body?: string | null;
  current_body?: string | null;
};

function coalesceBody(raw: RawContentAsset): string {
  const candidates = [raw.body, raw.content, raw.asset_body, raw.current_body];
  for (const value of candidates) {
    if (typeof value === "string") {
      return value;
    }
  }
  return "";
}

export function normalizeContentAsset(raw: RawContentAsset): ContentAsset {
  return {
    ...raw,
    body: coalesceBody(raw),
  };
}

export function normalizeContentAssetVersion(raw: ContentAssetVersion): ContentAssetVersion {
  const body =
    typeof raw.body === "string" && raw.body.trim()
      ? raw.body
      : "";
  return {
    ...raw,
    body,
  };
}

export function contentAssetBodyUnavailableLabel(locale: "ru" | "en"): string {
  return locale === "ru" ? "Текст материала недоступен" : "Material body unavailable";
}
