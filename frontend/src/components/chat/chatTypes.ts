import type { DraftInfo } from "../../types";

export type ChatMode =
  | "kilavuz"
  | "mevzuat"
  | "kucuk_sohbet"
  | "taslak_duzenleme"
  | "active_document"
  | "institution";

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
  type: string;
  case_id: string;
  payload: Record<string, any>;
  confirmation_required: boolean;
  confirmation_text: string;
}

export interface ActionResult {
  success: boolean;
  message: string;
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
