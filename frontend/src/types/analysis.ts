export interface DocumentInfo {
  document_type: string;
  process_intent: string;
  classification_mode: string;
  evidence: Array<{ field: string; text: string }>;
}

export interface ExtractionResult {
  fields: Record<string, any>; // Usually { value: string, evidence?: string } but can vary
  unknown_fields: string[];
  missing_fields: string[];
}

export interface MissingFieldResult {
  required_fields: string[];
  present_fields: string[];
  missing_fields: string[];
  uncertain_fields: string[];
  warnings: string[];
  field_results?: Record<string, { status: string; value?: any; reason?: string }>;
  needs_human_review?: boolean;
}

export interface LegalEvidence {
  metadata: {
    law_name?: string;
    law_number?: string;
    item_number?: string;
    source_type?: string;
  };
  text?: string;
  evidence?: string; // from v2
  retrieval_score?: number;
}

export interface LegalAnalysis {
  evidences?: LegalEvidence[];
  evidence?: string[]; // from v2
  sources?: LegalEvidence[]; // from v2
  warnings?: string[];
}

export interface RoutingResult {
  recommended_unit: string | null;
  reason: string;
  routing_score?: number;
  score_type?: string;
  registry_source?: string;
  warnings?: string[];
  ranked_units?: Array<{ name: string; score: number }>;
  score_breakdown?: Array<{ signal: string; value: number }>;
  alternative_units?: string[];
  ambiguity_reason?: string;
  routing_confidence_type?: string;
  needs_human_review?: boolean;
}

export interface DraftResult {
  rendered_text?: string;
  draft_text?: string;
  draft?: {
    subject?: string;
    body?: string;
  };
  subject?: string;
  edited_draft?: {
    subject: string;
    body: string;
  };
  draft_generation_mode?: string;
  requires_human_approval?: boolean;
  official_render?: {
    success: boolean;
    attempted: boolean;
    missing_fields?: string[];
  };
}

export interface QualityCheck {
  name: string;
  status: "pass" | "warning" | "fail";
  message: string;
}

export interface QualityResult {
  status: "pass" | "warning" | "fail";
  checks?: QualityCheck[];
  requires_human_review?: boolean;
  issues?: string[];
}

export interface HumanReview {
  required: boolean;
  status: string; // pending_review, approved, edited, rejected
  reject_reason?: string;
  original_draft?: {
    subject?: string;
    draft_text?: string;
  };
}

export interface AuditEvent {
  event: string;
  timestamp: string;
  message?: string;
}

export interface SummaryResult {
  short_summary?: string;
  structured_summary?: Record<string, any>;
  summary_mode?: string;
  source_map?: Record<string, string>;
  warnings?: string[];
  needs_human_review?: boolean;
}

export interface AnalysisResponse {
  analysis_id: string;
  document: DocumentInfo;
  extraction: ExtractionResult;
  missing_fields: MissingFieldResult;
  legal_analysis: LegalAnalysis;
  summary: SummaryResult;
  routing: RoutingResult;
  draft: DraftResult;
  quality: QualityResult;
  human_review: HumanReview;
  audit_history?: AuditEvent[];
  created_at?: string;
  node_timings?: Record<string, { duration_ms: number; status: string }>;
}

export interface AnalysisListItem {
  analysis_id: string;
  document_id: string;
  document_type?: string;
  process_intent?: string;
  subject?: string;
  recommended_unit?: string;
  human_review_status?: string;
  quality_status?: string;
  created_at?: string;
  total_processing_ms?: number;
}

export interface AnalysesResponse {
  items: AnalysisListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface ReviewQueueItem {
  analysis_id: string;
  document_type?: string;
  process_intent?: string;
  subject?: string;
  recommended_unit?: string;
  quality_status?: string;
  review_reasons: string[];
  created_at?: string;
}

export interface ReviewQueueResponse {
  items: ReviewQueueItem[];
  total: number;
  limit: number;
  offset: number;
}
