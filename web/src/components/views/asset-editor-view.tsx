"use client";



import { useState } from "react";

import { useQuery } from "@tanstack/react-query";

import {

  ApiKeyMissing,

  ProjectIdMissing,

} from "@/components/data/config-missing";

import { QueryStatus } from "@/components/data/query-status";

import { PageHeader } from "@/components/layout/page-header";

import { SchedulePublicationForm } from "@/components/assets/schedule-publication-form";

import { AssetDraftRevisionEditor } from "@/components/assets/asset-draft-revision-editor";

import { AssetApprovedRevisionPanel } from "@/components/assets/asset-approved-revision-panel";
import { AssetMediaBriefPanel } from "@/components/assets/asset-media-brief-panel";
import { AssetPublicationPackagesPanel } from "@/components/assets/asset-publication-packages-panel";

import { AssetVersionHistory } from "@/components/assets/asset-version-history";

import { Button } from "@/components/ui/button";

import { ConfirmDialog } from "@/components/ui/confirm-dialog";

import {

  fetchContentAsset,

  fetchContentAssetVersions,

} from "@/lib/api";

import { queryKeys } from "@/lib/api/query-keys";

import { useEnvConfig } from "@/lib/hooks/use-env-config";

import { useContentAssetMutations } from "@/lib/hooks/use-content-asset-mutations";

import { formatDateTime } from "@/lib/format";



type AssetEditorViewProps = {

  assetId: string;

};



function AssetActionBar({

  projectId,

  assetId,

  assetTitle,

  status,

  campaignId,

}: {

  projectId: string;

  assetId: string;

  assetTitle: string;

  status: string;

  campaignId?: string | null;

}) {

  const [archiveOpen, setArchiveOpen] = useState(false);

  const { submitReviewMutation, approveMutation, archiveMutation, isPending } =
    useContentAssetMutations({
      projectId,
      assetId,
      campaignId,
      assetTitle,
    });

  const isDraft = status === "draft";
  const isReview = status === "review";
  const isApproved = status === "approved";
  const isArchived = status === "archived";

  if (isArchived) {
    return (
      <p className="text-sm text-muted-foreground">Archived — read-only.</p>
    );
  }

  return (
    <>
      <div className="flex flex-wrap gap-2">
        {isDraft ? (
          <Button
            disabled={isPending}
            onClick={() => submitReviewMutation.mutate()}
          >
            {submitReviewMutation.isPending ? "Submitting…" : "Submit for Review"}
          </Button>
        ) : null}
        {isReview ? (
          <Button disabled={isPending} onClick={() => approveMutation.mutate()}>
            {approveMutation.isPending ? "Approving…" : "Approve"}
          </Button>
        ) : null}
        {isReview || isApproved ? (
          <Button
            variant="destructive"
            disabled={isPending}
            onClick={() => setArchiveOpen(true)}
          >
            Archive
          </Button>
        ) : null}
      </div>



      <ConfirmDialog

        open={archiveOpen}

        title="Archive asset?"

        description={`"${assetTitle}" will be archived. This does not publish or schedule anything.`}

        confirmLabel="Archive"

        destructive

        loading={archiveMutation.isPending}

        onCancel={() => {

          if (!archiveMutation.isPending) {

            setArchiveOpen(false);

          }

        }}

        onConfirm={() => {

          archiveMutation.mutate(undefined, {

            onSuccess: () => setArchiveOpen(false),

          });

        }}

      />

    </>

  );

}



export function AssetEditorView({ assetId }: AssetEditorViewProps) {

  const { hasApiKey, hasProjectId, projectId, isProjectScopeReady } =

    useEnvConfig();



  const assetQuery = useQuery({

    queryKey: queryKeys.contentAsset(projectId ?? "", assetId),

    queryFn: () => fetchContentAsset(projectId!, assetId),

    enabled: isProjectScopeReady,

  });



  const versionsQuery = useQuery({

    queryKey: queryKeys.contentAssetVersions(projectId ?? "", assetId),

    queryFn: () => fetchContentAssetVersions(projectId!, assetId),

    enabled: isProjectScopeReady && assetQuery.isSuccess,

  });



  if (!hasApiKey) {

    return (

      <div className="flex flex-col gap-6">

        <PageHeader title="Asset Editor" />

        <ApiKeyMissing />

      </div>

    );

  }



  if (!hasProjectId) {

    return (

      <div className="flex flex-col gap-6">

        <PageHeader title="Asset Editor" />

        <ProjectIdMissing />

      </div>

    );

  }



  return (

    <div className="flex flex-col gap-6">

      <QueryStatus query={assetQuery}>

        {(asset) => (

          <>

            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">

              <PageHeader

                title={asset.title}

                description={`${asset.type} · ${asset.status} · v${asset.current_version_number}`}

              />

              <AssetActionBar

                projectId={projectId!}

                assetId={assetId}

                assetTitle={asset.title}

                status={asset.status}

                campaignId={asset.campaign_id}

              />

            </div>

          </>

        )}

      </QueryStatus>



      <QueryStatus query={assetQuery}>

        {(asset) => {

          if (asset.status === "draft") {

            return <AssetDraftRevisionEditor projectId={projectId!} asset={asset} />;

          }

          if (asset.status === "review") {
            return (
              <section className="rounded-lg border border-border p-4">
                <p className="text-sm text-muted-foreground">
                  In review — edit is locked until approved or archived.
                </p>
              </section>
            );
          }

          if (asset.status === "approved") {
            return (
              <>
                <AssetApprovedRevisionPanel projectId={projectId!} asset={asset} />
                <AssetMediaBriefPanel projectId={projectId!} asset={asset} />
                <AssetPublicationPackagesPanel projectId={projectId!} asset={asset} />
              </>
            );
          }

          if (asset.status === "archived") {

            return (

              <section className="rounded-lg border border-border p-4">

                <p className="text-sm text-muted-foreground">

                  This asset is archived. Content is read-only.

                </p>

              </section>

            );

          }

          return null;

        }}

      </QueryStatus>



      <section className="rounded-lg border border-border p-4">

        <h2 className="text-sm font-semibold">Current version</h2>

        <QueryStatus query={assetQuery}>

          {(asset) => (

            <div className="mt-3 space-y-3 text-sm">

              <dl className="grid gap-2 sm:grid-cols-2">

                <div>

                  <dt className="text-muted-foreground">Approved version</dt>

                  <dd>

                    {asset.approved_version_number !== null

                      ? `v${asset.approved_version_number}`

                      : "—"}

                  </dd>

                </div>

                <div>

                  <dt className="text-muted-foreground">Updated</dt>

                  <dd>{formatDateTime(asset.updated_at)}</dd>

                </div>

              </dl>

              {asset.body ? (

                <pre className="max-h-96 overflow-auto rounded-md bg-muted/40 p-3 text-xs whitespace-pre-wrap">

                  {asset.body}

                </pre>

              ) : (

                <p className="text-muted-foreground">No body content.</p>

              )}

            </div>

          )}

        </QueryStatus>

      </section>



      <QueryStatus query={assetQuery}>

        {(asset) =>

          asset.status === "approved" &&

          asset.approved_version_number !== null ? (

            <SchedulePublicationForm

              projectId={projectId!}

              assetId={assetId}

              campaignId={asset.campaign_id}

              approvedVersionNumber={asset.approved_version_number}

            />

          ) : null

        }

      </QueryStatus>



      <QueryStatus

        query={versionsQuery}

        empty={

          versionsQuery.isSuccess && (versionsQuery.data?.length ?? 0) === 0

        }

        emptyTitle="No versions"

      >

        {(versions) => (

          <QueryStatus query={assetQuery}>

            {(asset) => (

              <AssetVersionHistory

                projectId={projectId!}

                assetId={assetId}

                versions={versions}

                currentVersionNumber={asset.current_version_number}

              />

            )}

          </QueryStatus>

        )}

      </QueryStatus>

    </div>

  );

}

