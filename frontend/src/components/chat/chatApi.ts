import type { ChatApiResponse } from "./chatTypes";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function sendChatMessage(
  message: string,
  analysisId?: string,
  institution?: string,
): Promise<ChatApiResponse> {
  const response = await fetch(`${API_BASE_URL}/api/chat/message`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message,
      analysis_id: analysisId || null,
      institution: institution || null,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail?.message || `HTTP Error: ${response.status}`,
    );
  }

  return response.json();
}
