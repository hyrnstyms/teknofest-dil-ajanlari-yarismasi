import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { api } from "../services/api";
import { QrVerifyPage } from "../pages/QrVerifyPage";
import { SimilarDocumentsCard } from "../components/cards/SimilarDocumentsCard";
import { AdminDashboard } from "../components/AdminDashboard";

beforeEach(() => {
  vi.restoreAllMocks();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("QR verification", () => {
  it("calls the public verification endpoint with an encoded id", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({
        id: "EVR/42",
        status: "verified",
        document_type: "dilekce",
        created_at: "2026-08-27T10:00:00+03:00",
      }),
    } as Response);
    vi.stubGlobal("fetch", mockFetch);

    await api.verifyDocument("EVR/42");

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/verify/EVR%2F42",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
  });

  it("renders status, document type and date from the backend response", async () => {
    vi.spyOn(api, "verifyDocument").mockResolvedValue({
      id: "EVR-42",
      status: "verified",
      document_type: "dilekce",
      created_at: "2026-08-27T10:00:00+03:00",
      valid: true,
    });

    render(
      <MemoryRouter initialEntries={["/dogrulama/EVR-42"]}>
        <Routes><Route path="/dogrulama/:id" element={<QrVerifyPage />} /></Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("Bu kayıt EVRAG doğrulama servisi tarafından bulundu.")).toBeInTheDocument();
    expect(screen.getByText("Verified")).toBeInTheDocument();
    expect(screen.getByText("Dilekçe")).toBeInTheDocument();
    expect(screen.getByText(/27 Ağustos 2026/)).toBeInTheDocument();
  });
});

describe("similar documents", () => {
  it("reports the missing HTTP integration without fabricating records", () => {
    render(<SimilarDocumentsCard />);
    expect(screen.getByRole("heading", { name: "Benzer Evraklar" })).toBeInTheDocument();
    expect(screen.getByText("API bağlantısı bekleniyor")).toBeInTheDocument();
    expect(screen.queryByRole("listitem")).not.toBeInTheDocument();
  });
});

describe("department distribution", () => {
  it("derives chart values from real analysis response items", async () => {
    vi.spyOn(api, "getRoiSummary").mockResolvedValue({
      processed_documents: 3,
      average_processing_seconds: 1.5,
      human_review_required_rate: 0.5,
      approved_count: 1,
      edited_count: 0,
      rejected_count: 0,
      estimated_saved_seconds: 10,
    });
    vi.spyOn(api, "getPendingReviews").mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 });
    vi.spyOn(api, "getAnalyses").mockResolvedValue({
      total: 3,
      limit: 20,
      offset: 0,
      items: [
        { analysis_id: "1", document_id: "1", recommended_unit: "Fen İşleri" },
        { analysis_id: "2", document_id: "2", recommended_unit: "Fen İşleri" },
        { analysis_id: "3", document_id: "3", recommended_unit: "İmar ve Şehircilik" },
      ],
    });

    render(<AdminDashboard onOpenAnalysis={() => undefined} />);

    expect(await screen.findByRole("heading", { name: "Birim Dağılımı" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("2 evrak")).toBeInTheDocument());
    const chart = screen.getByRole("img", { name: "Önerilen birimlere göre evrak dağılımı" });
    expect(within(chart).getByText("Fen İşleri")).toBeInTheDocument();
    expect(within(chart).getByText("İmar ve Şehircilik")).toBeInTheDocument();
  });
});
