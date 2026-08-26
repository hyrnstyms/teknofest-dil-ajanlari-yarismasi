export interface SystemStatusResponse {
  api: string;
  ollama: string;
  llm_model: string;
  embedding_model: string;
  embedding_dimension: number;
  qdrant: {
    total_points: number;
    legal_points: number;
    document_points: number;
    index_status: string;
    message: string;
  };
}

export interface ROISummaryResponse {
  processed_documents: number;
  average_processing_seconds: number;
  human_review_required_rate: number;
  approved_count: number;
  edited_count: number;
  rejected_count: number;
  estimated_saved_seconds: number;
  estimated_saved_percentage?: number | null;
  message?: string;
}
