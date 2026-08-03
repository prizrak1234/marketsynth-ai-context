"use client";

import { useEffect, useState } from "react";
import type { OfferVersionHistoryItem } from "@/lib/api/endpoints/offers";
import { listOfferVersions } from "@/lib/api/endpoints/offers";
import { useLocale } from "@/lib/i18n";

type Props = {
  projectId: string;
  offerId: string;
  versionNumber: number;
};

export function OfferVersionHistory({ projectId, offerId, versionNumber }: Props) {
  const { t } = useLocale();
  const [versions, setVersions] = useState<OfferVersionHistoryItem[]>([]);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (!expanded) return;
    let cancelled = false;
    void listOfferVersions(projectId, offerId).then((items) => {
      if (!cancelled) setVersions(items);
    });
    return () => {
      cancelled = true;
    };
  }, [expanded, projectId, offerId]);

  return (
    <div className="text-sm" data-testid="offer-version-history">
      <button
        type="button"
        className="font-medium underline-offset-2 hover:underline"
        style={{ color: "var(--ms-text-muted)" }}
        onClick={() => setExpanded((v) => !v)}
      >
        {t("offer.version.current", { n: String(versionNumber) })}
      </button>
      {expanded && versions.length > 1 ? (
        <ul className="mt-2 space-y-1 pl-4" style={{ color: "var(--ms-text-muted)" }}>
          {versions.map((v) => (
            <li key={v.id}>
              {t("offer.version.item", {
                n: String(v.version_number),
                title: v.offer_title || t("offer.untitled"),
              })}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
