export type PublicationPackage = {
  id: string;
  owner_id: string;
  project_id: string;
  content_asset_id: string;
  source_content_asset_id: string;
  channel: string;
  title: string;
  body: string;
  cta: string | null;
  metadata?: Record<string, unknown>;
  status: string;
  created_at: string;
  updated_at: string;
};

export type CreatePublicationPackageFromAssetResponse = {
  content_asset_id: string;
  publication_package_id: string;
  publication_package_status: string;
  channel: string;
};
