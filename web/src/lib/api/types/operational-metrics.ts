export type ReviewQueueMetrics = {
  pending_assets: number;
};

export type OperationalMetricsResponse = {
  project_id: string | null;
  window: string;
  agent_runs: Record<string, number>;
  graph_runs: Record<string, number>;
  handoff: Record<string, unknown>;
  outbox: Record<string, unknown>;
  webhooks: Record<string, unknown>;
  execution: Record<string, unknown>;
  replay: Record<string, unknown>;
  publishing: Record<string, unknown>;
  campaigns: Record<string, number>;
  review_queue: ReviewQueueMetrics;
  redis: {
    available: boolean;
    queue_depth: number;
    dlq_depth: number;
    error: string | null;
  };
};
