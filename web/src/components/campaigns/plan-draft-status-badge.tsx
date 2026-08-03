import { StatusBadge } from "@/components/ui/status-badge";

type PlanDraftStatusBadgeProps = {
  status: string;
};

export function PlanDraftStatusBadge({ status }: PlanDraftStatusBadgeProps) {
  return <StatusBadge status={status} strikethroughWhenArchived />;
}
