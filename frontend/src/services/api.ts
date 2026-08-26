import { DocumentState } from "../types";
import type { AnalysesResponse, ReviewQueueResponse } from "../types/analysis";
import type { ROISummaryResponse } from "../types/metrics";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

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
  async checkSystemReady(): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/ready`);
    if (!response.ok) {
      throw new Error(`HTTP Error: ${response.status}`);
    }
    return response.json();
  },

  async analyzeText(text: string): Promise<DocumentState> {
    const response = await fetch(`${API_BASE_URL}/api/documents/analyze-text`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ text }),
    });

    if (!response.ok) {
      return throwApiError(response);
    }

    return response.json();
  },

  async uploadDocument(file: File): Promise<DocumentState> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_BASE_URL}/api/documents/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      return throwApiError(response);
    }

    return response.json();
  },

  async approveAnalysis(analysisId: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/api/analysis/${analysisId}/approve`, {
      method: "POST",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail?.message || `HTTP Error: ${response.status}`);
    }

    return response.json();
  },

  async rejectAnalysis(analysisId: string, reason: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/api/analysis/${analysisId}/reject`, {
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

  async getAnalyses(params?: { limit?: number; offset?: number; status?: string }): Promise<AnalysesResponse> {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.offset) searchParams.set('offset', String(params.offset));
    if (params?.status) searchParams.set('status', params.status);

    const response = await fetch(`${API_BASE_URL}/api/analyses?${searchParams}`);
    if (!response.ok) {
      throw new Error(`HTTP Error: ${response.status}`);
    }
    return response.json();
  },

  async getAnalysis(analysisId: string): Promise<DocumentState> {
    const response = await fetch(`${API_BASE_URL}/api/analysis/${analysisId}`);
    if (!response.ok) {
      return throwApiError(response);
    }
    return response.json();
  },

  async getRoiSummary(): Promise<ROISummaryResponse> {
    const response = await fetch(`${API_BASE_URL}/api/roi/summary`);
    if (!response.ok) {
      throw new Error(`HTTP Error: ${response.status}`);
    }
    return response.json();
  },

  async getInstitutions(): Promise<{ institutions: string[]; count: number }> {
    const response = await fetch(`${API_BASE_URL}/api/institutions`);
    if (!response.ok) {
      throw new Error(`HTTP Error: ${response.status}`);
    }
    return response.json();
  },

  async editAnalysis(analysisId: string, subject: string, body: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/api/analysis/${analysisId}/edit`, {
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

  async getPendingReviews(params?: { limit?: number; offset?: number }): Promise<ReviewQueueResponse> {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.offset) searchParams.set('offset', String(params.offset));

    const response = await fetch(`${API_BASE_URL}/api/reviews/pending?${searchParams}`);
    if (!response.ok) {
      throw new Error(`HTTP Error: ${response.status}`);
    }
    return response.json();
  },

  getDocxUrl(analysisId: string): string {
    return `${API_BASE_URL}/api/analysis/${analysisId}/export/docx`;
  },
};
