import { fetchApi } from "./api";
import { SystemStatusResponse, ROISummaryResponse } from "../types/metrics";

export async function getSystemStatus(): Promise<SystemStatusResponse> {
  return fetchApi<SystemStatusResponse>("/api/system/status");
}

export async function getROISummary(): Promise<ROISummaryResponse> {
  return fetchApi<ROISummaryResponse>("/api/roi/summary");
}
