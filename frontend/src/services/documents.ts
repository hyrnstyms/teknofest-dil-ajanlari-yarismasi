import { fetchApi } from "./api";
import { AnalysisResponse } from "../types/analysis";

export async function analyzeText(text: string): Promise<AnalysisResponse> {
  return fetchApi<AnalysisResponse>("/api/documents/analyze-text", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ text })
  });
}

export async function uploadDocument(file: File): Promise<AnalysisResponse> {
  const formData = new FormData();
  formData.append("file", file);
  
  return fetchApi<AnalysisResponse>("/api/documents/upload", {
    method: "POST",
    body: formData
  });
}
