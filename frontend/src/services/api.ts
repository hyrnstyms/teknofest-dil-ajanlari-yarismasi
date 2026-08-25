import { DocumentState } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

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

export interface RoiSummary {
  processed_documents: number;
  average_processing_seconds: number;
  human_review_required_rate: number;
  approved_count: number;
  edited_count: number;
  rejected_count: number;
  estimated_saved_seconds?: number;
  estimated_saved_percentage?: number | null;
  message?: string;
}

export interface AnalysisListItem {
  analysis_id: string;
  document_id?: string;
  document_type?: string;
  process_intent?: string;
  subject?: string;
  recommended_unit?: string;
  human_review_status?: string;
  quality_status?: string;
  created_at?: string;
  total_processing_ms?: number;
}

export interface PendingReviewItem {
  analysis_id: string;
  document_type?: string;
  process_intent?: string;
  subject?: string;
  recommended_unit?: string;
  quality_status?: string;
  review_reasons?: string[];
  created_at?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail?.message || `HTTP Error: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  async checkSystemReady(): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/ready`);
    if (!response.ok) {
      throw new Error(`HTTP Error: ${response.status}`);
    }
    return response.json();
  },

  async listInstitutionOptions(): Promise<InstitutionOption[]> {
    const response = await fetch(`${API_BASE_URL}/api/institutions`);
    if (!response.ok) {
      throw new Error(`HTTP Error: ${response.status}`);
    }

    const data = await response.json();
    return data.institution_options;
  },

  async getAnalysis(analysisId: string): Promise<DocumentState> {
    const response = await fetch(`${API_BASE_URL}/api/analysis/${analysisId}`);
    return parseResponse<DocumentState>(response);
  },

  async getRoiSummary(): Promise<RoiSummary> {
    const response = await fetch(`${API_BASE_URL}/api/roi/summary`);
    return parseResponse<RoiSummary>(response);
  },

  async getAnalyses(limit = 20): Promise<PaginatedResponse<AnalysisListItem>> {
    const response = await fetch(`${API_BASE_URL}/api/analyses?limit=${limit}&offset=0`);
    return parseResponse<PaginatedResponse<AnalysisListItem>>(response);
  },

  async getPendingReviews(limit = 20): Promise<PaginatedResponse<PendingReviewItem>> {
    const response = await fetch(`${API_BASE_URL}/api/reviews/pending?limit=${limit}&offset=0`);
    return parseResponse<PaginatedResponse<PendingReviewItem>>(response);
  },

  async downloadDocx(analysisId: string): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/api/analysis/${analysisId}/export/docx`);
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail?.message || "DOCX indirilemedi.");
    }
    return response.blob();
  },

  async analyzeText(text: string, institution: string): Promise<DocumentState> {
    const response = await fetch(`${API_BASE_URL}/api/documents/analyze-text`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ text, institution }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail?.message || `HTTP Error: ${response.status}`);
    }

    return response.json();
  },

  async uploadDocument(file: File, institution: string): Promise<DocumentState> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("institution", institution);

    const response = await fetch(`${API_BASE_URL}/api/documents/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail?.message || `HTTP Error: ${response.status}`);
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
};
