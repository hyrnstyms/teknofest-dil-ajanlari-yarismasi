import type { PendingAction, ActionResult } from "../components/chat/chatTypes";
import { caseRequest } from "./caseHttp";

export interface CaseActionAdapter {
  executeAction(action: PendingAction): Promise<ActionResult>;
}

export function createCaseActionAdapter(token: string): CaseActionAdapter {
  return {
    async executeAction(action: PendingAction): Promise<ActionResult> {
      const result = await caseRequest<ActionResult>(
        "/api/copilot/actions/confirm",
        token,
        { method: "POST", body: JSON.stringify(action) },
      );
      window.dispatchEvent(
        new CustomEvent("evrag:case-updated", { detail: { caseId: action.case_id } }),
      );
      return result;
    },
  };
}
