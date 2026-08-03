import { StatusBadge } from "@/components/ui/status-badge";

type CampaignStatusBadgeProps = {
  status: string;
};

export function CampaignStatusBadge({ status }: CampaignStatusBadgeProps) {
  return <StatusBadge status={status} strikethroughWhenArchived />;
}
