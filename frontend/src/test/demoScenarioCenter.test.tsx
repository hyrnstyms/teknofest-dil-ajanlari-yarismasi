import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DemoScenarioCenter } from "../components/demo/DemoScenarioCenter";
import { demoApi } from "../services/demoApi";

vi.mock("../services/demoApi", () => ({ demoApi: { scenarios: vi.fn(), prepare: vi.fn(), reset: vi.fn() } }));

describe("Demo scenario visibility", () => {
  beforeEach(() => vi.clearAllMocks());
  it("is collapsed by default when the backend demo endpoint is available", async () => {
    vi.mocked(demoApi.scenarios).mockResolvedValue({ items: [{ key: "yol_onarim", title: "Yol onarım", institution_id: "belediye", prepared: false }] });
    render(<MemoryRouter><DemoScenarioCenter token="token"/></MemoryRouter>);
    expect(await screen.findByText("Demo Senaryoları")).toBeInTheDocument();
    expect(screen.queryByText("Yol onarım")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Göster/ }));
    expect(screen.getByText("Yol onarım")).toBeInTheDocument();
  });
  it("is absent when DEMO_MODE disables the backend endpoint", async () => {
    vi.mocked(demoApi.scenarios).mockRejectedValue(new Error("not found"));
    const { container } = render(<MemoryRouter><DemoScenarioCenter token="token"/></MemoryRouter>);
    await waitFor(() => expect(demoApi.scenarios).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });
});
