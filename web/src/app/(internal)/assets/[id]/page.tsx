import { AssetEditorView } from "@/components/views/asset-editor-view";

type AssetEditorPageProps = {
  params: Promise<{ id: string }>;
};

export default async function AssetEditorPage({ params }: AssetEditorPageProps) {
  const { id } = await params;
  return <AssetEditorView assetId={id} />;
}
