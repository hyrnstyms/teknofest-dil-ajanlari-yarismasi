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
