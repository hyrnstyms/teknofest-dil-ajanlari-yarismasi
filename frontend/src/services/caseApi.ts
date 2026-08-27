import type { CaseActionResult, CaseInboxResponse, CaseRecord, Department, DepartmentAction } from "../types/case";
import { caseRequest } from "./caseHttp";
export const caseApi = {
  inbox: (token: string, query = "") => caseRequest<CaseInboxResponse>(`/api/cases/inbox${query ? `?${query}` : ""}`, token),
  get: (token: string, id: string) => caseRequest<CaseRecord>(`/api/cases/${id}`, token),
  route: (token: string, item: CaseRecord, departmentCode: string) => caseRequest<CaseActionResult>(`/api/cases/${item.id}/route`, token, { method: "POST", body: JSON.stringify({ department_code: departmentCode, expected_version: item.version, confirmed: true }) }),
  start: (token: string, item: CaseRecord) => caseRequest<CaseActionResult>(`/api/cases/${item.id}/start`, token, { method: "POST", body: JSON.stringify({ expected_version: item.version, confirmed: true }) }),
  departmentAction: (token: string, item: CaseRecord, input: Omit<DepartmentAction, "id" | "verified" | "recorded_by_user_id" | "created_at">) => caseRequest<CaseActionResult>(`/api/cases/${item.id}/department-action`, token, { method: "POST", body: JSON.stringify({ ...input, expected_version: item.version, confirmed: true }) }),
  requestCitizenInfo: (token: string, item: CaseRecord) => caseRequest<CaseActionResult>(`/api/cases/${item.id}/citizen-requests`, token, { method: "POST", body: JSON.stringify({ ...item.clarification, expected_version: item.version, confirmed: true }) }),
  departments: (token: string, institution: string) => caseRequest<{ institution_id: string; departments: Department[] }>(`/api/institutions/${institution}/departments`, token),
};
