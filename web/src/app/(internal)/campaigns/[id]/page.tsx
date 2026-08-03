import { CampaignDetailView } from "@/components/views/campaign-detail-view";

type CampaignDetailPageProps = {
  params: Promise<{ id: string }>;
};

export default async function CampaignDetailPage({ params }: CampaignDetailPageProps) {
  const { id } = await params;
  return <CampaignDetailView campaignId={id} />;
}
