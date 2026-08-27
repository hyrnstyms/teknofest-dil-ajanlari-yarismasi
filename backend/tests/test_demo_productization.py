from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.cases.exports import approved_export_context, render_case_pdf
from backend.app.cases.runtime import get_case_engine
from backend.app.db.repository import AnalysisRepository
from backend.app.main import app
from backend.app.official_writing.docx_renderer import render_to_docx

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_domain(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    engine = get_case_engine(); engine.clear_domain(); AnalysisRepository(engine=engine.engine).clear()
    yield
    engine.clear_domain(); AnalysisRepository(engine=engine.engine).clear()


def login(key: str) -> dict[str, str]:
    response = client.post("/api/auth/demo-login", json={"user_key": key})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_demo_personas_include_both_institutions_and_scenarios_are_idempotent():
    personas = client.get("/api/demo/personas")
    assert personas.status_code == 200
    assert {item["institution_id"] for item in personas.json()["items"]} == {"belediye", "kaymakamlik"}
    headers = login("ayse_kaya")
    first = client.post("/api/demo/scenarios/yol_onarim/prepare", headers=headers)
    second = client.post("/api/demo/scenarios/yol_onarim/prepare", headers=headers)
    assert first.status_code == second.status_code == 200
    assert first.json()["case"]["id"] == second.json()["case"]["id"]
    assert first.json()["citizen_url"].startswith("/takip/")
    assert "token=" in first.json()["citizen_url"]
    reset = client.post("/api/demo/scenarios/reset", headers=headers)
    assert reset.status_code == 200
    assert reset.json()["deleted_demo_cases"] == 1


def test_kaymakamlik_scenario_uses_real_profile_unit():
    headers = login("selin_aksoy")
    response = client.post("/api/demo/scenarios/kaymakamlik_egitim/prepare", headers=headers)
    assert response.status_code == 200
    case_id = response.json()["case"]["id"]
    aggregate = client.get(f"/api/cases/{case_id}", headers=headers).json()
    assert aggregate["case"]["institution_id"] == "kaymakamlik"
    assert aggregate["analysis"]["recommended_department_code"] == "milli_egitim"


def test_approved_case_draft_renders_docx_pdf_and_qr():
    aggregate = {
        "case": {"tracking_code": "EVR-TEST-001", "institution_id": "belediye", "current_department_code": "fen_isleri", "originator_type": "VATANDAS", "originator_name": "Ali Yılmaz"},
        "analysis": {"routing": {"recommended_unit": "Fen İşleri Müdürlüğü"}, "extraction": {"fields": {"subject": {"value": "Yol bakım talebi", "validated": True}}}},
        "drafts": [{"id": "draft-1", "status": "APPROVED", "draft_type": "OFFICIAL_RESPONSE", "content": {"subject": "Başvurunuz Hk.", "recipient": "Ali Yılmaz", "body": "Başvurunuz incelenmiş ve bakım programına alınmıştır."}}],
    }
    context, _ = approved_export_context(aggregate, "draft-1")
    docx = render_to_docx(context, evrak_id="EVR-TEST-001").getvalue()
    pdf = render_case_pdf(context, "EVR-TEST-001").getvalue()
    assert docx.startswith(b"PK")
    assert pdf.startswith(b"%PDF")
