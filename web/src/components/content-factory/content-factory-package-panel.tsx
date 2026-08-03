"use client";

import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import {
  approvePublicationPackage,
  archivePublicationPackage,
  createPublicationPackageFromAsset,
  fetchPublicationPackages,
  submitPublicationPackageForReview,
} from "@/lib/api/endpoints/publication-packages";
import { ApiError } from "@/lib/api/errors";
import {
  backendChannelForProduct,
  labelPackageStatus,
  type ContentFactoryProductChannelId,
} from "@/lib/content-factory/labels";
import type { ContentAsset } from "@/lib/api/types/content-assets";
import { useLocale } from "@/lib/i18n";

type ContentFactoryPackagePanelProps = {
  projectId: string;
  channelProductId: ContentFactoryProductChannelId;
  selectedAsset: ContentAsset | null;
  onPackageReady: (packageId: string) => void;
};

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Request failed";
}

export function ContentFactoryPackagePanel({
  projectId,
  channelProductId,
  selectedAsset,
  onPackageReady,
}: ContentFactoryPackagePanelProps) {
  const { t, locale } = useLocale();
  const queryClient = useQueryClient();
  const backendChannel = backendChannelForProduct(channelProductId);

  const packagesQuery = useQuery({
    queryKey: ["projects", projectId, "publication-packages", selectedAsset?.id],
    queryFn: () =>
      fetchPublicationPackages(projectId, {
        content_asset_id: selectedAsset?.id,
      }),
    enabled: Boolean(selectedAsset?.id),
  });

  const activePackage =
    packagesQuery.data?.find((pkg) => pkg.channel === backendChannel && pkg.status !== "archived") ??
    null;

  const invalidate = () => {
    void queryClient.invalidateQueries({
      queryKey: ["projects", projectId, "publication-packages"],
    });
  };

  const createMutation = useMutation({
    mutationFn: () => {
      if (!selectedAsset) throw new Error("material required");
      return createPublicationPackageFromAsset(projectId, selectedAsset.id, {
        channel: backendChannel,
        title: selectedAsset.title,
        body: selectedAsset.body ?? "",
      });
    },
    onSuccess: (data) => {
      invalidate();
      onPackageReady(data.publication_package_id);
    },
  });

  const submitMutation = useMutation({
    mutationFn: () => {
      if (!activePackage) throw new Error("package required");
      return submitPublicationPackageForReview(projectId, activePackage.id);
    },
    onSuccess: invalidate,
  });

  const approveMutation = useMutation({
    mutationFn: () => {
      if (!activePackage) throw new Error("package required");
      return approvePublicationPackage(projectId, activePackage.id);
    },
    onSuccess: () => {
      invalidate();
      if (activePackage) onPackageReady(activePackage.id);
    },
  });

  const reworkMutation = useMutation({
    mutationFn: () => {
      if (!activePackage) throw new Error("package required");
      return archivePublicationPackage(projectId, activePackage.id);
    },
    onSuccess: invalidate,
  });

  useEffect(() => {
    if (activePackage?.status === "approved") {
      onPackageReady(activePackage.id);
    }
  }, [activePackage?.id, activePackage?.status, onPackageReady]);

  const mutationError =
    createMutation.error ??
    submitMutation.error ??
    approveMutation.error ??
    reworkMutation.error;

  if (!selectedAsset) {
    return (
      <section
        className="rounded-xl border p-4 text-sm text-muted-foreground"
        data-testid="content-factory-package-empty"
      >
        {t("contentFactory.package.selectMaterialFirst")}
      </section>
    );
  }

  if (selectedAsset.status !== "approved") {
    return (
      <section
        className="rounded-xl border p-4 text-sm text-muted-foreground"
        data-testid="content-factory-package-not-ready"
      >
        {t("contentFactory.package.materialMustBeApproved")}
      </section>
    );
  }

  return (
    <section
      className="rounded-xl border p-4"
      style={{
        borderColor: "var(--ms-border-default)",
        background: "var(--ms-bg-surface)",
      }}
      data-testid="content-factory-package-panel"
    >
      <h2 className="text-sm font-semibold">{t("contentFactory.packageLabel")}</h2>
      <p className="mt-1 text-xs text-muted-foreground">{t("contentFactory.package.hint")}</p>

      {!activePackage ? (
        <div className="mt-4">
          <Button
            type="button"
            size="sm"
            disabled={createMutation.isPending}
            onClick={() => createMutation.mutate()}
            data-testid="content-factory-package-create"
          >
            {t("contentFactory.action.createPackage")}
          </Button>
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          <div className="text-sm">
            <p className="font-medium">{activePackage.title}</p>
            <p className="text-xs text-muted-foreground">
              {labelPackageStatus(locale, activePackage.status)}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {activePackage.status === "draft" ? (
              <Button
                type="button"
                size="sm"
                disabled={submitMutation.isPending}
                onClick={() => submitMutation.mutate()}
                data-testid="content-factory-package-submit"
              >
                {t("contentFactory.action.checkPackage")}
              </Button>
            ) : null}
            {activePackage.status === "review" ? (
              <>
                <Button
                  type="button"
                  size="sm"
                  disabled={approveMutation.isPending}
                  onClick={() => approveMutation.mutate()}
                  data-testid="content-factory-package-approve"
                >
                  {t("contentFactory.action.approvePackage")}
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={reworkMutation.isPending}
                  onClick={() => reworkMutation.mutate()}
                  data-testid="content-factory-package-rework"
                >
                  {t("contentFactory.action.reworkPackage")}
                </Button>
              </>
            ) : null}
            {activePackage.status === "approved" ? (
              <p className="text-xs text-muted-foreground" data-testid="content-factory-package-approved">
                {t("contentFactory.package.readyForPreview")}
              </p>
            ) : null}
          </div>
        </div>
      )}

      {mutationError ? (
        <p className="mt-2 text-xs text-destructive">{errorMessage(mutationError)}</p>
      ) : null}
    </section>
  );
}
