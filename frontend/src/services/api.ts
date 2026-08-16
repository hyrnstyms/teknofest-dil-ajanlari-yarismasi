import { ApiError } from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  try {
    const url = `${API_BASE_URL}${endpoint}`;
    const response = await fetch(url, options);
    
    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch (e) {
        throw { code: "unknown_error", message: `Sunucu hatası: ${response.statusText}` };
      }
      
      const detail = errorData.detail || errorData;
      const apiError: ApiError = {
        code: detail.code || "api_error",
        message: detail.message || "Bilinmeyen bir hata oluştu."
      };
      throw apiError;
    }
    
    return response.json();
  } catch (err: any) {
    if (err.message === "Failed to fetch") {
      throw { code: "network_error", message: "Sunucuya ulaşılamadı. Lütfen bağlantınızı kontrol edin." };
    }
    throw err;
  }
}
