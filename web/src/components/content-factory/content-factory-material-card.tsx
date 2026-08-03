"use client";

import { Button } from "@/components/ui/button";
import {
  labelMaterialStatus,
  isDemoMaterial,
} from "@/lib/content-factory/labels";
import type { ContentAsset } from "@/lib/api/types/content-assets";
import { useLocale } from "@/lib/i18n";

type ContentFactoryMaterialCardProps = {
  asset: ContentAsset;
  selected: boolean;
  onSelect: () => void;
  onOpen: () => void;
};

export function ContentFactoryMaterialCard({
  asset,
  selected,
  onSelect,
  onOpen,
}: ContentFactoryMaterialCardProps) {
  const { t, locale } = useLocale();
  const demo = isDemoMaterial(asset.metadata);

  return (
    <article
      className="rounded-xl border p-4"
      style={{
        borderColor: selected ? "var(--ms-brand-primary)" : "var(--ms-border-default)",
        background: "var(--ms-bg-surface)",
      }}
      data-testid={`content-factory-material-${asset.id}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {t("contentFactory.materialLabel")}
          </p>
          <h3 className="mt-1 truncate text-sm font-semibold">{asset.title}</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            {labelMaterialStatus(locale, asset.status)}
          </p>
          {demo ? (
            <p
              className="mt-2 text-xs"
              style={{ color: "var(--ms-text-muted)" }}
              data-testid="content-factory-demo-marker"
            >
              {t("contentFactory.demoMaterialsHint")}
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="button" size="sm" variant="outline" onClick={onOpen}>
            {t("contentFactory.action.viewMaterial")}
          </Button>
          <Button
            type="button"
            size="sm"
            variant={selected ? "default" : "outline"}
            onClick={onSelect}
          >
            {selected
              ? t("contentFactory.action.selectedForPackage")
              : t("contentFactory.action.selectForPackage")}
          </Button>
        </div>
      </div>
    </article>
  );
}
