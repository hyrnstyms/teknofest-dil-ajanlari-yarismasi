import { DocumentState } from "../types";
import type {
  AnalysesResponse,
  AnalysisListItem as AnalysisItem,
  ReviewQueueItem,
  ReviewQueueResponse,
} from "../types/analysis";
import type { ROISummaryResponse } from "../types/metrics";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
function requestTimeout(input: RequestInfo | URL): number {
  const target = String(input);
  if (target.includes("/api/documents/")) return 180_000;
  if (target.endsWith("/ready")) return 90_000;
  return 30_000;
}

async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), requestTimeout(input));
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiRequestError(
        "analysis_timeout",
        "İstek zaman aşımına uğradı. Lütfen tekrar deneyin.",
        408,
      );
    }
    throw error;
  } finally {
    window.clearTimeout(timer);
  }
}

export interface InstitutionUiConfig {
  title?: string;
  description?: string;
  upload_label?: string;
  institution_display_name?: string;
}

export interface InstitutionOption {
  id: string;
  label: string;
  ui_config: InstitutionUiConfig;
}

export type RoiSummary = ROISummaryResponse;
export type AnalysisListItem = AnalysisItem;
export type PendingReviewItem = ReviewQueueItem;
export interface SystemStatus {
  api?: string;
  llm_provider?: string;
  llm_model?: string;
  llm_models?: Record<string, string>;
  embedding_model?: string;
  embedding_dimension?: number;
  qdrant?: {
    total_points?: number;
    legal_points?: number;
    document_points?: number;
    index_status?: string;
    message?: string;
  };
}

type AnalysisQuery = number | { limit?: number; offset?: number; status?: string };
type ReviewQuery = number | { limit?: number; offset?: number };

export class ApiRequestError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(
    code: string,
    message: string,
    status: number,
  ) {
    super(message);
    this.name = "ApiRequestError";
    this.code = code;
    this.status = status;
  }
}

async function throwApiError(response: Response): Promise<never> {
  const errorData = await response.json().catch(() => ({}));
  const detail = errorData?.detail;
  throw new ApiRequestError(
    detail?.code || `http_${response.status}`,
    detail?.message || `HTTP Error: ${response.status}`,
    response.status,
  );
}

export const api = {
  async getSystemStatus(): Promise<SystemStatus> {
    const response = await apiFetch(API_BASE_URL + "/api/system/status");
    if (!response.ok) {
      return throwApiError(response);
    }
    return response.json();
  },
  async checkSystemReady(): Promise<any> {
    const response = await apiFetch(`${API_BASE_URL}/ready`);
    if (!response.ok) {
      throw new Error(`HTTP Error: ${response.status}`);
    }
    return response.json();
  },

  async listInstitutionOptions(): Promise<InstitutionOption[]> {
    const response = await apiFetch(`${API_BASE_URL}/api/institutions`);
    if (!response.ok) {
      return throwApiError(response);
    }
    const data = await response.json();
    return data.institution_options || [];
  },

  async analyzeText(text: string, institution?: string): Promise<DocumentState> {
    const response = await apiFetch(`${API_BASE_URL}/api/documents/analyze-text`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ text, ...(institution ? { institution } : {}) }),
    });

    if (!response.ok) {
      return throwApiError(response);
    }

    return response.json();
  },

  async uploadDocument(file: File, institution?: string): Promise<DocumentState> {
    const formData = new FormData();
    formData.append("file", file);
    if (institution) formData.append("institution", institution);

    const response = await apiFetch(`${API_BASE_URL}/api/documents/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      return throwApiError(response);
    }

    return response.json();
  },

  async approveAnalysis(analysisId: string): Promise<any> {
    const response = await apiFetch(`${API_BASE_URL}/api/analysis/${analysisId}/approve`, {
      method: "POST",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail?.message || `HTTP Error: ${response.status}`);
    }

    return response.json();
  },

  async rejectAnalysis(analysisId: string, reason: string): Promise<any> {
    const response = await apiFetch(`${API_BASE_URL}/api/analysis/${analysisId}/reject`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ reason }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail?.message || `HTTP Error: ${response.status}`);
    }

    return response.json();
  },

  async transferAnalysis(analysisId: string): Promise<any> {
    const response = await apiFetch(
      `${API_BASE_URL}/api/analyses/${analysisId}/transfer`,
      { method: "POST" }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail?.message || `HTTP Error: ${response.status}`);
    }

    return response.json();
  },

  async getAnalyses(query?: AnalysisQuery): Promise<AnalysesResponse> {
    const params = typeof query === "number" ? { limit: query } : query;
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.offset) searchParams.set('offset', String(params.offset));
    if (params?.status) searchParams.set('status', params.status);

    const response = await apiFetch(`${API_BASE_URL}/api/analyses?${searchParams}`);
    if (!response.ok) {
      throw new Error(`HTTP Error: ${response.status}`);
    }
    return response.json();
  },

  async getAnalysis(analysisId: string): Promise<DocumentState> {
    const response = await apiFetch(`${API_BASE_URL}/api/analysis/${analysisId}`);
    if (!response.ok) {
      return throwApiError(response);
    }
    return response.json();
  },

  async getRoiSummary(): Promise<ROISummaryResponse> {
    const response = await apiFetch(`${API_BASE_URL}/api/roi/summary`);
    if (!response.ok) {
      throw new Error(`HTTP Error: ${response.status}`);
    }
    return response.json();
  },

  async getInstitutions(): Promise<{ institutions: string[]; count: number }> {
    const response = await apiFetch(`${API_BASE_URL}/api/institutions`);
    if (!response.ok) {
      throw new Error(`HTTP Error: ${response.status}`);
    }
    return response.json();
  },

  async editAnalysis(analysisId: string, subject: string, body: string): Promise<any> {
    const response = await apiFetch(`${API_BASE_URL}/api/analysis/${analysisId}/edit`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ subject, body }),
    });

    if (!response.ok) {
      return throwApiError(response);
    }

    return response.json();
  },

  async getPendingReviews(query?: ReviewQuery): Promise<ReviewQueueResponse> {
    const params = typeof query === "number" ? { limit: query } : query;
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.offset) searchParams.set('offset', String(params.offset));

    const response = await apiFetch(`${API_BASE_URL}/api/reviews/pending?${searchParams}`);
    if (!response.ok) {
      throw new Error(`HTTP Error: ${response.status}`);
    }
    return response.json();
  },

  getDocxUrl(analysisId: string): string {
    return `${API_BASE_URL}/api/analysis/${analysisId}/export/docx`;
  },

  async downloadDocx(analysisId: string): Promise<Blob> {
    const response = await apiFetch(`${API_BASE_URL}/api/analysis/${analysisId}/export/docx`);
    if (!response.ok) {
      return throwApiError(response);
    }
    return response.blob();
  },
};
