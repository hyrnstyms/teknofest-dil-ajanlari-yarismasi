import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CaseProductPanels } from "../components/case/CaseProductPanels";
import type { CaseRecord } from "../types/case";

const base: CaseRecord = { id: "case-1", tracking_code: "EVR-1", institution_id: "belediye", title: "Yol bakım", source_type: "VATANDAS", source_channel: "WEB_FORM", originator_type: "VATANDAS", originator_name: "Ali Yılmaz", current_department_code: "fen_isleri", current_department_name: "Fen İşleri Müdürlüğü", workflow_status: "IN_PROGRESS", received_at: "2026-01-01", created_at: "2026-01-01", updated_at: "2026-01-01", version: 3, timeline: [], department_actions: [], drafts: [], permissions: ["RECORD_DEPARTMENT_ACTION", "SAVE_DRAFT"], analysis_summary: "Yol bakım talebi", analysis_details: { document: { document_type: "dilekçe", process_intent: "bildirim" }, extraction: { fields: { location: { value: "Çınar Sokak", validated: true } } }, missing_fields: { missing_fields: [] }, legal_analysis: { verified: true, text: "3071 sayılı Kanun" } } };

describe("Case official writing and report experience", () => {
  it("always exposes the reply-draft area and locked flow before DepartmentAction", () => { render(<CaseProductPanels item={base} token="token" onRefresh={vi.fn()} onNotice={vi.fn()}/>); fireEvent.click(screen.getByRole("button", { name: /Cevap Taslağı/ })); expect(screen.getByText("Resmî yazı alanı hazır")).toBeInTheDocument(); expect(screen.getByText(/Kurum İşlemi → Taslak/)).toBeInTheDocument(); });
  it("shows all Task 1 report sections", () => { render(<CaseProductPanels item={base} token="token" onRefresh={vi.fn()} onNotice={vi.fn()}/>); fireEvent.click(screen.getByRole("button", { name: "AI Analiz Raporu" })); for (const label of ["Belge", "Özet", "Çıkarılan Bilgiler", "Eksik Bilgiler", "Mevzuat / Dayanak", "Yönlendirme", "Resmî Yazışma Kontrolleri"]) expect(screen.getAllByText(label).length).toBeGreaterThan(0); });
  it("renders A4, direct edit and quality controls for an unapproved draft", () => { const item = { ...base, workflow_status: "RESPONSE_DRAFTED" as const, department_actions: [{ id: "a", action_type: "İNCELEME", result: "Tespit", decision: "Programa alındı", verified: true, recorded_by_user_id: "u", created_at: "2026-01-01" }], permissions: ["SAVE_DRAFT", "APPROVE_DRAFT"], drafts: [{ id: "d", draft_type: "OFFICIAL_RESPONSE" as const, draft_status: "DRAFT" as const, revision: 1, recipient: "Ali Yılmaz", subject: "Başvurunuz Hk.", body: "Başvurunuz incelenmiştir.", grounded_action_id: "a", ai_generated: true }] }; render(<CaseProductPanels item={item} token="token" onRefresh={vi.fn()} onNotice={vi.fn()}/>); fireEvent.click(screen.getByRole("button", { name: /Cevap Taslağı/ })); expect(screen.getByText("T.C.")).toBeInTheDocument(); expect(screen.getByRole("button", { name: "Düzenle" })).toBeInTheDocument(); expect(screen.getByText("Düzeltme / Kalite Kontrolü")).toBeInTheDocument(); });
  it("renders exact Turkish text and visible editable actions above A4", () => {
    const sentence = "Personel kontrolü sonucunda güncel değerlendirme bu cümleyle kayda alınmıştır. çğıöşü ÇĞİÖŞÜ";
    const item = { ...base, workflow_status: "RESPONSE_DRAFTED" as const, department_actions: [{ id: "a", action_type: "İNCELEME", result: "Tespit", decision: "Programa alındı", verified: true, recorded_by_user_id: "u", created_at: "2026-01-01" }], permissions: ["SAVE_DRAFT", "APPROVE_DRAFT"], drafts: [{ id: "d", draft_type: "OFFICIAL_RESPONSE" as const, draft_status: "EDITED" as const, revision: 2, recipient: "Ali Yılmaz", subject: "Başvurunuz Hk.", body: sentence, grounded_action_id: "a", ai_generated: true, personnel_edited: true }] };
    render(<CaseProductPanels item={item} token="token" onRefresh={vi.fn()} onNotice={vi.fn()}/>);
    fireEvent.click(screen.getByRole("button", { name: /Cevap Taslağı/ }));
    expect(screen.getByText(/Personel kontrolü sonucunda güncel değerlendirme/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Düzenle" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Yeniden Oluştur" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Onayla" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Düzenle" }).closest(".draft-action-toolbar")).toBeTruthy();
  });

  it("shows approved actions and marks an older draft as archived", () => {
    const common = { draft_type: "OFFICIAL_RESPONSE" as const, recipient: "Ali Yılmaz", subject: "Başvurunuz Hk.", body: "Metin", grounded_action_id: "a", ai_generated: true };
    const item = { ...base, workflow_status: "WAITING_FINAL_APPROVAL" as const, permissions: ["SAVE_DRAFT", "APPROVE_DRAFT"], drafts: [{ ...common, id: "old", draft_status: "DRAFT" as const, revision: 3 }, { ...common, id: "approved", draft_status: "APPROVED" as const, revision: 4 }] };
    render(<CaseProductPanels item={item} token="token" onRefresh={vi.fn()} onNotice={vi.fn()}/>);
    fireEvent.click(screen.getByRole("button", { name: /Cevap Taslağı/ }));
    expect(screen.getByRole("button", { name: "Yeni Revizyon Oluştur" })).toBeVisible();
    expect(screen.getByRole("button", { name: "DOCX İndir" })).toBeVisible();
    expect(screen.getByRole("button", { name: "PDF İndir" })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: /Taslak · v3/ }));
    expect(screen.getByText("Bu sürüm arşivlenmiş bir taslaktır.")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Düzenle" })).not.toBeInTheDocument();
  });});
