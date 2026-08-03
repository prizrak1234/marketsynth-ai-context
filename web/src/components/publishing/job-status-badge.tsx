import { StatusBadge } from "@/components/ui/status-badge";

type JobStatusBadgeProps = {
  status: string;
};

export function JobStatusBadge({ status }: JobStatusBadgeProps) {
  return <StatusBadge status={status} />;
}
