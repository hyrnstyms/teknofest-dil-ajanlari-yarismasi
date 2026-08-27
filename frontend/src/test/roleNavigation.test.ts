/**
 * EVRAG Person 3 – Role Navigation Tests
 *
 * Verifies that navigationForRole returns the correct items per role and
 * that BIRIM_PERSONELI navigation does NOT include EVRAK_KAYIT-only items.
 * Also ensures that the roleLabel helper returns a human-readable string
 * and does NOT expose raw role enum values to the UI.
 *
 * Key product decision (Person 3 Final Cleanup):
 *   - "Resmî Yazılar" is removed from both role navigations.
 *   - Drafts/official replies live inside the case workspace (Cevap Taslağı tab).
 *   - EVRAK_KAYIT gets "Giden Evraklar" (key: outgoing) for approved outgoing docs.
 *   - BIRIM_PERSONELI has no separate writing entry.
 */

import { describe, it, expect } from 'vitest';
import { navigationForRole, roleLabel } from '../utils/roleNavigation';

describe('navigationForRole', () => {
  it('returns EVRAK_KAYIT navigation items', () => {
    const items = navigationForRole('EVRAK_KAYIT');
    const keys = items.map((i) => i.key);
    expect(keys).toContain('home');
    expect(keys).toContain('incoming');
    expect(keys).toContain('clarification');
    expect(keys).toContain('routing');
    expect(keys).toContain('history');
  });

  it('EVRAK_KAYIT has Giden Evraklar (outgoing) entry', () => {
    const items = navigationForRole('EVRAK_KAYIT');
    const keys = items.map((i) => i.key);
    expect(keys).toContain('outgoing');
  });

  it('returns BIRIM_PERSONELI navigation items', () => {
    const items = navigationForRole('BIRIM_PERSONELI');
    const keys = items.map((i) => i.key);
    expect(keys).toContain('home');
    expect(keys).toContain('assigned');
    expect(keys).toContain('progress');
    expect(keys).toContain('approval');
    expect(keys).toContain('deadline');
    expect(keys).toContain('history');
  });

  it('BIRIM_PERSONELI does not get EVRAK_KAYIT-only routing key', () => {
    const items = navigationForRole('BIRIM_PERSONELI');
    const keys = items.map((i) => i.key);
    // "routing" (Yönlendirme Bekleyenler) is EVRAK_KAYIT only
    expect(keys).not.toContain('routing');
    // "incoming" (Gelen Evrak Havuzu) is EVRAK_KAYIT only
    expect(keys).not.toContain('incoming');
  });

  it('EVRAK_KAYIT does not get BIRIM_PERSONELI-only assigned key', () => {
    const items = navigationForRole('EVRAK_KAYIT');
    const keys = items.map((i) => i.key);
    expect(keys).not.toContain('assigned');
  });

  it('neither role has a standalone "writings" (Resmî Yazılar) nav entry', () => {
    for (const role of ['EVRAK_KAYIT', 'BIRIM_PERSONELI'] as const) {
      const keys = navigationForRole(role).map((i) => i.key);
      expect(keys).not.toContain('writings');
    }
  });

  it('BIRIM_PERSONELI does not have an outgoing writings entry', () => {
    // Drafts for Birim Personeli are accessed inside the case workspace only
    const keys = navigationForRole('BIRIM_PERSONELI').map((i) => i.key);
    expect(keys).not.toContain('outgoing');
  });

  it('all items have non-empty to and text', () => {
    for (const role of ['EVRAK_KAYIT', 'BIRIM_PERSONELI'] as const) {
      for (const item of navigationForRole(role)) {
        expect(item.to).toBeTruthy();
        expect(item.text).toBeTruthy();
        expect(item.key).toBeTruthy();
      }
    }
  });
});

describe('roleLabel', () => {
  it('returns Turkish label for EVRAK_KAYIT', () => {
    const label = roleLabel('EVRAK_KAYIT');
    // Must not expose raw enum
    expect(label).not.toBe('EVRAK_KAYIT');
    expect(label.length).toBeGreaterThan(0);
  });

  it('returns Turkish label for BIRIM_PERSONELI', () => {
    const label = roleLabel('BIRIM_PERSONELI');
    expect(label).not.toBe('BIRIM_PERSONELI');
    expect(label.length).toBeGreaterThan(0);
  });
});
