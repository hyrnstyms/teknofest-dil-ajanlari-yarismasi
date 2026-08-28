from __future__ import annotations

import io
import zipfile

import fitz

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
        "drafts": [{"id": "draft-1", "status": "APPROVED", "draft_type": "OFFICIAL_RESPONSE", "content": {"subject": "Başvurunuz Hk.", "recipient": "Ali Yılmaz", "body": "Başvurunuz kapsamında ilgili bölgede yapılan incelemede yol yüzeyinde deformasyon tespit edilmiştir. çğıöşü ÇĞİÖŞÜ"}}],
    }
    context, _ = approved_export_context(aggregate, "draft-1")
    assert context["konu"] == "Başvurunuz Hk"
    assert aggregate["drafts"][0]["content"]["subject"] == "Başvurunuz Hk."
    docx = render_to_docx(context, evrak_id="EVR-TEST-001").getvalue()
    pdf = render_case_pdf(context, "EVR-TEST-001").getvalue()
    assert docx.startswith(b"PK")
    assert pdf.startswith(b"%PDF")
    with zipfile.ZipFile(io.BytesIO(docx)) as archive:
        document_xml = archive.read("word/document.xml").decode("utf-8")
    assert "çğıöşü ÇĞİÖŞÜ" in document_xml
    with fitz.open(stream=pdf, filetype="pdf") as document:
        pdf_text = "\n".join(page.get_text() for page in document)
    assert "deformasyon tespit edilmiştir" in " ".join(pdf_text.split())
    assert "EVR-TEST-001" in pdf_text

def test_citizen_example_is_explicit_allowlisted_post_with_real_demo_token():
    response = client.post("/api/demo/citizen-examples/yol_onarim")
    assert response.status_code == 200
    payload = response.json()
    assert payload["scenario_key"] == "yol_onarim"
    assert "demo-token" not in payload["citizen_url"]
    tracking, token = payload["citizen_url"].split("/takip/", 1)[1].split("?token=", 1)
    assert client.get(f"/api/public/cases/{tracking}", params={"token": token}).status_code == 200
    assert client.post("/api/demo/citizen-examples/dis_kurum_afet").status_code == 404


def test_yol_demo_persists_verified_indexed_legal_evidence_and_late_states():
    ayse = login("ayse_kaya")
    early = client.post("/api/demo/scenarios/yol_onarim/prepare", headers=ayse).json()
    aggregate = client.get(f"/api/cases/{early['case']['id']}", headers=ayse).json()
    legal = aggregate["analysis"]["legal_analysis"]
    assert legal["verified"] is True
    assert legal["sources"][0]["law_number"] == "2709"
    assert legal["sources"][0]["madde_no"] == "127"
    assert legal["sources"][0]["trusted_source"] is True
    assert "2709 sayılı Türkiye Cumhuriyeti Anayasası, Madde 127" in aggregate["analysis"]["routing"]["evidence"]
    late = client.post("/api/demo/scenarios/yol_onarim_yedek/prepare", headers=ayse).json()
    completed = client.post("/api/demo/scenarios/tamamlanmis_dosya/prepare", headers=ayse).json()
    assert late["case"]["workflow_status"] == "WAITING_FINAL_APPROVAL"
    assert completed["case"]["workflow_status"] == "COMPLETED"
