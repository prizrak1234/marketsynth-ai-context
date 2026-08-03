import { StatusBadge } from "@/components/ui/status-badge";

type ChannelStatusBadgeProps = {
  status: string;
};

export function ChannelStatusBadge({ status }: ChannelStatusBadgeProps) {
  return <StatusBadge status={status} />;
}
