"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import {
  approveContentAsset,
  archiveContentAsset,
  createManualContentAssetRevision,
  fetchContentAsset,
  submitContentAssetForReview,
} from "@/lib/api/endpoints/content-assets";
import { contentAssetBodyUnavailableLabel } from "@/lib/api/mappers/content-assets";
import { ApiError } from "@/lib/api/errors";
import { labelMaterialStatus, planDraftLineage } from "@/lib/content-factory/labels";
import type { ContentAsset } from "@/lib/api/types/content-assets";
import { useLocale } from "@/lib/i18n";

type ContentFactoryMaterialEditorProps = {
  projectId: string;
  asset: ContentAsset;
  onClose: () => void;
  onUpdated: () => void;
};

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Request failed";
}

export function ContentFactoryMaterialEditor({
  projectId,
  asset,
  onClose,
  onUpdated,
}: ContentFactoryMaterialEditorProps) {
  const { t, locale } = useLocale();
  const queryClient = useQueryClient();
  const assetQuery = useQuery({
    queryKey: ["projects", projectId, "content-assets", asset.id],
    queryFn: () => fetchContentAsset(projectId, asset.id),
    initialData: asset,
    refetchOnWindowFocus: false,
  });
  const resolvedAsset = assetQuery.data ?? asset;
  const resolvedBody =
    typeof resolvedAsset.body === "string" ? resolvedAsset.body : "";
  const [title, setTitle] = useState(resolvedAsset.title);
  const [body, setBody] = useState(resolvedBody);
  const [actionError, setActionError] = useState<string | null>(null);
  const bodyUnavailable = !resolvedBody.trim();

  useEffect(() => {
    setTitle(resolvedAsset.title);
    setBody(resolvedBody);
  }, [resolvedAsset.id, resolvedAsset.title, resolvedBody]);

  const invalidate = () => {
    void queryClient.invalidateQueries({
      queryKey: ["projects", projectId, "content-assets"],
    });
    onUpdated();
  };

  const saveMutation = useMutation({
    mutationFn: () =>
      createManualContentAssetRevision(projectId, asset.id, { title, body }),
    onSuccess: () => {
      setActionError(null);
      invalidate();
    },
    onError: (err) => setActionError(errorMessage(err)),
  });

  const submitMutation = useMutation({
    mutationFn: () => submitContentAssetForReview(projectId, asset.id),
    onSuccess: () => {
      setActionError(null);
      invalidate();
    },
    onError: (err) => setActionError(errorMessage(err)),
  });

  const approveMutation = useMutation({
    mutationFn: () => approveContentAsset(projectId, asset.id),
    onSuccess: () => {
      setActionError(null);
      invalidate();
    },
    onError: (err) => setActionError(errorMessage(err)),
  });

  const rejectMutation = useMutation({
    mutationFn: () => archiveContentAsset(projectId, asset.id),
    onSuccess: () => {
      setActionError(null);
      invalidate();
      onClose();
    },
    onError: (err) => setActionError(errorMessage(err)),
  });

  const busy =
    saveMutation.isPending ||
    submitMutation.isPending ||
    approveMutation.isPending ||
    rejectMutation.isPending;
  const lineage = planDraftLineage(resolvedAsset.metadata);

  return (
    <section
      className="rounded-xl border p-4"
      style={{
        borderColor: "var(--ms-border-default)",
        background: "var(--ms-bg-surface)",
      }}
      data-testid="content-factory-material-editor"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {t("contentFactory.materialLabel")}
          </p>
          <p className="text-sm font-semibold">{resolvedAsset.title}</p>
          <p className="text-xs text-muted-foreground">
            {labelMaterialStatus(locale, resolvedAsset.status)}
          </p>
          {lineage ? (
            <p
              className="mt-1 text-xs text-muted-foreground"
              data-testid="content-factory-material-lineage"
            >
              {t("contentFactory.materials.lineage", {
                slot: lineage.slotIndex,
                draftId: lineage.draftId.slice(0, 8),
              })}
            </p>
          ) : null}
        </div>
        <Button type="button" size="sm" variant="ghost" onClick={onClose}>
          {t("contentFactory.action.closeMaterial")}
        </Button>
      </div>

      <div className="mt-4 space-y-3">
        <label className="block text-xs font-medium">
          {t("contentFactory.field.title")}
          <input
            className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
            style={{ borderColor: "var(--ms-border-default)" }}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            data-testid="content-factory-material-title"
          />
        </label>
        <label className="block text-xs font-medium">
          {t("contentFactory.field.body")}
          {bodyUnavailable ? (
            <p className="mt-1 text-xs text-muted-foreground" data-testid="content-factory-material-body-unavailable">
              {contentAssetBodyUnavailableLabel(locale)}
            </p>
          ) : null}
          <textarea
            rows={8}
            className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
            style={{ borderColor: "var(--ms-border-default)" }}
            value={body ?? ""}
            onChange={(e) => setBody(e.target.value)}
            data-testid="content-factory-material-body"
          />
        </label>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={busy}
          onClick={() => saveMutation.mutate()}
          data-testid="content-factory-material-save"
        >
          {t("contentFactory.action.saveMaterial")}
        </Button>
        {resolvedAsset.status === "draft" ? (
          <Button
            type="button"
            size="sm"
            disabled={busy}
            onClick={() => submitMutation.mutate()}
            data-testid="content-factory-material-submit"
          >
            {t("contentFactory.action.submitMaterialReview")}
          </Button>
        ) : null}
        {resolvedAsset.status === "review" ? (
          <Button
            type="button"
            size="sm"
            disabled={busy}
            onClick={() => approveMutation.mutate()}
            data-testid="content-factory-material-approve"
          >
            {t("contentFactory.action.approveMaterial")}
          </Button>
        ) : null}
        {resolvedAsset.status !== "archived" && resolvedAsset.status !== "approved" ? (
          <Button
            type="button"
            size="sm"
            variant="destructive"
            disabled={busy}
            onClick={() => rejectMutation.mutate()}
            data-testid="content-factory-material-reject"
          >
            {t("contentFactory.action.rejectMaterial")}
          </Button>
        ) : null}
      </div>

      {actionError ? (
        <p className="mt-2 text-xs text-destructive" data-testid="content-factory-material-error">
          {actionError}
        </p>
      ) : null}
    </section>
  );
}
