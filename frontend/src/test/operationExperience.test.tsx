import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { CaseOperationPlan } from "../components/case/CaseOperationPlan";
import { MissingInformationSolution } from "../components/case/MissingInformationSolution";
import { OperationalNextAction } from "../components/case/OperationalNextAction";
import { RoleOperationsDashboard } from "../components/case/RoleOperationsDashboard";
import { WritingGroundingSummary } from "../components/case/WritingGroundingSummary";
import type { CaseRecord, CurrentUser } from "../types/case";

const registry: CurrentUser = { id: "u1", name: "Kayıt Personeli", role: "EVRAK_KAYIT", institution_id: "i1", department_code: "YAZI", department_name: "Yazı İşleri" };
const department: CurrentUser = { ...registry, id: "u2", role: "BIRIM_PERSONELI", department_code: "FEN", department_name: "Fen İşleri Müdürlüğü" };

const item: CaseRecord = {
  id: "c1", tracking_code: "EVR-2026-001", institution_id: "i1", title: "Bozuk kaldırım başvurusu",
  source_type: "VATANDAS", source_channel: "WEB_FORM", originator_type: "VATANDAS", originator_name: "Başvuru Sahibi",
  current_department_code: "YAZI", current_department_name: "Yazı İşleri", workflow_status: "READY_TO_ROUTE", priority: "Yüksek",
  received_at: "2026-08-27T08:00:00Z", created_at: "2026-08-27T08:00:00Z", updated_at: "2026-08-27T08:00:00Z", version: 1,
  routing_recommendation: { recommended_unit: "Fen İşleri Müdürlüğü", recommended_department_code: "FEN", reason: "Kaldırım bakımından sorumlu birimdir.", evidence: ["Konu ve hizmet alanı eşleşti."], alternatives: [], requires_human_review: true },
  ai_operation: { task_type: "YOL_BAKIM_INCELEME", department_code: "fen_isleri", team_code: "saha_bakim_ekibi", team_name: "Saha Bakım Ekibi", recommended_role: "SAHA_EKIBI", requires_field_visit: true, reason: "yol_bakim_sikayeti süreç profiliyle eşleşti." },
  priority_assessment: { priority: "HIGH", priority_reason: "Evrak açık bir acil işlem ifadesi içeriyor." },
  deadline: { applicable: true, deadline_days: 30, remaining_days: 5, risk_level: "APPROACHING", legal_basis: { verified: true, citation: "3071 sayılı Kanun Madde 7" } },
  clarification: { needs_clarification: true, blocking: true, requested_fields: ["address"], question_type: "free_text", question: "Olay adresi nedir?", options: [], resume_target: "READY_TO_ROUTE", reason: "Saha incelemesi için konum gereklidir.", target_type: "VATANDAS", target_name: "Başvuru Sahibi", recommended_action: "CITIZEN_INFORMATION_REQUESTED", required_for_process: true, missing_field: "location" },
  timeline: [], department_actions: [], drafts: [{ id: "d1", draft_type: "MISSING_INFORMATION_REQUEST", draft_status: "DRAFT", subject: "Adres bilgisi talebi", recipient: "Başvuru Sahibi", recipient_kind: "VATANDAS", body: "Adres bilgisini iletiniz.", ai_generated: true }],
  analysis_summary: "Kaldırım için yerinde inceleme gerekiyor.", analysis_details: { extraction: { fields: {} } }, permissions: ["ROUTE_CASE", "REQUEST_CITIZEN_INFO"],
};

describe("EVRAG operation-first experience", () => {
  it("shows a registry routing desk derived from case data", () => {
    render(<MemoryRouter><RoleOperationsDashboard user={registry} items={[item]} loading={false}/></MemoryRouter>);
    expect(screen.getByText("Yazı İşleri Operasyon Masası")).toBeInTheDocument();
    expect(screen.getByText("AI HAVALE ÖNERİLERİ")).toBeInTheDocument();
    expect(screen.getByText("Kaldırım bakımından sorumlu birimdir.")).toBeInTheDocument();
  });

  it("turns department cases into today's work", () => {
    render(<MemoryRouter><RoleOperationsDashboard user={department} items={[{ ...item, workflow_status: "IN_DEPARTMENT", permissions: ["START_CASE"] }]} loading={false}/></MemoryRouter>);
    expect(screen.getByText("Fen İşleri Müdürlüğü Çalışma Masası")).toBeInTheDocument();
    expect(screen.getByText("BUGÜNÜN İŞLERİ")).toBeInTheDocument();
    expect(screen.getByText("Dosyayı işleme al")).toBeInTheDocument();
  });

  it("renders the real Level-2 task without inventing personnel", () => {
    const onRoute = vi.fn();
    const routed = { ...item, current_department_code: "fen_isleri", current_department_name: "Fen İşleri Müdürlüğü", workflow_status: "IN_DEPARTMENT" as const, permissions: ["START_CASE"], assignment: { id: "t1", case_id: "c1", source_case_id: "c1", task_type: "YOL_BAKIM_INCELEME", department_code: "fen_isleri", team_code: "saha_bakim_ekibi", recommended_role: "SAHA_EKIBI", assigned_user_id: null, status: "ASSIGNMENT_PENDING" as const, created_at: "2026-08-27T08:00:00Z", updated_at: "2026-08-27T08:00:00Z" } };
    render(<CaseOperationPlan item={routed} onRoute={onRoute}/>);
    expect(screen.getByText("EVRAG AKILLI İŞLEM PLANI")).toBeInTheDocument();
    expect(screen.getAllByText("ASSIGNMENT_PENDING").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Saha Bakım Ekibi").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Saha Ekibi").length).toBeGreaterThan(0);
    expect(screen.getByText(/sahte personel gösterilmedi/)).toBeInTheDocument();
    expect(screen.queryByText(/Ahmet|Mehmet|Ayşe/)).not.toBeInTheDocument();
  });

  it("explains missing information and chooses the correct source", () => {
    render(<MissingInformationSolution item={item} onRequest={vi.fn()}/>);
    expect(screen.getByText("Başvuru Sahibi")).toBeInTheDocument();
    expect(screen.getByText("Olay konumu / adres")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Vatandaştan Konum Bilgisi İste" })).toBeEnabled();
  });

  it("uses the backend internal clarification target", () => {
    const internal = { ...item, source_type: "KURUM_ICI" as const, originator_type: "KURUM_ICI" as const, clarification: { ...item.clarification!, target_type: "INTERNAL_DEPARTMENT" as const, target_name: "Yazı İşleri", target_department: "yazi_isleri", recommended_action: "INTERNAL_INFORMATION_REQUESTED" } };
    render(<MissingInformationSolution item={internal} onRequest={vi.fn()}/>);
    expect(screen.getByRole("button", { name: "Yazı İşleri Müdürlüğünden Eksik Bilgi İste" })).toBeEnabled();
  });

  it("offers exactly the actionable next step and explains draft grounding", () => {
    const onAction = vi.fn();
    render(<><OperationalNextAction item={item} user={registry} onAction={onAction}/><WritingGroundingSummary item={item}/></>);
    fireEvent.click(screen.getByRole("button", { name: /Eksik Bilgi Talebi Oluştur/ }));
    expect(onAction).toHaveBeenCalledWith("clarification");
    expect(screen.getByText("BU TASLAK NEDEN ÜRETİLDİ?")).toBeInTheDocument();
    expect(screen.getAllByText("Saha incelemesi için konum gereklidir.").length).toBeGreaterThan(0);
  });
});
