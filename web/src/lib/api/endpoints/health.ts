import { apiJson } from "@/lib/api/client";

export type HealthResponse = {
  status: string;
  app: string;
  database: string;
  redis: string;
};

export function fetchHealth() {
  return apiJson<HealthResponse>("/health");
}

export function fetchVersion() {
  return apiJson<{ name: string; version: string; environment: string }>("/version");
}
