import { caseRequest } from "./caseHttp";

export interface DemoPersona { user_key: string; name: string; role: string; institution_id: string; department_code: string }
export interface DemoScenario { key: string; title: string; institution_id: string; prepared: boolean }
export interface PreparedScenario { scenario_key: string; created: boolean; case: { id: string; tracking_code: string }; citizen_url: string }

export const demoApi = {
  personas: () => caseRequest<{ items: DemoPersona[] }>("/api/demo/personas"),
  scenarios: (token: string) => caseRequest<{ items: DemoScenario[] }>("/api/demo/scenarios", token),
  prepare: (token: string, key: string) => caseRequest<PreparedScenario>(`/api/demo/scenarios/${key}/prepare`, token, { method: "POST" }),
  reset: (token: string) => caseRequest<{ deleted_demo_cases: number }>("/api/demo/scenarios/reset", token, { method: "POST" }),
  citizenAccess: (token: string, caseId: string) => caseRequest<{ citizen_url: string }>(`/api/demo/cases/${caseId}/citizen-access`, token),
};
