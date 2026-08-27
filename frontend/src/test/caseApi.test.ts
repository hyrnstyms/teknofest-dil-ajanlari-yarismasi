/**
 * EVRAG Person 3 – caseApi action shape tests
 *
 * Verifies that:
 *  - route() sends department_code, expected_version and confirmed:true
 *  - start() sends expected_version and confirmed:true
 *  - departmentAction() includes all human-provided fields plus version/confirmed
 *  - requestCitizenInfo() sends clarification fields plus version/confirmed
 *  - NONE of the above send role, institution or department_code in auth context
 *    (those must come from the token, not the request body)
 *
 * HTTP calls are stubbed; no backend is required.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { caseApi } from '../services/caseApi';
import type { CaseRecord } from '../types/case';

beforeEach(() => {
  vi.restoreAllMocks();
});

function makeFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as Response);
}

const TOKEN = 'test-bearer-token';

const MINIMAL_CASE: CaseRecord = {
  id: 'case-uuid-001',
  tracking_code: 'EVR-2026-000001',
  institution_id: 'belediye',
  title: 'Yol bakım talebi',
  source_type: 'VATANDAS',
  source_channel: 'EBYS',
  originator_type: 'VATANDAS',
  originator_name: 'Ali Yılmaz',
  current_department_code: 'yazi_isleri',
  current_department_name: 'Yazı İşleri Müdürlüğü',
  workflow_status: 'READY_TO_ROUTE',
  received_at: '2026-08-27T09:30:00+03:00',
  created_at: '2026-08-27T09:31:00+03:00',
  updated_at: '2026-08-27T09:31:00+03:00',
  version: 3,
  timeline: [],
  department_actions: [],
  drafts: [],
  permissions: ['ROUTE_CASE'],
  routing_recommendation: {
    recommended_unit: 'Fen İşleri Müdürlüğü',
    recommended_department_code: 'fen_isleri',
    reason: 'Yol bakım',
    evidence: [],
    alternatives: [],
    requires_human_review: true,
  },
};

// ── route() ───────────────────────────────────────────────────────────────────

describe('caseApi.route', () => {
  it('sends department_code, expected_version, confirmed:true', async () => {
    const mockFetch = makeFetch(200, {
      case: { ...MINIMAL_CASE, workflow_status: 'IN_DEPARTMENT', version: 4 },
      message: 'Yönlendirildi',
    });
    vi.stubGlobal('fetch', mockFetch);

    await caseApi.route(TOKEN, MINIMAL_CASE, 'fen_isleri');

    const [, init] = (mockFetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit];
    const body = JSON.parse(init.body as string);

    expect(body.department_code).toBe('fen_isleri');
    expect(body.expected_version).toBe(3);
    expect(body.confirmed).toBe(true);
    expect(body.routing_snapshot.routing.recommended_department_code).toBe('fen_isleri');
  });

  it('does NOT include role or institution_id in request body', async () => {
    const mockFetch = makeFetch(200, {
      case: { ...MINIMAL_CASE },
      message: 'ok',
    });
    vi.stubGlobal('fetch', mockFetch);

    await caseApi.route(TOKEN, MINIMAL_CASE, 'fen_isleri');

    const [, init] = (mockFetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit];
    const body = JSON.parse(init.body as string);

    // role and institution must come from the bearer token, not from request body
    expect(body.role).toBeUndefined();
    expect(body.institution_id).toBeUndefined();
    expect(body.user_id).toBeUndefined();
  });
});

describe('caseApi aggregate integration', () => {
  it('maps Person 1 structured operation, task, priority and timeline fields', async () => {
    const task = {
      id: 'task-1', case_id: MINIMAL_CASE.id, source_case_id: MINIMAL_CASE.id,
      task_type: 'YOL_BAKIM_INCELEME', department_code: 'fen_isleri',
      team_code: 'saha_bakim_ekibi', recommended_role: 'SAHA_EKIBI',
      assigned_user_id: null, status: 'ASSIGNMENT_PENDING',
      created_at: MINIMAL_CASE.created_at, updated_at: MINIMAL_CASE.updated_at,
    };
    vi.stubGlobal('fetch', makeFetch(200, {
      case: { ...MINIMAL_CASE, current_department_code: 'fen_isleri', workflow_status: 'IN_DEPARTMENT' },
      permissions: ['START_CASE'], assignments: [], tasks: [task], assignment: task,
      information_requests: [],
      ai_operation: { task_type: 'YOL_BAKIM_INCELEME', department_code: 'fen_isleri', team_code: 'saha_bakim_ekibi', recommended_role: 'SAHA_EKIBI', requires_field_visit: true },
      priority_assessment: { priority: 'HIGH', priority_reason: 'Acil ifadesi bulundu.' },
      clarification: {},
      events: [{ id: 'e1', event_type: 'CASE_ROUTED', actor_type: 'USER', actor_user_id: 'u1', created_at: MINIMAL_CASE.updated_at, from_status: 'READY_TO_ROUTE', to_status: 'IN_DEPARTMENT', payload: { from_department: 'yazi_isleri', to_department: 'fen_isleri' } }],
      timeline: [{ id: 'e1', event_type: 'CASE_ROUTED', actor_type: 'USER', actor_user_id: 'u1', created_at: MINIMAL_CASE.updated_at, from_status: 'READY_TO_ROUTE', to_status: 'IN_DEPARTMENT', payload: { from_department: 'yazi_isleri', to_department: 'fen_isleri' } }],
      department_actions: [], drafts: [], analysis: null,
      deadline: { applicable: false, due_at: null, risk_level: 'UNKNOWN' },
    }));

    const result = await caseApi.get(TOKEN, MINIMAL_CASE.id);

    expect(result.ai_operation?.team_code).toBe('saha_bakim_ekibi');
    expect(result.assignment?.status).toBe('ASSIGNMENT_PENDING');
    expect(result.priority_assessment?.priority_reason).toBe('Acil ifadesi bulundu.');
    expect(result.timeline[0].label).toBe('Fen İşleri Müdürlüğü birimine havale edildi');
    expect(result.timeline[0].actor_name).toBeUndefined();
  });

  it('posts clarification metadata to the real information-request endpoint', async () => {
    const clarificationCase: CaseRecord = {
      ...MINIMAL_CASE,
      clarification: {
        needs_clarification: true, blocking: true, requested_fields: ['location'],
        question_type: 'free_text', question: 'Konumu paylaşınız.', options: [], resume_target: 'missing_field',
        reason: 'Saha incelemesi için konum gerekir.', target_type: 'VATANDAS', target_name: 'Ali Yılmaz',
        recommended_action: 'CITIZEN_INFORMATION_REQUESTED', required_for_process: true, missing_field: 'location',
      },
    };
    const mockFetch = makeFetch(200, { case: clarificationCase, information_request: { id: 'ir1' } });
    vi.stubGlobal('fetch', mockFetch);

    await caseApi.requestInformation(TOKEN, clarificationCase);

    const [url, init] = (mockFetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit];
    const body = JSON.parse(init.body as string);
    expect(url).toContain(`/api/cases/${MINIMAL_CASE.id}/information-requests`);
    expect(body.requested_fields).toEqual(['location']);
    expect(body.target_type).toBe('VATANDAS');
    expect(body.reason).toBe('Saha incelemesi için konum gerekir.');
    expect(body.confirmed).toBe(true);
  });

  it('maps INTERNAL_DEPARTMENT to the backend KURUM_ICI request contract', async () => {
    const internal: CaseRecord = {
      ...MINIMAL_CASE, source_type: 'KURUM_ICI', originator_type: 'KURUM_ICI',
      clarification: {
        needs_clarification: true, blocking: true, requested_fields: ['attachment'],
        question_type: 'free_text', question: 'Eksik eki iletiniz.', options: [], resume_target: 'missing_field',
        target_type: 'INTERNAL_DEPARTMENT', target_name: 'Yazı İşleri', target_department: 'yazi_isleri',
      },
    };
    const mockFetch = makeFetch(200, { case: internal, information_request: { id: 'ir2' } });
    vi.stubGlobal('fetch', mockFetch);

    await caseApi.requestInformation(TOKEN, internal);

    const [, init] = (mockFetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit];
    const body = JSON.parse(init.body as string);
    expect(body.target_type).toBe('KURUM_ICI');
    expect(body.target_department).toBe('yazi_isleri');
  });
});

// ── start() ───────────────────────────────────────────────────────────────────

describe('caseApi.start', () => {
  it('sends expected_version and confirmed:true', async () => {
    const inDeptCase: CaseRecord = {
      ...MINIMAL_CASE,
      workflow_status: 'IN_DEPARTMENT',
      permissions: ['START_CASE'],
    };
    const mockFetch = makeFetch(200, {
      case: { ...inDeptCase, workflow_status: 'IN_PROGRESS', version: 5 },
      message: 'İşleme alındı',
    });
    vi.stubGlobal('fetch', mockFetch);

    await caseApi.start(TOKEN, inDeptCase);

    const [, init] = (mockFetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit];
    const body = JSON.parse(init.body as string);

    expect(body.expected_version).toBe(inDeptCase.version);
    expect(body.confirmed).toBe(true);
  });
});

// ── departmentAction() ────────────────────────────────────────────────────────

describe('caseApi.departmentAction', () => {
  it('includes action fields, expected_version and confirmed:true', async () => {
    const inProgressCase: CaseRecord = {
      ...MINIMAL_CASE,
      workflow_status: 'IN_PROGRESS',
      permissions: ['RECORD_DEPARTMENT_ACTION'],
    };
    const mockFetch = makeFetch(200, {
      case: inProgressCase,
      message: 'Kaydedildi',
    });
    vi.stubGlobal('fetch', mockFetch);

    const actionInput = {
      action_type: 'SAHA_INCELEMESI',
      result: 'Yol deformasyonu tespit edildi.',
      decision: 'Bakım programına alındı.',
      planned_date: '2026-08-29',
      notes: '',
    };

    await caseApi.departmentAction(TOKEN, inProgressCase, actionInput);

    const [, init] = (mockFetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit];
    const body = JSON.parse(init.body as string);

    expect(body.action_type).toBe('SAHA_INCELEMESI');
    expect(body.result).toBe('Yol deformasyonu tespit edildi.');
    expect(body.decision).toBe('Bakım programına alındı.');
    expect(body.expected_version).toBe(inProgressCase.version);
    expect(body.confirmed).toBe(true);
    // Must NOT include verified/recorded_by_user_id — those are backend-set
    expect(body.verified).toBeUndefined();
    expect(body.recorded_by_user_id).toBeUndefined();
  });
});
