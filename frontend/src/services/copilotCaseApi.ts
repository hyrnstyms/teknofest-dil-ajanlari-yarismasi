import type { PendingAction, ActionResult } from "../components/chat/chatTypes";

export interface CaseActionAdapter {
  executeAction(action: PendingAction): Promise<ActionResult>;
}

export const mockCaseActionAdapter: CaseActionAdapter = {
  async executeAction(action: PendingAction): Promise<ActionResult> {
    // Mock API call delay
    await new Promise((res) => setTimeout(res, 1000));
    
    // Always return success but with a clear demo warning
    return {
      success: true,
      message: "[DEMO] İşlem simüle edildi — gerçek Case Engine entegrasyonu bekleniyor.",
    };
  }
};
