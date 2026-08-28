import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CaseProductPanels } from "../components/case/CaseProductPanels";
import { caseApi } from "../services/caseApi";
import type { CaseRecord } from "../types/case";

const base: CaseRecord = { id: "case-1", tracking_code: "EVR-1", institution_id: "belediye", title: "Yol bakım", source_type: "VATANDAS", source_channel: "WEB_FORM", originator_type: "VATANDAS", originator_name: "Ali Yılmaz", current_department_code: "fen_isleri", current_department_name: "Fen İşleri Müdürlüğü", workflow_status: "IN_PROGRESS", received_at: "2026-01-01", created_at: "2026-01-01", updated_at: "2026-01-01", version: 3, timeline: [], department_actions: [], drafts: [], permissions: ["RECORD_DEPARTMENT_ACTION", "SAVE_DRAFT"], analysis_summary: "Yol bakım talebi", analysis_details: { document: { document_type: "dilekçe", process_intent: "bildirim" }, extraction: { fields: { location: { value: "Çınar Sokak", validated: true } } }, missing_fields: { missing_fields: [] }, legal_analysis: { verified: true, text: "3071 sayılı Kanun" } } };

describe("Case official writing and report experience", () => {
  it("always exposes the reply-draft area and locked flow before DepartmentAction", () => { render(<CaseProductPanels item={base} token="token" onRefresh={vi.fn()} onNotice={vi.fn()}/>); fireEvent.click(screen.getByRole("button", { name: /Cevap Taslağı/ })); expect(screen.getByText("Resmî yazı alanı hazır")).toBeInTheDocument(); expect(screen.getByText(/Kurum İşlemi → Taslak/)).toBeInTheDocument(); });
  it("shows all Task 1 report sections", () => { render(<CaseProductPanels item={base} token="token" onRefresh={vi.fn()} onNotice={vi.fn()}/>); fireEvent.click(screen.getByRole("button", { name: "AI Analiz Raporu" })); for (const label of ["Belge", "Özet", "Çıkarılan Bilgiler", "Eksik Bilgiler", "Mevzuat / Kanıt", "Yönlendirme", "Resmî Yazışma Kontrolleri"]) expect(screen.getAllByText(label).length).toBeGreaterThan(0); });
  it("renders A4, direct edit and quality controls for an unapproved draft", () => { const item = { ...base, workflow_status: "RESPONSE_DRAFTED" as const, department_actions: [{ id: "a", action_type: "İNCELEME", result: "Tespit", decision: "Programa alındı", verified: true, recorded_by_user_id: "u", created_at: "2026-01-01" }], permissions: ["SAVE_DRAFT", "APPROVE_DRAFT"], drafts: [{ id: "d", draft_type: "OFFICIAL_RESPONSE" as const, draft_status: "DRAFT" as const, revision: 1, recipient: "Ali Yılmaz", subject: "Başvurunuz Hk.", body: "Başvurunuz incelenmiştir.", grounded_action_id: "a", ai_generated: true }] }; render(<CaseProductPanels item={item} token="token" onRefresh={vi.fn()} onNotice={vi.fn()}/>); fireEvent.click(screen.getByRole("button", { name: /Cevap Taslağı/ })); expect(screen.getByText("T.C.")).toBeInTheDocument(); expect(screen.getByRole("button", { name: "Düzenle" })).toBeInTheDocument(); expect(screen.getByText("Düzeltme / Kalite Kontrolü")).toBeInTheDocument(); });

  it("shows and persistently edits an Analysis preview without exposing official actions", async () => {
    const previewItem: CaseRecord = {
      ...base,
      analysis_id: "analysis-1",
      workflow_status: "READY_TO_ROUTE",
      drafts: [],
      analysis_preview_draft: {
        analysis_id: "analysis-1",
        draft_type: "cevap_yazisi",
        subject: "Eski Konu",
        body: "AI tarafından oluşturulan ön taslak.",
        recipient: "Ali Yılmaz",
        recipient_kind: "gercek_kisi",
        edited: false,
      },
    };
    const edit = vi.spyOn(caseApi, "editAnalysisPreview").mockResolvedValue({ status: "success", message: "Taslak güncellendi." });
    const refresh = vi.fn().mockResolvedValue(undefined);
    render(<CaseProductPanels item={previewItem} token="token" onRefresh={refresh} onNotice={vi.fn()}/>);

    fireEvent.click(screen.getByRole("button", { name: "Cevap Taslağı (1)" }));
    expect(screen.getByText("Bu bir AI ön taslağıdır; resmî CaseDraft değildir.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Onayla" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "DOCX" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Ön Taslağı Düzenle" }));
    fireEvent.change(screen.getByLabelText("Konu"), { target: { value: "Yeni Konu" } });
    fireEvent.change(screen.getByLabelText("Gövde"), { target: { value: "Personel tarafından düzenlenen metin." } });
    fireEvent.click(screen.getByRole("button", { name: "Düzenlemeyi Kaydet" }));

    await waitFor(() => expect(edit).toHaveBeenCalledWith("token", previewItem, {
      subject: "Yeni Konu",
      body: "Personel tarafından düzenlenen metin.",
    }));
    expect(refresh).toHaveBeenCalledOnce();
  });
});
