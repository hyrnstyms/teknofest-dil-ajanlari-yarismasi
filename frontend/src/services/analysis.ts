import { fetchApi } from "./api";
import { AnalysisResponse, AnalysesResponse, ReviewQueueResponse } from '../types/analysis';

export async function getAnalysis(analysisId: string): Promise<AnalysisResponse> {
  return fetchApi<AnalysisResponse>(`/api/analysis/${analysisId}`);
}

export async function approveAnalysis(analysisId: string): Promise<void> {
  return fetchApi<void>(`/api/analysis/${analysisId}/approve`, {
    method: "POST"
  });
}

export async function rejectAnalysis(analysisId: string, reason: string): Promise<void> {
  return fetchApi<void>(`/api/analysis/${analysisId}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason })
  });
}

export async function editAnalysis(analysisId: string, subject: string, body: string): Promise<void> {
  return fetchApi<void>(`/api/analysis/${analysisId}/edit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ subject, body })
  });
}

export async function getAnalyses(params?: {
  limit?: number;
  offset?: number;
  status?: string;
  document_type?: string;
  process_intent?: string;
}): Promise<AnalysesResponse> {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set('limit', params.limit.toString());
  if (params?.offset) searchParams.set('offset', params.offset.toString());
  if (params?.status) searchParams.set('status', params.status);
  if (params?.document_type) searchParams.set('document_type', params.document_type);
  if (params?.process_intent) searchParams.set('process_intent', params.process_intent);
  
  const qs = searchParams.toString();
  return fetchApi<AnalysesResponse>(`/api/analyses${qs ? `?${qs}` : ''}`);
}

export async function getPendingReviews(params?: {
  limit?: number;
  offset?: number;
}): Promise<ReviewQueueResponse> {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set('limit', params.limit.toString());
  if (params?.offset) searchParams.set('offset', params.offset.toString());
  
  const qs = searchParams.toString();
  return fetchApi<ReviewQueueResponse>(`/api/reviews/pending${qs ? `?${qs}` : ''}`);
}
