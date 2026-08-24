from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app, analysis_store
from backend.app.telemetry.service import telemetry_service

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_teardown():
    # Clear state before each test
    analysis_store.clear()
    telemetry_service.records.clear()
    yield

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

def test_ready():
    res = client.get("/ready")
    assert res.status_code == 200
    # Even if degraded, status code should be 200, but ready field might be false

def test_analyze_text(monkeypatch):
    # Mock workflow to avoid heavy LLM calls
    from backend.app.graph.workflow import KamuaiWorkflow
    class MockWorkflow:
        def run(self, text, document_id=None):
            return {
                "document": {"document_type": "dilekce"},
                "human_review": {"required": True, "status": "pending_review"},
                "draft": {"draft_text": "hello"}
            }
    
    monkeypatch.setattr("backend.app.main.get_workflow", lambda: MockWorkflow())
    
    res = client.post("/api/documents/analyze-text", json={"text": "test_text"})
    assert res.status_code == 200
    data = res.json()
    assert "analysis_id" in data
    assert data["document"]["document_type"] == "dilekce"
    assert len(telemetry_service.records) == 1

def test_get_analysis_not_found():
    res = client.get("/api/analysis/invalid_id")
    assert res.status_code == 404
    assert res.json()["detail"]["code"] == "analysis_not_found"
    assert "bulunamadı" in res.json()["detail"]["message"].lower()

def test_approve_edit_reject(monkeypatch):
    # Put a mock analysis in store
    analysis_store["test_id"] = {
        "human_review": {"status": "pending_review"},
        "draft": {"draft_text": "original"}
    }
    from backend.app.telemetry.models import TelemetryRecord
    telemetry_service.records["test_id"] = TelemetryRecord(analysis_id="test_id")
    
    # Approve
    res = client.post("/api/analysis/test_id/approve")
    assert res.status_code == 200
    assert analysis_store["test_id"]["human_review"]["status"] == "approved"
    assert telemetry_service.records["test_id"].human_review_status == "approved"
    
    # Edit
    res = client.post("/api/analysis/test_id/edit", json={"body": "edited text"})
    assert res.status_code == 200
    assert analysis_store["test_id"]["human_review"]["status"] == "edited"
    assert analysis_store["test_id"]["human_review"]["original_draft"]["draft_text"] == "original"
    assert analysis_store["test_id"]["draft"]["edited_draft"]["body"] == "edited text"
    
    # Reject
    res = client.post("/api/analysis/test_id/reject", json={"reason": "bad text"})
    assert res.status_code == 200
    assert analysis_store["test_id"]["human_review"]["status"] == "rejected"
    assert analysis_store["test_id"]["human_review"]["reject_reason"] == "bad text"

def test_roi_summary_empty():
    res = client.get("/api/roi/summary")
    assert res.status_code == 200
    assert res.json()["processed_documents"] == 0
    
def test_system_status():
    res = client.get("/api/system/status")
    assert res.status_code == 200
    assert "api" in res.json()
    assert "qdrant" in res.json()

def test_upload_txt(tmp_path):
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("dummy test text")
    
    # Mock analyze-text so upload doesn't run LLM
    from backend.app.main import app
    def mock_analyze(req):
        return {"analysis_id": "mock_upload_123", "text": req.text}
    app.dependency_overrides = {}  # or monkeypatch analyze_text
    
    with open(txt_file, "rb") as f:
        # Actually this will call the real analyze_text. I should monkeypatch get_workflow
        from backend.app.graph.workflow import KamuaiWorkflow
        class MockWorkflow:
            def run(self, text, document_id=None):
                return {"text": text, "document_id": document_id}
        import backend.app.main
        backend.app.main.get_workflow = lambda: MockWorkflow()

        res = client.post("/api/documents/upload", files={"file": ("test.txt", f, "text/plain")})
        assert res.status_code == 200
        assert res.json()["text"] == "dummy test text"


def test_chat_edit_draft_updates_analysis_state_atomically(monkeypatch):
    original_draft = {
        "draft_type": "ust_yazi",
        "draft": {
            "subject": "Eski Başvuru Konusu",
            "body": "Eski başvuru metni.",
        },
    }
    updated_draft = {
        "draft_type": "ust_yazi",
        "draft": {
            "subject": "Yeni Başvuru Konusu",
            "body": "Eski başvuru metni.",
        },
        "mod_c_validated_context": {"konu": "Yeni Başvuru Konusu"},
    }
    analysis_store["mod-c-test"] = {
        "draft": deepcopy(original_draft),
        "extraction": {},
        "routing": {},
        "human_review": {"status": "pending_review"},
        "audit_history": [],
    }
    state_before = analysis_store["mod-c-test"]

    monkeypatch.setattr(
        "backend.app.main.handle_draft_edit",
        lambda message, current_draft, workflow_context: {
            "status": "applied",
            "sohbet_yaniti": "Konu değişikliği hazırlandı.",
            "updated_draft": deepcopy(updated_draft),
            "validation_errors": [],
            "validation_warnings": [],
        },
    )

    response = client.post(
        "/api/analysis/mod-c-test/chat/edit-draft",
        json={"message": "Taslak konusunu değiştir."},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "applied"
    stored = analysis_store["mod-c-test"]
    assert stored is not state_before
    assert stored["draft"] == updated_draft
    assert stored["human_review"]["status"] == "edited"
    assert stored["human_review"]["mod_c_original_draft"] == original_draft
    assert stored["audit_history"][-1]["event"] == "draft_edited_via_chat"


def test_chat_edit_draft_keeps_state_unchanged_when_edit_is_rejected(
    monkeypatch,
):
    analysis_store["mod-c-rejected"] = {
        "draft": {
            "draft_type": "diger",
            "draft": {"subject": "Konu", "body": "Gövde"},
        },
        "human_review": {"status": "pending_review"},
        "audit_history": [],
    }
    original_state = deepcopy(analysis_store["mod-c-rejected"])

    monkeypatch.setattr(
        "backend.app.main.handle_draft_edit",
        lambda message, current_draft, workflow_context: {
            "status": "rejected",
            "sohbet_yaniti": "Taslak türü desteklenmiyor.",
            "updated_draft": None,
            "validation_errors": [],
            "validation_warnings": [],
        },
    )

    response = client.post(
        "/api/analysis/mod-c-rejected/chat/edit-draft",
        json={"message": "Taslak gövdesini değiştir."},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert analysis_store["mod-c-rejected"] == original_state


def test_general_chat_routes_mod_a_without_analysis_id(monkeypatch):
    calls = []

    def fake_handle(message, current_draft=None, workflow_context=None):
        calls.append((message, current_draft, workflow_context))
        return "Evrak yükleme alanını kullanabilirsiniz."

    monkeypatch.setattr("backend.app.main.handle_chat_message", fake_handle)

    response = client.post(
        "/api/chat/message",
        json={"message": "Evrakı nasıl yüklerim?"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "mode": "kilavuz",
        "status": "answered",
        "sohbet_yaniti": "Evrak yükleme alanını kullanabilirsiniz.",
        "updated_draft": None,
        "validation_errors": [],
        "validation_warnings": [],
    }
    assert calls == [("Evrakı nasıl yüklerim?", None, {})]


def test_general_chat_routes_mod_b_to_handle_chat_message(monkeypatch):
    calls = []

    def fake_handle(message, current_draft=None, workflow_context=None):
        calls.append((message, current_draft, workflow_context))
        return "Kaynaklı mevzuat cevabı. [4982, Madde 11]"

    monkeypatch.setattr("backend.app.main.handle_chat_message", fake_handle)

    response = client.post(
        "/api/chat/message",
        json={"message": "4982 sayılı Kanun Madde 11 nedir?"},
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "mevzuat"
    assert response.json()["status"] == "answered"
    assert "[4982, Madde 11]" in response.json()["sohbet_yaniti"]
    assert calls == [("4982 sayılı Kanun Madde 11 nedir?", None, {})]


def test_general_chat_routes_mod_c_and_updates_state_atomically(monkeypatch):
    original_draft = {
        "draft_type": "ust_yazi",
        "draft": {"subject": "Eski Konu", "body": "Eski gövde."},
    }
    updated_draft = {
        "draft_type": "ust_yazi",
        "draft": {"subject": "Yeni Konu", "body": "Eski gövde."},
        "official_rendered_text": "Konu: Yeni Konu",
    }
    analysis_store["general-mod-c"] = {
        "draft": deepcopy(original_draft),
        "extraction": {"fields": {}},
        "routing": {"recommended_unit": "Yazı İşleri"},
        "human_review": {"status": "pending_review"},
        "audit_history": [],
    }
    state_before = analysis_store["general-mod-c"]
    calls = []

    def fake_handle(message, current_draft=None, workflow_context=None):
        calls.append((message, current_draft, workflow_context))
        return {
            "status": "applied",
            "sohbet_yaniti": "Konu değişikliği uygulandı.",
            "updated_draft": deepcopy(updated_draft),
            "validation_errors": [],
            "validation_warnings": [],
        }

    monkeypatch.setattr("backend.app.main.handle_chat_message", fake_handle)

    response = client.post(
        "/api/chat/message",
        json={
            "message": "Taslak konusunu Yeni Konu olarak değiştir.",
            "analysis_id": "general-mod-c",
        },
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "taslak_duzenleme"
    assert response.json()["status"] == "applied"
    assert calls[0][1] == original_draft
    assert calls[0][2]["routing"] == {"recommended_unit": "Yazı İşleri"}
    stored = analysis_store["general-mod-c"]
    assert stored is not state_before
    assert stored["draft"] == updated_draft
    assert stored["human_review"]["mod_c_original_draft"] == original_draft
    assert stored["audit_history"][-1]["event"] == "draft_edited_via_chat"


def test_general_chat_rejects_mod_c_without_analysis_id_before_handler(
    monkeypatch,
):
    monkeypatch.setattr(
        "backend.app.main.handle_chat_message",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Chat handler çağrılmamalı")
        ),
    )

    response = client.post(
        "/api/chat/message",
        json={"message": "Taslak konusunu değiştir."},
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "taslak_duzenleme"
    assert response.json()["status"] == "rejected"
    assert response.json()["sohbet_yaniti"] == (
        "Önce bir evrak analiz edin, sonra taslak düzenleme özelliğini "
        "kullanabilirsiniz."
    )


def test_general_chat_rejects_mod_c_when_analysis_has_no_draft(monkeypatch):
    analysis_store["without-draft"] = {
        "human_review": {"status": "pending_review"},
        "audit_history": [],
    }
    original_state = deepcopy(analysis_store["without-draft"])
    monkeypatch.setattr(
        "backend.app.main.handle_chat_message",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Chat handler çağrılmamalı")
        ),
    )

    response = client.post(
        "/api/chat/message",
        json={
            "message": "Taslak gövdesini değiştir.",
            "analysis_id": "without-draft",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert response.json()["sohbet_yaniti"] == (
        "Önce bir evrak analiz edin, sonra taslak düzenleme özelliğini "
        "kullanabilirsiniz."
    )
    assert analysis_store["without-draft"] == original_state


def test_general_chat_returns_not_found_for_unknown_analysis_id():
    response = client.post(
        "/api/chat/message",
        json={
            "message": "Evrakı nasıl yüklerim?",
            "analysis_id": "unknown-analysis",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "analysis_not_found"
