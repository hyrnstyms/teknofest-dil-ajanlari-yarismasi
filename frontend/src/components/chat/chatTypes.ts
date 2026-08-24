import type { DraftInfo } from "../../types";

export type ChatMode =
  | "kilavuz"
  | "mevzuat"
  | "kucuk_sohbet"
  | "taslak_duzenleme";

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

export interface ChatApiResponse {
  mode: ChatMode;
  status: ChatStatus;
  sohbet_yaniti: string;
  updated_draft: DraftInfo | null;
  validation_errors: ChatValidationIssue[];
  validation_warnings: ChatValidationIssue[];
}

export interface ChatUiMessage {
  id: string;
  role: "user" | "bot";
  text: string;
  mode?: ChatMode;
  status?: ChatStatus;
  validationErrors?: ChatValidationIssue[];
}
