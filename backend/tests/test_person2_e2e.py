from copy import deepcopy

from fastapi import FastAPI
from fastapi.testclient import TestClient
import backend.app.intelligence.preview_router as preview_module
from backend.app.intelligence.case_writing import CaseWritingService
from backend.app.intelligence.preview_router import router as preview_router

app = FastAPI()
app.include_router(preview_router)
client = TestClient(app)

def test_scenario_a_yol_onarim():
    # Scenario A
    # Initial request
    resp = client.post("/api/cases/case-123/ai/clarification-preview", json={
        "context": {
            "document": {"document_type": "dilekce", "process_intent": "basvuru"},
            "missing_fields": {"has_blocking_missing": False},
            "routing": {"recommended_unit": "fen_isleri_mudurlugu", "needs_human_review": False},
            "raw_text": "yol bakım talebi",
            "institution_id": "belediye"
        }
    })
    assert resp.status_code == 200
    assert resp.json()["persisted"] is False

    # Official Response Preview - Attempt unsupported completion
    resp = client.post("/api/cases/case-123/ai/official-response-preview", json={
        "context": {
            "department_action": {
                "result": "Yol deformasyonu tespit edildi.",
                "decision": "Bakım programına alındı.",
                "verified": True,
                "case_id": "case-123"
            },
            "document": {"document_type": "dilekce", "process_intent": "basvuru"},
            "routing": {"recommended_unit": "fen_isleri_mudurlugu"}
        }
    })
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["persisted"] is False
    assert data["canonical_draft_type"] == "OFFICIAL_RESPONSE"
    assert "programına alındı" in data["draft"]["body"]
    assert "onarım tamamlandı" not in data["draft"]["body"].casefold()
    assert data["quality"]["status"] != "fail"

def test_scenario_b_ambiguous_ruhsat():
    # Clarification
    request_body = {
        "context": {
            "document": {"document_type": "diger", "process_intent": "diger"},
            "missing_fields": {"has_blocking_missing": True, "missing_fields": ["ruhsat_turu"]},
            "routing": {"needs_human_review": True, "ambiguity_reason": "Ruhsat türü belirsiz."},
            "raw_text": "Ruhsat başvurusu yapmak istiyorum."
        }
    }
    before = deepcopy(request_body)
    resp = client.post("/api/cases/case-456/ai/clarification-preview", json=request_body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["persisted"] is False
    assert data["blocking"] is True
    assert data["requested_fields"] == ["permit_type"]
    assert data["question_type"] == "choice"
    assert request_body == before

def test_scenario_c_deadline_unknown():
    resp = client.post("/api/cases/case-789/ai/deadline-evaluation", json={
        "context": {
            "received_at": "2023-10-12T10:00:00Z",
            "legal_analysis": {
                "evidence": [],
                "sources": []
            }
        }
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["due_at"] is None
    assert data["risk_level"] == "UNKNOWN"

def test_scenario_d_verified_deadline():
    resp = client.post("/api/cases/case-000/ai/deadline-evaluation", json={
        "context": {
            "received_at": "2023-10-12T10:00:00Z",
            "legal_analysis": {
                "evidence": [{"text": "Başvurular 30 takvim günü içinde sonuçlandırılır.", "source": "K1"}],
                "sources": [{"law_number": "3071", "title": "Dilekçe Hakkı"}]
            }
        }
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["deadline_days"] == 30
    assert data["deadline_type"] == "CALENDAR_DAY"
    assert data["due_at"] == "2023-11-11T10:00:00+00:00"
    assert data["legal_basis"] == {
        "verified": True,
        "law_number": "3071",
        "article": None,
        "citation": "3071 sayılı Kanun",
    }
    assert data["persisted"] is False
    assert data["operational_priority_separate"] is True

def test_negative_no_department_action():
    resp = client.post("/api/cases/case-123/ai/official-response-preview", json={
        "context": {}
    })
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "verified_department_action_required"
    assert resp.json()["detail"]["context"]["case_id"] == "case-123"

def test_negative_unverified_department_action():
    resp = client.post("/api/cases/case-123/ai/official-response-preview", json={
        "context": {
            "department_action": {"verified": False, "result": "Test"}
        }
    })
    assert resp.status_code == 409

def test_negative_other_case_department_action():
    resp = client.post("/api/cases/case-123/ai/official-response-preview", json={
        "context": {
            "department_action": {"verified": True, "result": "Test", "case_id": "other-case"}
        }
    })
    assert resp.status_code == 409


def test_negative_department_action_without_case_identity():
    resp = client.post("/api/cases/case-123/ai/official-response-preview", json={
        "context": {
            "department_action": {"verified": True, "result": "Test"}
        }
    })
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "verified_department_action_required"


def test_quality_blocks_unsupported_completion_at_preview_boundary(monkeypatch):
    class UnsupportedCompletionWriter:
        def draft(self, context=None, **kwargs):
            return {
                "draft": {
                    "subject": "Başvurunuz Hk.",
                    "body": "Yol onarımı tamamlanmıştır.",
                }
            }

    monkeypatch.setattr(
        preview_module,
        "_writing",
        CaseWritingService(writing_agent=UnsupportedCompletionWriter()),
    )
    resp = client.post("/api/cases/case-123/ai/official-response-preview", json={
        "context": {
            "department_action": {
                "case_id": "case-123",
                "result": "Yol deformasyonu tespit edildi.",
                "decision": "Bakım programına alındı.",
                "verified": True,
            }
        }
    })

    assert resp.status_code == 200
    data = resp.json()
    assert data["blocked"] is True
    assert data["quality"]["status"] == "fail"
    assert "department_action_contradiction" in data["quality"]["checks"]

def test_negative_deadline_unverified_evidence():
    resp = client.post("/api/cases/case-789/ai/deadline-evaluation", json={
        "context": {
            "received_at": "2023-10-12T10:00:00Z",
            "legal_analysis": {
                "evidence": ["30 gün içinde çözülmeli"] # Not a dict with source, just unverified string
            }
        }
    })
    assert resp.status_code == 200
    data = resp.json()
    # It might extract duration, but legal basis is not verified if there is no verified source
    assert data["risk_level"] == "UNKNOWN"

def test_negative_deadline_received_at_absent():
    resp = client.post("/api/cases/case-000/ai/deadline-evaluation", json={
        "context": {
            "received_at": None,
            "legal_analysis": {
                "evidence": [{"text": "30 takvim günü", "source": "K1"}],
                "sources": [{"law_number": "3071"}]
            }
        }
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["due_at"] is None
    assert data["risk_level"] == "UNKNOWN"


def test_validation_error_uses_frozen_envelope():
    resp = client.post("/api/cases/case-123/ai/clarification-preview", json={
        "context": {"originator": "not-an-object"}
    })
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "validation_error"
    assert detail["message"]
    assert detail["context"]["errors"]


def test_preview_does_not_expose_private_reasoning_fields():
    resp = client.post("/api/cases/case-123/ai/clarification-preview", json={
        "context": {
            "raw_text": "Ruhsat başvurusu yapmak istiyorum.",
            "missing_fields": {"has_blocking_missing": True},
        }
    })
    assert resp.status_code == 200

    forbidden = {"chain_of_thought", "chain-of-thought", "reasoning_trace", "thoughts"}

    def keys(value):
        if isinstance(value, dict):
            for key, child in value.items():
                yield str(key).casefold()
                yield from keys(child)
        elif isinstance(value, list):
            for child in value:
                yield from keys(child)

    assert forbidden.isdisjoint(set(keys(resp.json())))
