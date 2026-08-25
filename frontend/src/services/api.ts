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
