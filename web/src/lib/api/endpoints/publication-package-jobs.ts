import { apiJson } from "@/lib/api/client";
import type {
  PublicationPackageJob,
  SchedulePublicationPackageJobPayload,
} from "@/lib/api/types/publication-package-jobs";

function jobsPath(projectId: string, suffix = "") {
  return `/projects/${projectId}/publication-package-jobs${suffix}`;
}

export function fetchPublicationPackageJobs(
  projectId: string,
  params?: { publication_package_id?: string },
) {
  const search = new URLSearchParams();
  if (params?.publication_package_id) {
    search.set("publication_package_id", params.publication_package_id);
  }
  const query = search.toString();
  return apiJson<PublicationPackageJob[]>(
    `${jobsPath(projectId)}${query ? `?${query}` : ""}`,
  );
}

export function fetchPublicationPackageJob(projectId: string, jobId: string) {
  return apiJson<PublicationPackageJob>(jobsPath(projectId, `/${jobId}`));
}

export function executePublicationPackageJobDryRun(projectId: string, jobId: string) {
  return apiJson<PublicationPackageJob>(
    jobsPath(projectId, `/${jobId}/execute-dry-run`),
    { method: "POST" },
  );
}

export function schedulePublicationPackageJob(
  projectId: string,
  jobId: string,
  payload: SchedulePublicationPackageJobPayload,
) {
  return apiJson<PublicationPackageJob>(jobsPath(projectId, `/${jobId}/schedule`), {
    method: "POST",
    body: payload,
  });
}

export function createPublicationPackageJob(
  projectId: string,
  packageId: string,
  channelId: string,
  idempotencyKey?: string,
) {
  const search = new URLSearchParams({ channel_id: channelId });
  return apiJson<PublicationPackageJob>(
    `/projects/${projectId}/publication-packages/${packageId}/publication-jobs?${search}`,
    {
      method: "POST",
      headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined,
    },
  );
}
