import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CaseProductPanels } from "../components/case/CaseProductPanels";
import type { CaseRecord } from "../types/case";

const routedCase: CaseRecord = {
  id: "case-analysis",
  tracking_code: "EVR-2026-000005",
  institution_id: "belediye",
  title: "Kaymakamlık — Afet Eylem Planı Altyapı Bilgisi Talebi",
  source_type: "DIS_KURUM",
  source_channel: "KEP",
  originator_type: "DIS_KURUM",
  originator_name: "Örenli İlçe Kaymakamlığı",
  current_department_code: "fen_isleri",
  current_department_name: "Fen İşleri Müdürlüğü",
  workflow_status: "IN_DEPARTMENT",
  priority: "DEMO:dis_kurum_afet",
  received_at: "2026-08-27T08:00:00Z",
  created_at: "2026-08-27T08:00:00Z",
  updated_at: "2026-08-27T08:00:00Z",
  version: 4,
  routing_recommendation: {
    recommended_unit: "Fen İşleri Müdürlüğü",
    recommended_department_code: "fen_isleri",
    reason: "Talep edilen altyapı kayıtları bu müdürlüğün görev alanındadır.",
    evidence: [],
    alternatives: [],
    requires_human_review: true,
  },
  ai_operation: {
    task_type: "GENEL_INCELEME",
    department_code: "fen_isleri",
    team_name: "Saha Bakım Ekibi",
    reason: "Talep edilen altyapı kayıtları bu müdürlüğün görev alanındadır.",
  },
  clarification: {
    needs_clarification: false,
    blocking: false,
    requested_fields: [],
    question_type: "free_text",
    question: "",
    options: [],
    resume_target: "READY_TO_ROUTE",
  },
  timeline: [],
  department_actions: [],
  drafts: [{
    id: "draft-1",
    draft_type: "FORWARDING_COVER_LETTER",
    draft_status: "DRAFT",
    subject: "Afet eylem planı altyapı bilgileri",
    recipient: "Fen İşleri Müdürlüğü",
    body: "Bilgilerin hazırlanması rica olunur.",
    ai_generated: true,
  }],
  analysis_summary: "Örenli Kaymakamlığı, afet eylem planı güncellemesi kapsamında belediyenin altyapı verilerini talep etmektedir.",
  analysis_details: {
    document: {
      document_type: "kurumlar_arasi_yazi",
      process_intent: "bilgi_talebi",
      subject_excerpt: "Afet eylem planı altyapı bilgilerinin talebi",
    },
    extraction: {
      fields: {
        institution: { value: "Örenli İlçe Kaymakamlığı", validated: true },
        request: { value: "Belediye altyapı bilgilerinin gönderilmesi", validated: true },
        deadline: { value: "30.08.2026", validated: true },
        internal_note: { value: "DEMO:dis_kurum_afet", validated: true },
        uncertain_field: { value: "Gösterilmemeli", validated: false },
      },
    },
    missing_fields: { missing_fields: [], blocking_fields: [] },
    legal_analysis: {
      verified: true,
      evidence: [{ title: "Bilgi Edinme Hakkı Kanunu", law_number: "4982", madde_no: "11", score: 0.92 }],
      sources: [],
    },
  },
  permissions: [],
};

describe("Case document analysis overview", () => {
  it("surfaces the specification results while technical details stay closed", () => {
    const { container } = render(<CaseProductPanels item={routedCase} token="token" onRefresh={vi.fn()} onNotice={vi.fn()}/>);
    for (const text of [
      "Evrak analiz sonucu",
      "Kurumlar Arası Yazı",
      "Bilgi Talebi",
      "Örenli İlçe Kaymakamlığı",
      "Çıkarılan Bilgiler",
      "İşlemi engelleyen eksik bilgi bulunmadı",
      "Doğrulanmış mevzuat dayanağı",
      "Yönlendirme",
      "Fen İşleri Müdürlüğü",
      "Havale tamamlandı",
      "1 taslak hazır",
      "İşlem Geçmişi",
    ]) expect(screen.getAllByText(text, { exact: false }).length).toBeGreaterThan(0);
    expect(screen.queryByText("Resmî Yazışma Kontrolleri")).not.toBeInTheDocument();
    expect(container.textContent).not.toMatch(/DEMO:|DIS_KURUM|IN_DEPARTMENT|READY_TO_ROUTE/);
    expect(container.textContent).not.toContain("AI Fen İşleri Müdürlüğünü öneriyor");
  });

  it("opens the response-draft tab from the compact draft status", () => {
    render(<CaseProductPanels item={routedCase} token="token" onRefresh={vi.fn()} onNotice={vi.fn()}/>);
    fireEvent.click(screen.getByRole("button", { name: "Taslağa Git" }));
    expect(screen.getByText("Taslak İçeriği")).toBeInTheDocument();
  });

  it("shows blocking detail and does not invent a law when verified evidence is absent", () => {
    const missingCase: CaseRecord = {
      ...routedCase,
      drafts: [],
      source_type: "VATANDAS",
      originator_type: "VATANDAS",
      originator_name: "Başvuru Sahibi",
      workflow_status: "WAITING_CITIZEN_INFO",
      clarification: {
        needs_clarification: true,
        blocking: true,
        requested_fields: ["location"],
        question_type: "free_text",
        question: "Olay yeri nedir?",
        options: [],
        resume_target: "READY_TO_ROUTE",
        reason: "Saha incelemesi için olay yeri bilinmelidir.",
        target_type: "VATANDAS",
        target_name: "Başvuru sahibi",
      },
      analysis_details: {
        ...routedCase.analysis_details,
        missing_fields: { missing_fields: ["location"], blocking_fields: ["location"] },
        legal_analysis: { verified: false, evidence: [], sources: [] },
      },
    };
    render(<CaseProductPanels item={missingCase} token="token" onRefresh={vi.fn()} onNotice={vi.fn()}/>);
    expect(screen.getByText("Konum")).toBeInTheDocument();
    expect(screen.getByText("Saha incelemesi için olay yeri bilinmelidir.")).toBeInTheDocument();
    expect(screen.getByText("Başvuru sahibi")).toBeInTheDocument();
    expect(screen.getByText("Bu işlem için doğrulanmış özel mevzuat dayanağı bulunamadı.")).toBeInTheDocument();
    expect(screen.queryByText(/3071|4982/)).not.toBeInTheDocument();
  });
});
