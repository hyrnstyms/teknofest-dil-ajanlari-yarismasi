from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from backend.app.cases.runtime import get_case_engine
from backend.app.db.repository import AnalysisRepository
from backend.app.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_integrated_domain():
    engine = get_case_engine()
    engine.clear_domain()
    AnalysisRepository(engine=engine.engine).clear()
    yield
    engine.clear_domain()
    AnalysisRepository(engine=engine.engine).clear()


def login(user_key: str) -> dict[str, str]:
    response = client.post("/api/auth/demo-login", json={"user_key": user_key})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def pending_action(response) -> dict:
    assert response.status_code == 200, response.text
    event = None
    for block in response.text.split("\n\n"):
        if block.startswith("event: pending_action"):
            data_line = next(line for line in block.splitlines() if line.startswith("data: "))
            event = json.loads(data_line[6:])["pending_action"]
    assert event is not None, response.text
    return event


def test_yol_onarim_full_lifecycle_and_copilot_confirmation(monkeypatch):
    class RoadWorkflow:
        def run(self, text, document_id=None):
            return {
                "document_id": document_id,
                "raw_text": text,
                "document": {
                    "document_type": "dilekce",
                    "process_intent": "bildirim",
                    "subject_excerpt": "Yol bakım talebi",
                    "request_excerpt": "Çınar Sokak yol deformasyonu incelensin.",
                },
                "extraction": {
                    "fields": {
                        "person_name": {"value": "Ali Yılmaz", "validated": True},
                        "location": {"value": "Çınar Sokak", "validated": True},
                    }
                },
                "legal_analysis": {
                    "verified": True,
                    "deadline_days": 30,
                    "deadline_type": "CALENDAR_DAY",
                    "legal_basis": {
                        "law_number": "3071",
                        "article": "7",
                        "citation": "3071 sayılı Kanun, Madde 7",
                    },
                    "text": "Başvurunun sonucu 30 takvim günü içinde bildirilir.",
                },
                "missing_fields": {
                    "has_blocking_missing": False,
                    "blocking_fields": [],
                    "missing_fields": [],
                    "missing_field_details": [],
                },
                "summary": {"short_summary": "Çınar Sokak yol bakım talebi"},
                "routing": {
                    "recommended_unit": "Fen İşleri Müdürlüğü",
                    "recommended_department_code": "fen_isleri",
                    "reason": "Yol bakım ve onarım sorumluluğu",
                    "evidence": ["Yol deformasyonu bildirimi"],
                    "alternatives": [],
                    "requires_human_review": True,
                },
                "human_review": {"required": True, "status": "pending_review"},
            }

    monkeypatch.setattr("backend.app.main.get_workflow", lambda institution=None: RoadWorkflow())
    ayse = login("ayse_kaya")
    mehmet = login("mehmet_demir")

    intake = client.post(
        "/api/documents/analyze-text",
        headers=ayse,
        json={"text": "Çınar Sokak yol deformasyonu", "institution": "belediye"},
    )
    assert intake.status_code == 200, intake.text
    created = intake.json()
    assert created["case_id"] and created["tracking_code"] and created["citizen_access_token"]

    aggregate = client.get(f"/api/cases/{created['case_id']}", headers=ayse).json()
    assert aggregate["case"]["workflow_status"] == "WAITING_INITIAL_REVIEW"
    assert aggregate["analysis"]["routing"]["recommended_department_code"] == "fen_isleri"
    assert aggregate["deadline"]["deadline_days"] == 30
    assert aggregate["deadline"]["due_at"] is not None
    assert aggregate["deadline"]["legal_basis"]["verified"] is True

    reviewed = client.post(
        f"/api/cases/{created['case_id']}/accept-review",
        headers=ayse,
        json={"expected_version": aggregate["case"]["version"], "confirmed": True},
    ).json()
    stream = client.post(
        "/api/copilot/stream",
        headers=ayse,
        json={"message": "Fen İşlerine gönder.", "case_id": created["case_id"]},
    )
    action = pending_action(stream)
    assert action["type"] == "ROUTE_CASE"
    assert action["payload"]["expected_version"] == reviewed["version"]

    confirmed = client.post("/api/copilot/actions/confirm", headers=ayse, json=action)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["case"]["workflow_status"] == "IN_DEPARTMENT"
    repeated = client.post("/api/copilot/actions/confirm", headers=ayse, json=action)
    assert repeated.status_code == 200
    assert repeated.json() == confirmed.json()

    inbox = client.get("/api/cases/inbox", headers=mehmet).json()["items"]
    assert [item["id"] for item in inbox] == [created["case_id"]]
    version = confirmed.json()["case"]["version"]
    started = client.post(
        f"/api/cases/{created['case_id']}/start",
        headers=mehmet,
        json={"expected_version": version, "confirmed": True},
    ).json()
    action_result = client.post(
        f"/api/cases/{created['case_id']}/department-action",
        headers=mehmet,
        json={
            "action_type": "SAHA_INCELEMESI",
            "result": "Yol deformasyonu tespit edildi.",
            "decision": "Bakım programına alındı.",
            "expected_version": started["version"],
            "confirmed": True,
        },
    ).json()

    draft_action = pending_action(client.post(
        "/api/copilot/stream",
        headers=mehmet,
        json={"message": "Vatandaşa cevap hazırla.", "case_id": created["case_id"]},
    ))
    assert draft_action["type"] == "CREATE_OFFICIAL_DRAFT"
    drafted = client.post(
        "/api/copilot/actions/confirm", headers=mehmet, json=draft_action
    )
    assert drafted.status_code == 200, drafted.text
    draft = drafted.json()["result"]["draft"]
    assert "tamamlandı" not in draft["content"]["body"].casefold()
    assert "bakım programına alındı" in draft["content"]["body"].casefold()

    approved = client.post(
        f"/api/cases/{created['case_id']}/drafts/{draft['id']}/approve",
        headers=mehmet,
        json={
            "expected_version": drafted.json()["case"]["version"],
            "confirmed": True,
        },
    ).json()
    completed = client.post(
        f"/api/cases/{created['case_id']}/complete",
        headers=mehmet,
        json={
            "draft_id": draft["id"],
            "expected_version": approved["case"]["version"],
            "confirmed": True,
        },
    ).json()
    final_aggregate = client.get(f"/api/cases/{created['case_id']}", headers=mehmet).json()
    assert final_aggregate["drafts"][-1]["status"] == "APPROVED"
    closed = client.post(
        f"/api/cases/{created['case_id']}/close",
        headers=ayse,
        json={"expected_version": completed["case"]["version"], "confirmed": True},
    )
    assert closed.json()["workflow_status"] == "CLOSED"

    public = client.get(
        f"/api/public/cases/{created['tracking_code']}",
        params={"token": created["citizen_access_token"]},
    ).json()
    assert public["public_status"] == "Kapatıldı"
    assert public["timeline"][-1]["event"] == "CASE_CLOSED"
    assert "department_actions" not in public


def test_ambiguous_ruhsat_citizen_answer_resumes_routing(monkeypatch):
    class PermitWorkflow:
        def run(self, text, document_id=None):
            return {
                "document_id": document_id,
                "raw_text": text,
                "document": {
                    "document_type": "form",
                    "document_subtype": "ruhsat_basvurusu",
                    "process_intent": "basvuru",
                    "request_excerpt": "Ruhsat başvurusu yapmak istiyorum.",
                },
                "extraction": {"fields": {
                    "person_name": {"value": "Ayşe Vatandaş", "validated": True},
                    "address": {"value": "Çınar Mahallesi", "validated": True},
                    "signature_present": {"value": True, "validated": True},
                    "request": {"value": "Ruhsat başvurusu", "validated": True},
                }},
                "legal_analysis": {},
                "missing_fields": {
                    "has_blocking_missing": True,
                    "permit_ambiguity": {
                        "field": "permit_type",
                        "question": "Başvurunuz hangi ruhsat türüyle ilgilidir?",
                        "options": ["YAPI_RUHSATI", "ISYERI_ACMA_RUHSATI"],
                    },
                },
                "summary": {"short_summary": "Belirsiz ruhsat başvurusu"},
                "routing": {},
                "human_review": {"required": True, "status": "pending_review"},
            }

    monkeypatch.setattr("backend.app.main.get_workflow", lambda institution=None: PermitWorkflow())
    ayse = login("ayse_kaya")
    intake = client.post(
        "/api/documents/analyze-text",
        headers=ayse,
        json={"text": "Ruhsat başvurusu", "institution": "belediye"},
    ).json()
    aggregate = client.get(f"/api/cases/{intake['case_id']}", headers=ayse).json()
    clarification = aggregate["analysis"]["clarification"]
    assert clarification["needs_clarification"] is True
    assert aggregate["analysis"]["routing"] == {}

    requested = client.post(
        f"/api/cases/{intake['case_id']}/citizen-requests",
        headers=ayse,
        json={**clarification, "expected_version": aggregate["case"]["version"], "confirmed": True},
    )
    assert requested.status_code == 200, requested.text
    public = client.get(
        f"/api/public/cases/{intake['tracking_code']}",
        params={"token": intake["citizen_access_token"]},
    ).json()
    assert public["clarification"]["requested_fields"] == ["permit_type"]

    completed = client.post(
        f"/api/public/cases/{intake['tracking_code']}/complete-info",
        params={"token": intake["citizen_access_token"]},
        json={"answers": {"permit_type": "YAPI_RUHSATI"}},
    )
    assert completed.status_code == 200, completed.text
    resumed = client.get(f"/api/cases/{intake['case_id']}", headers=ayse).json()
    assert resumed["case"]["workflow_status"] == "READY_TO_ROUTE"
    assert resumed["analysis"]["routing"]["recommended_department_code"] == "imar_sehircilik"

    routed = client.post(
        f"/api/cases/{intake['case_id']}/route",
        headers=ayse,
        json={
            "department_code": "imar_sehircilik",
            "routing_snapshot": resumed["analysis"]["routing"],
            "expected_version": resumed["case"]["version"],
            "confirmed": True,
        },
    )
    assert routed.status_code == 200, routed.text
    assert routed.json()["workflow_status"] == "IN_DEPARTMENT"
    assert routed.json()["current_department_code"] == "imar_sehircilik"
