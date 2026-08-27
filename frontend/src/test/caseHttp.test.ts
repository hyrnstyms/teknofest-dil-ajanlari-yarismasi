/**
 * EVRAG Person 3 – caseHttp / ApiError Tests
 *
 * Verifies that:
 *  - 401 responses are surfaced as ApiError with status 401
 *  - 403 responses are surfaced as ApiError with status 403
 *  - successful responses are returned as parsed JSON
 *  - backend error envelopes are parsed correctly
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { caseRequest, ApiError } from '../services/caseHttp';

beforeEach(() => {
  vi.restoreAllMocks();
});

function makeFetch(status: number, body: unknown): typeof fetch {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as Response);
}

describe('caseRequest', () => {
  it('returns parsed JSON on success', async () => {
    vi.stubGlobal('fetch', makeFetch(200, { hello: 'world' }));
    const result = await caseRequest<{ hello: string }>('/api/test');
    expect(result).toEqual({ hello: 'world' });
  });

  it('throws ApiError with status 401 for unauthenticated response', async () => {
    vi.stubGlobal(
      'fetch',
      makeFetch(401, {
        detail: { code: 'authentication_required', message: 'Kimlik doğrulama gereklidir.' },
      }),
    );
    await expect(caseRequest('/api/protected')).rejects.toSatisfy(
      (e: unknown) => e instanceof ApiError && e.status === 401,
    );
  });

  it('throws ApiError with status 403 for forbidden response', async () => {
    vi.stubGlobal(
      'fetch',
      makeFetch(403, {
        detail: { code: 'action_forbidden', message: 'Bu işlem için yetkiniz bulunmuyor.' },
      }),
    );
    await expect(caseRequest('/api/forbidden', 'token')).rejects.toSatisfy(
      (e: unknown) => e instanceof ApiError && e.status === 403 && e.code === 'action_forbidden',
    );
  });

  it('parses canonical error code from backend envelope', async () => {
    vi.stubGlobal(
      'fetch',
      makeFetch(409, {
        detail: {
          code: 'invalid_case_transition',
          message: 'İşlem mevcut dosya durumunda gerçekleştirilemez.',
        },
      }),
    );
    try {
      await caseRequest('/api/cases/123/route', 'token', { method: 'POST', body: '{}' });
      expect.fail('Should have thrown');
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).code).toBe('invalid_case_transition');
      expect((e as ApiError).status).toBe(409);
    }
  });

  it('sends Authorization header when token is provided', async () => {
    const mockFetch = makeFetch(200, {});
    vi.stubGlobal('fetch', mockFetch);
    await caseRequest('/api/cases/inbox', 'my-token');
    const [, init] = (mockFetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>)['Authorization']).toBe('Bearer my-token');
  });

  it('does NOT send Authorization header when no token', async () => {
    const mockFetch = makeFetch(200, {});
    vi.stubGlobal('fetch', mockFetch);
    await caseRequest('/api/public/cases/EVR-2026-00001');
    const [, init] = (mockFetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>)['Authorization']).toBeUndefined();
  });
});
