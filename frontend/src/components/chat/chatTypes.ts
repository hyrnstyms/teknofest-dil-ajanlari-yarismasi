import type { DraftInfo } from "../../types";

export type ChatMode =
  | "kilavuz"
  | "mevzuat"
  | "kucuk_sohbet"
  | "taslak_duzenleme"
  | "active_document"
  | "institution"
  | "workflow_action"
  | "clarification_action"
  | "inbox_query"
  | "case_query_state";

export type ChatStatus =
  | "answered"
  | "applied"
  | "rejected"
  | "no_change"
  | "error";

export interface ChatValidationIssue {
  kural_kodu?: string;
  mesaj?: string;
  madde_ref?: string;
}

export interface ChatSource {
  law_number: string;
  title: string;
  madde_no: string;
  excerpt: string;
  score: number;
}

export interface ChatApiResponse {
  mode: ChatMode;
  status: ChatStatus;
  sohbet_yaniti: string;
  updated_draft: DraftInfo | null;
  validation_errors: ChatValidationIssue[];
  validation_warnings: ChatValidationIssue[];
}

export interface PendingAction {
  action_id: string;
  type:
    | "ROUTE_CASE"
    | "START_CASE"
    | "REQUEST_CITIZEN_INFO"
    | "CREATE_OFFICIAL_DRAFT"
    | "APPROVE_DRAFT"
    | "FINALIZE_CASE";
  case_id: string;
  payload: Record<string, any>;
  confirmation_required: boolean;
  confirmation_text: string;
}

export interface ActionResult {
  success: boolean;
  message: string;
  case?: Record<string, unknown>;
}

export interface ChatUiMessage {
  id: string;
  role: "user" | "bot";
  text: string;
  mode?: ChatMode;
  status?: ChatStatus;
  validationErrors?: ChatValidationIssue[];
  isStreaming?: boolean;
  sources?: ChatSource[];
  pendingAction?: PendingAction;
  actionResult?: ActionResult;
  actionStatus?: "idle" | "submitting" | "resolved";
}
