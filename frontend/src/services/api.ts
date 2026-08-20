import { DocumentState } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

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
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail?.message || `HTTP Error: ${response.status}`);
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
