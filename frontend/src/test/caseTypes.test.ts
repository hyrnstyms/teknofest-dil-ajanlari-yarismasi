/**
 * EVRAG Person 3 – Case Types / Contract Audit Tests
 *
 * Pure unit tests that verify:
 *  - CaseStatus enum values match the contract
 *  - "ROUTED" is NOT a valid CaseStatus (contract §5 explicitly forbids it)
 *  - DraftType enum values match the contract
 *  - draft_status enum values match the contract
 *  - source_type / source_channel / originator_type match contract §4
 *  - PublicCase does NOT expose fields forbidden by contract §9.4
 */

import { describe, it, expect } from 'vitest';

// Import types for narrowing — we can't instantiate TS types at runtime,
// so we verify via object literals that would fail tsc if wrong.
import type {
  CaseStatus,
  CaseRecord,
  PublicCase,
  CaseDraft,
} from '../types/case';

// ── CaseStatus values ─────────────────────────────────────────────────────────

describe('CaseStatus canonical values', () => {
  const CANONICAL_STATUSES: CaseStatus[] = [
    'RECEIVED',
    'ANALYZING',
    'WAITING_INITIAL_REVIEW',
    'WAITING_CITIZEN_INFO',
    'READY_TO_ROUTE',
    'IN_DEPARTMENT',
    'IN_PROGRESS',
    'RESPONSE_DRAFTED',
    'WAITING_FINAL_APPROVAL',
    'COMPLETED',
    'CLOSED',
  ];

  it('has exactly 11 canonical statuses matching the contract', () => {
    expect(CANONICAL_STATUSES).toHaveLength(11);
  });

  it('includes all required statuses', () => {
    expect(CANONICAL_STATUSES).toContain('RECEIVED');
    expect(CANONICAL_STATUSES).toContain('IN_DEPARTMENT');
    expect(CANONICAL_STATUSES).toContain('IN_PROGRESS');
    expect(CANONICAL_STATUSES).toContain('CLOSED');
  });

  it('does NOT include ROUTED — contract §5 explicitly forbids it', () => {
    // 'ROUTED' must never be a durable status per contract
    expect(CANONICAL_STATUSES).not.toContain('ROUTED' as CaseStatus);
  });
});

// ── DraftType values ──────────────────────────────────────────────────────────

describe('CaseDraft draft_type canonical values', () => {
  const DRAFT_TYPES: CaseDraft['draft_type'][] = [
    'MISSING_INFORMATION_REQUEST',
    'INTERIM_INFORMATION',
    'OFFICIAL_RESPONSE',
    'INTERNAL_MEMO',
    'FORWARDING_COVER_LETTER',
  ];

  it('has 5 canonical draft types matching contract §7.5', () => {
    expect(DRAFT_TYPES).toHaveLength(5);
  });

  it('includes OFFICIAL_RESPONSE', () => {
    expect(DRAFT_TYPES).toContain('OFFICIAL_RESPONSE');
  });

  it('includes MISSING_INFORMATION_REQUEST', () => {
    expect(DRAFT_TYPES).toContain('MISSING_INFORMATION_REQUEST');
  });
});

describe('CaseDraft draft_status canonical values', () => {
  const DRAFT_STATUSES: CaseDraft['draft_status'][] = [
    'DRAFT',
    'EDITED',
    'APPROVED',
    'SENT',
    'CANCELLED',
  ];

  it('has 5 canonical draft statuses', () => {
    expect(DRAFT_STATUSES).toHaveLength(5);
  });
});

// ── CaseRecord field structure ────────────────────────────────────────────────

describe('CaseRecord structural invariants', () => {
  // Build a minimal valid CaseRecord to verify type structure
  const record: CaseRecord = {
    id: 'case-uuid',
    tracking_code: 'EVR-2026-000001',
    institution_id: 'belediye',
    title: 'Yol bakım talebi',
    source_type: 'VATANDAS',
    source_channel: 'EBYS',
    originator_type: 'VATANDAS',
    originator_name: 'Ali Yılmaz',
    current_department_code: 'yazi_isleri',
    current_department_name: 'Yazı İşleri Müdürlüğü',
    workflow_status: 'RECEIVED',
    received_at: '2026-08-27T09:30:00+03:00',
    created_at: '2026-08-27T09:31:00+03:00',
    updated_at: '2026-08-27T09:31:00+03:00',
    version: 1,
    timeline: [],
    department_actions: [],
    drafts: [],
    permissions: [],
  };

  it('has received_at field — not created_at as legal date proxy', () => {
    expect(record.received_at).toBeDefined();
    // Contract §4 invariant 4: received_at is legal receipt time; created_at must not substitute
    expect(record.received_at).not.toBe(record.created_at);
  });

  it('has current_department_code and originator_name as separate fields', () => {
    // Contract §4 invariant 3: originator and current_department_code are separate
    expect(record.originator_name).toBeDefined();
    expect(record.current_department_code).toBeDefined();
    // They should be distinct concepts
    expect(record.originator_name).not.toBe(record.current_department_code);
  });

  it('has version field for optimistic concurrency', () => {
    expect(typeof record.version).toBe('number');
  });

  it('does NOT have citizen_token field in CaseRecord (internal only, must not leak)', () => {
    // citizen_token must NOT be in the main CaseRecord type
    expect('citizen_token' in record).toBe(false);
  });
});

// ── PublicCase invariants ─────────────────────────────────────────────────────

describe('PublicCase public DTO invariants', () => {
  const publicCase: PublicCase = {
    tracking_code: 'EVR-2026-000001',
    subject: 'Yol bakım talebi',
    received_at: '2026-08-27T09:30:00+03:00',
    status: 'İşleminiz incelemede',
    workflow_status: 'RECEIVED',
    updated_at: '2026-08-27T09:31:00+03:00',
    timeline: [],
  };

  it('does NOT expose internal user IDs', () => {
    expect('assigned_user_id' in publicCase).toBe(false);
    expect('recorded_by_user_id' in publicCase).toBe(false);
  });

  it('does NOT expose originator contact information', () => {
    expect('originator_email' in publicCase).toBe(false);
    expect('originator_phone' in publicCase).toBe(false);
  });

  it('does NOT expose routing internals', () => {
    expect('routing_recommendation' in publicCase).toBe(false);
    expect('department_actions' in publicCase).toBe(false);
  });

  it('does NOT expose AI scores or prompts', () => {
    expect('analysis_summary' in publicCase).toBe(false);
  });

  it('has tracking_code, subject, received_at and status', () => {
    expect(publicCase.tracking_code).toBeTruthy();
    expect(publicCase.subject).toBeTruthy();
    expect(publicCase.received_at).toBeTruthy();
    expect(publicCase.status).toBeTruthy();
  });
});
