/** Build review note map from backend asset acceptance truth. */

import type { GeneratedVisualAssetDto } from "@/lib/api/endpoints/generated-visual-assets";

export function reviewNotesFromAssets(
  assets: GeneratedVisualAssetDto[],
  labels: { accepted: string; rejected: string },
): Record<string, string> {
  const notes: Record<string, string> = {};
  for (const asset of assets) {
    if (asset.user_accepted === true) {
      notes[asset.id] = labels.accepted;
    } else if (asset.user_accepted === false) {
      notes[asset.id] = labels.rejected;
    }
  }
  return notes;
}

/** Latest accepted image asset for the owner (deterministic: newest created_at). */
export function latestAcceptedImageAssetId(
  assets: GeneratedVisualAssetDto[],
): string | null {
  const accepted = assets.filter(
    (a) =>
      a.user_accepted === true &&
      (a.mime_type || "").startsWith("image/") &&
      a.asset_type !== "video_clip",
  );
  if (accepted.length === 0) return null;
  accepted.sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );
  return accepted[0]?.id ?? null;
}
