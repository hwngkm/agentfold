import { apiGet } from "./http";

// Khớp `GET /health` trong contracts/openapi.json.
export type Health = { status: string; env: string };

export function getHealth(): Promise<Health> {
  return apiGet<Health>("/health");
}
