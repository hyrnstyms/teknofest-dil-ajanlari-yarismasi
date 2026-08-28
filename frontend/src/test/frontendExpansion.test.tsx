import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { api } from "../services/api";
import * as adminApi from "../services/adminApi";
import { QrVerifyPage } from "../pages/QrVerifyPage";
import { SimilarDocumentsCard } from "../components/cards/SimilarDocumentsCard";
import { AdminPage } from "../pages/AdminPage";

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
        found: true,
        evrak_id: "EVR/42",
        source: "case",
        status: "in_progress",
        status_label: "İşlemde",
        document_type: "dilekce",
        received_at: "2026-08-27T10:00:00+03:00",
        institution_id: "belediye",
      }),
    } as Response);
    vi.stubGlobal("fetch", mockFetch);

    await api.verifyDocument("EVR/42");

    const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
    expect(mockFetch).toHaveBeenCalledWith(
      `${apiBase}/api/verify/EVR%2F42`,
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
  });

  it("renders status, document type and date from the backend response", async () => {
    vi.spyOn(api, "verifyDocument").mockResolvedValue({
      found: true,
      evrak_id: "EVR-42",
      source: "case",
      status: "in_progress",
      status_label: "İşlemde",
      document_type: "dilekce",
      received_at: "2026-08-27T10:00:00+03:00",
      institution_id: "belediye",
    });

    render(
      <MemoryRouter initialEntries={["/dogrulama/EVR-42"]}>
        <Routes><Route path="/dogrulama/:id" element={<QrVerifyPage />} /></Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("Bu kayıt EVRAG doğrulama servisi tarafından bulundu.")).toBeInTheDocument();
    expect(screen.getByText("İşlemde")).toBeInTheDocument();
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
  it("renders chart values from the admin stats endpoint", async () => {
    vi.spyOn(adminApi, "fetchAdminStats").mockResolvedValue({
      total_cases: 3,
      today_cases: 1,
      average_processing_hours: 2.5,
      human_review_ratio: 0.5,
      department_distribution: [
        { institution_id: "belediye", department_code: "fen_isleri", count: 2 },
        { institution_id: "belediye", department_code: "imar", count: 1 },
      ],
      draft_metrics: { approved: 1, rejected: 1 },
    });

    render(<AdminPage />);

    expect(await screen.findByRole("heading", { name: "Birim Dağılımı" })).toBeInTheDocument();
    const chart = screen.getByRole("img", { name: "Birimlere göre evrak dağılımı" });
    expect(within(chart).getByText("belediye / fen_isleri")).toBeInTheDocument();
    expect(within(chart).getByText("2 evrak")).toBeInTheDocument();
    expect(within(chart).getByText("belediye / imar")).toBeInTheDocument();
  });
});
