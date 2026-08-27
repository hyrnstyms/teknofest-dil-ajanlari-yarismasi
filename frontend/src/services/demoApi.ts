import { caseRequest } from "./caseHttp";

export interface DemoPersona { user_key: string; name: string; role: string; institution_id: string; department_code: string }
export interface DemoScenario { key: string; title: string; institution_id: string; prepared: boolean; expected_department?: string; source_type?: string }
export interface DemoMeta { title: string; source_type: string; document_type: string; intent: string; expected_department?: string; expected_task?: string; expected_team?: string; requires_field_visit?: boolean; priority?: string; expected_draft_type?: string; is_dis_kurum?: boolean }
export interface PreparedScenario { scenario_key: string; created: boolean; case: { id: string; tracking_code: string }; citizen_url: string; demo_meta?: DemoMeta }

export const demoApi = {
  personas: () => caseRequest<{ items: DemoPersona[] }>("/api/demo/personas"),
  scenarios: (token: string) => caseRequest<{ items: DemoScenario[] }>("/api/demo/scenarios", token),
  prepare: (token: string, key: string) => caseRequest<PreparedScenario>(`/api/demo/scenarios/${key}/prepare`, token, { method: "POST" }),
  reset: (token: string) => caseRequest<{ deleted_demo_cases: number }>("/api/demo/scenarios/reset", token, { method: "POST" }),
  citizenAccess: (token: string, caseId: string) => caseRequest<{ citizen_url: string }>(`/api/demo/cases/${caseId}/citizen-access`, token),
};
