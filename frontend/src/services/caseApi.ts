import type {
  CaseActionResult,
  CaseDraft,
  CaseEvent,
  CaseInboxResponse,
  CaseRecord,
  Department,
  DepartmentAction,
} from "../types/case";
import { caseRequest } from "./caseHttp";

interface CaseAggregateWire {
  case: Omit<CaseRecord, "title" | "current_department_name" | "timeline" | "department_actions" | "drafts" | "permissions"> & { current_department_name?: string };
  permissions: string[];
  events: Array<CaseEvent & { actor_user_id?: string | null; payload?: Record<string, unknown> }>;
  department_actions: DepartmentAction[];
  drafts: Array<{ id: string; draft_type: CaseDraft["draft_type"]; status: CaseDraft["draft_status"]; content: { subject?: string; body?: string; recipient?: string }; created_by_user_id?: string; grounded_action_id?: string | null }>;
  analysis?: {
    summary?: { short_summary?: string; structured_summary?: { subject?: string; request?: string } };
    routing?: CaseRecord["routing_recommendation"];
    clarification?: Omit<NonNullable<CaseRecord["clarification"]>, "question_type" | "options"> & {
      question_type: "free_text" | "choice" | "single_choice";
      options: Array<string | { value: string; label: string }>;
    };
  } | null;
  deadline?: CaseRecord["deadline"];
}

function summaryTitle(aggregate: CaseAggregateWire): string {
  const summary = aggregate.analysis?.summary;
  return summary?.short_summary
    || summary?.structured_summary?.subject
    || `Başvuru ${aggregate.case.tracking_code}`;
}

function normalizeAggregate(aggregate: CaseAggregateWire): CaseRecord {
  const routing = aggregate.analysis?.routing;
  const clarification = aggregate.analysis?.clarification;
  return {
    ...aggregate.case,
    title: summaryTitle(aggregate),
    current_department_name: aggregate.case.current_department_name || aggregate.case.current_department_code,
    routing_recommendation: routing ? {
      ...routing,
      reason: routing.reason || "AI sınıflandırması ve kurum sorumluluk alanı eşleşmesi.",
      evidence: routing.evidence || [],
      alternatives: routing.alternatives || [],
      requires_human_review: routing.requires_human_review !== false,
    } : undefined,
    clarification: clarification ? {
      ...clarification,
      question_type: clarification.question_type === "choice" ? "single_choice" : clarification.question_type,
      requested_fields: clarification.requested_fields || [],
      options: (clarification.options || []).map((option) => typeof option === "string" ? { value: option, label: option.replaceAll("_", " ") } : option),
    } : undefined,
    analysis_summary: aggregate.analysis?.summary?.short_summary
      || aggregate.analysis?.summary?.structured_summary?.request,
    deadline: aggregate.deadline,
    timeline: aggregate.events.map((event) => ({ ...event, actor_name: event.actor_name })),
    department_actions: aggregate.department_actions,
    drafts: aggregate.drafts.map((draft) => ({
      id: draft.id,
      draft_type: draft.draft_type,
      draft_status: draft.status,
      recipient: draft.content?.recipient,
      subject: draft.content?.subject || "Başvurunuz Hk.",
      body: draft.content?.body || "",
      prepared_by_department: aggregate.case.current_department_code,
      ai_generated: true,
    })),
    permissions: aggregate.permissions,
  };
}

async function refresh(token: string, id: string): Promise<CaseRecord> {
  const aggregate = await caseRequest<CaseAggregateWire>(`/api/cases/${id}`, token);
  return normalizeAggregate(aggregate);
}

async function mutate(
  token: string,
  item: CaseRecord,
  path: string,
  body: Record<string, unknown>,
  message: string,
): Promise<CaseActionResult> {
  const mutation = await caseRequest<{ case?: CaseRecord } | CaseRecord>(path, token, {
    method: "POST",
    body: JSON.stringify(body),
  });
  const testOrCompatibleCase = "case" in mutation ? mutation.case : undefined;
  return {
    case: testOrCompatibleCase?.permissions ? testOrCompatibleCase : await refresh(token, item.id),
    message,
  };
}

export const caseApi = {
  inbox: async (token: string, query = ""): Promise<CaseInboxResponse> => {
    const response = await caseRequest<CaseInboxResponse>(
      `/api/cases/inbox${query ? `?${query}` : ""}`,
      token,
    );
    return {
      ...response,
      items: response.items.map((item) => ({
        ...item,
        title: item.title || `Başvuru ${item.tracking_code}`,
        current_department_name: item.current_department_name || item.current_department_code,
        timeline: item.timeline || [],
        department_actions: item.department_actions || [],
        drafts: item.drafts || [],
        permissions: item.permissions || [],
      })),
    };
  },
  get: refresh,
  acceptReview: (token: string, item: CaseRecord) => mutate(
    token,
    item,
    `/api/cases/${item.id}/accept-review`,
    { expected_version: item.version, confirmed: true },
    "İlk inceleme onaylandı; dosya yönlendirmeye hazır.",
  ),
  route: (token: string, item: CaseRecord, departmentCode: string) => mutate(
    token,
    item,
    `/api/cases/${item.id}/route`,
    { department_code: departmentCode, expected_version: item.version, confirmed: true },
    "Dosya ilgili birime yönlendirildi.",
  ),
  start: (token: string, item: CaseRecord) => mutate(
    token,
    item,
    `/api/cases/${item.id}/start`,
    { expected_version: item.version, confirmed: true },
    "Dosya işleme alındı.",
  ),
  departmentAction: (
    token: string,
    item: CaseRecord,
    input: Omit<DepartmentAction, "id" | "verified" | "recorded_by_user_id" | "created_at">,
  ) => mutate(
    token,
    item,
    `/api/cases/${item.id}/department-action`,
    { ...input, expected_version: item.version, confirmed: true },
    "Doğrulanmış kurum işlem sonucu kaydedildi.",
  ),
  requestCitizenInfo: (token: string, item: CaseRecord) => mutate(
    token,
    item,
    `/api/cases/${item.id}/citizen-requests`,
    { ...item.clarification, expected_version: item.version, confirmed: true },
    "Eksik bilgi talebi kaydedildi.",
  ),
  departments: (token: string, institution: string) => caseRequest<{ institution_id: string; departments: Department[] }>(`/api/institutions/${institution}/departments`, token),
};
