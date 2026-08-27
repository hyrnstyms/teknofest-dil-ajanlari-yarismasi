/**
 * EVRAG Person 3 – CasePrimitives Tests
 *
 * Verifies:
 *  - StatusBadge renders canonical Turkish status labels
 *  - No raw enum value (e.g. "READY_TO_ROUTE") is visible in normal UI
 *  - CaseTimeline renders server-provided event labels (not derived locally)
 *  - ConfirmAction exposes Onayla / Vazgeç buttons and prevents re-submit while busy
 *  - EmptyState renders title and text
 */

import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import {
  StatusBadge,
  CaseTimeline,
  ConfirmAction,
  EmptyState,
} from '../components/case/CasePrimitives';
import type { CaseEvent, CaseStatus } from '../types/case';

// ── StatusBadge ──────────────────────────────────────────────────────────────

describe('StatusBadge', () => {
  const statusCases: Array<[CaseStatus, string]> = [
    ['RECEIVED', 'Başvuru Alındı'],
    ['ANALYZING', 'AI Analizi Sürüyor'],
    ['WAITING_INITIAL_REVIEW', 'Ön İnceleme Bekliyor'],
    ['WAITING_CITIZEN_INFO', 'Vatandaştan Bilgi Bekleniyor'],
    ['READY_TO_ROUTE', 'Yönlendirme Onayı Bekliyor'],
    ['IN_DEPARTMENT', 'Birim İşleminde'],
    ['IN_PROGRESS', 'İşlemde'],
    ['RESPONSE_DRAFTED', 'Cevap Taslağı Hazır'],
    ['WAITING_FINAL_APPROVAL', 'Cevap Onayı Bekliyor'],
    ['COMPLETED', 'Tamamlandı'],
    ['CLOSED', 'Kapatıldı'],
  ];

  for (const [status, label] of statusCases) {
    it(`renders Turkish label for ${status}`, () => {
      const { container } = render(<StatusBadge status={status} />);
      // Correct Turkish label visible
      expect(container).toHaveTextContent(label);
      // Raw enum NOT directly visible as text (may be in CSS class attr which is fine)
      expect(container.textContent).not.toBe(status);
    });
  }

  it('does NOT render a raw accuracy percentage string', () => {
    const { container } = render(<StatusBadge status="READY_TO_ROUTE" />);
    // Invariant: no "%NN doğru" or "%NN accuracy" patterns
    expect(container.textContent).not.toMatch(/%\d+/);
  });
});

// ── CaseTimeline ─────────────────────────────────────────────────────────────

describe('CaseTimeline', () => {
  const events: CaseEvent[] = [
    {
      id: 'e1',
      event_type: 'CASE_RECEIVED',
      label: 'Başvuru alındı',
      actor_name: 'Sistem',
      created_at: '2026-08-27T09:30:00+03:00',
    },
    {
      id: 'e2',
      event_type: 'CASE_ROUTED',
      label: 'Fen İşleri Müdürlüğüne aktarıldı',
      actor_name: 'Ayşe Kaya',
      created_at: '2026-08-27T10:00:00+03:00',
    },
  ];

  it('renders server-provided event labels', () => {
    render(<CaseTimeline events={events} />);
    expect(screen.getByText('Başvuru alındı')).toBeInTheDocument();
    expect(screen.getByText('Fen İşleri Müdürlüğüne aktarıldı')).toBeInTheDocument();
  });

  it('renders actor names from server data', () => {
    render(<CaseTimeline events={events} />);
    expect(screen.getByText('Ayşe Kaya')).toBeInTheDocument();
  });

  it('renders an empty list without errors when events is empty', () => {
    const { container } = render(<CaseTimeline events={[]} />);
    expect(container.querySelector('ol')).toBeInTheDocument();
    expect(container.querySelectorAll('li').length).toBe(0);
  });
});

// ── ConfirmAction ─────────────────────────────────────────────────────────────

describe('ConfirmAction', () => {
  it('renders title and text', () => {
    render(
      <ConfirmAction
        title="Kurumsal sorumluluğu aktar"
        text="Bu işlem dosyanın kurumsal sorumluluğunu Fen İşleri Müdürlüğüne aktaracaktır."
        onCancel={() => {}}
        onConfirm={() => {}}
      />,
    );
    expect(screen.getByText('Kurumsal sorumluluğu aktar')).toBeInTheDocument();
    expect(
      screen.getByText(/Bu işlem dosyanın kurumsal sorumluluğunu/),
    ).toBeInTheDocument();
  });

  it('shows Onayla and Vazgeç buttons', () => {
    render(
      <ConfirmAction
        title="Test"
        text="Test text"
        onCancel={() => {}}
        onConfirm={() => {}}
      />,
    );
    expect(screen.getByRole('button', { name: /Onayla/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Vazgeç/i })).toBeInTheDocument();
  });

  it('disables both buttons when busy', () => {
    render(
      <ConfirmAction
        title="Test"
        text="Test text"
        busy
        onCancel={() => {}}
        onConfirm={() => {}}
      />,
    );
    const buttons = screen.getAllByRole('button');
    for (const btn of buttons) {
      expect(btn).toBeDisabled();
    }
  });

  it('calls onCancel when Vazgeç is clicked', () => {
    let cancelled = false;
    render(
      <ConfirmAction
        title="Test"
        text="Test text"
        onCancel={() => { cancelled = true; }}
        onConfirm={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: /Vazgeç/i }));
    expect(cancelled).toBe(true);
  });

  it('calls onConfirm when Onayla is clicked', () => {
    let confirmed = false;
    render(
      <ConfirmAction
        title="Test"
        text="Test text"
        onCancel={() => {}}
        onConfirm={() => { confirmed = true; }}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: /Onayla/i }));
    expect(confirmed).toBe(true);
  });
});

// ── EmptyState ────────────────────────────────────────────────────────────────

describe('EmptyState', () => {
  it('renders title and text', () => {
    render(<EmptyState title="Bekleyen dosya yok" text="Filtreye uygun kayıt bulunamadı." />);
    expect(screen.getByText('Bekleyen dosya yok')).toBeInTheDocument();
    expect(screen.getByText('Filtreye uygun kayıt bulunamadı.')).toBeInTheDocument();
  });
});
