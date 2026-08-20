export interface DocumentInfo {
  document_type?: string;
  process_intent?: string;
  [key: string]: any;
}

export interface ExtractionInfo {
  fields?: Record<string, any>;
  [key: string]: any;
}

export interface LegalEvidence {
  law_name?: string;
  law_number?: string;
  article?: string;
  text?: string;
  score?: number;
  [key: string]: any;
}

export interface LegalAnalysis {
  evidence?: LegalEvidence[];
  [key: string]: any;
}

export interface MissingFields {
  missing_fields?: string[];
  needs_human_review?: boolean;
  [key: string]: any;
}

export interface SummaryInfo {
  short_summary?: string;
  [key: string]: any;
}

export interface RoutingInfo {
  recommended_unit?: string;
  confidence?: number;
  reason?: string;
  requires_human_review?: boolean;
  [key: string]: any;
}

export interface DraftInfo {
  draft_type?: string;
  draft_text?: string;
  official_render?: string;
  [key: string]: any;
}

export interface QualityIssue {
  field?: string;
  issue?: string;
  severity?: string;
  [key: string]: any;
}

export interface QualityInfo {
  status?: string;
  issues?: QualityIssue[];
  [key: string]: any;
}

export interface HumanReview {
  status?: string; // "pending_review", "approved", "rejected"
  required?: boolean;
  reject_reason?: string;
  [key: string]: any;
}

export interface AuditEvent {
  event: string;
  timestamp: string;
  message: string;
}

export interface DocumentState {
  document_id: string;
  raw_text: string;
  analysis_id?: string;
  
  document: DocumentInfo;
  extraction: ExtractionInfo;
  legal_analysis: LegalAnalysis;
  missing_fields: MissingFields;
  summary: SummaryInfo;
  routing: RoutingInfo;
  draft: DraftInfo;
  quality: QualityInfo;
  human_review: HumanReview;
  
  warnings: string[];
  node_timings: Record<string, number>;
  audit_history?: AuditEvent[];
  
  // allow legacy fields just in case
  [key: string]: any;
}
