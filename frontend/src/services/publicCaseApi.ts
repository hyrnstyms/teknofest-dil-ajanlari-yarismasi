import type { PublicCase } from "../types/case";
import { caseRequest } from "./caseHttp";
export const publicCaseApi = {
  get: (code: string, token: string) => caseRequest<PublicCase>(`/api/public/cases/${encodeURIComponent(code)}?token=${encodeURIComponent(token)}`),
  completeInfo: (code: string, token: string, answers: Record<string, string>) => caseRequest<PublicCase>(`/api/public/cases/${encodeURIComponent(code)}/complete-info?token=${encodeURIComponent(token)}`, undefined, { method: "POST", body: JSON.stringify({ answers }) }),
};
