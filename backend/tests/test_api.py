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

def test_ready(monkeypatch):
    class FakeResponse:
        status_code = 200

    class FakeStore:
        client = type(
            "FakeClient",
            (),
            {"get_collections": lambda self: []},
        )()

    monkeypatch.setattr("requests.get", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr(
        "backend.app.main._get_embedding_service_singleton",
        lambda: type("FakeEmbedding", (), {"model": object()})(),
    )
    monkeypatch.setattr(
        "backend.app.main._get_qdrant_store_singleton",
        lambda: FakeStore(),
    )

    res = client.get("/ready")
    assert res.status_code == 200
    assert res.json()["ready"] is True


def test_ready_reuses_embedding_and_qdrant_singletons(monkeypatch):
    from backend.app.main import (
        _get_embedding_service_singleton,
        _get_qdrant_store_singleton,
    )

    constructor_calls = {"embedding": 0, "qdrant": 0}

    class FakeEmbeddingService:
        def __init__(self):
            constructor_calls["embedding"] += 1
            self.model = object()

    class FakeQdrantClient:
        def get_collections(self):
            return []

    class FakeQdrantStore:
        def __init__(self):
            constructor_calls["qdrant"] += 1
            self.client = FakeQdrantClient()

    class FakeOllamaResponse:
        status_code = 200

    monkeypatch.setattr("requests.get", lambda *args, **kwargs: FakeOllamaResponse())
    monkeypatch.setattr(
        "backend.app.rag.embedding_service.EmbeddingService",
        FakeEmbeddingService,
    )
    monkeypatch.setattr(
        "backend.app.rag.qdrant_store.QdrantStore",
        FakeQdrantStore,
    )

    _get_embedding_service_singleton.cache_clear()
    _get_qdrant_store_singleton.cache_clear()
    try:
        responses = [client.get("/ready") for _ in range(3)]

        assert all(response.status_code == 200 for response in responses)
        assert all(response.json()["ready"] is True for response in responses)
        assert constructor_calls == {"embedding": 1, "qdrant": 1}
    finally:
        _get_embedding_service_singleton.cache_clear()
        _get_qdrant_store_singleton.cache_clear()


def test_ready_checks_evren_models_without_inference(monkeypatch):
    from backend.app.llm.settings import LLMSettings

    calls = []

    class FakeResponse:
        status_code = 200

    class FakeStore:
        client = type(
            "FakeClient",
            (),
            {"get_collections": lambda self: []},
        )()

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse()

    monkeypatch.setenv("LLM_PROVIDER", "evren")
    monkeypatch.setattr(
        LLMSettings,
        "EVREN_BASE_URL",
        "https://example.invalid/v1/",
    )
    monkeypatch.setattr(LLMSettings, "EVREN_API_KEY", "test-key")
    monkeypatch.setattr("requests.get", fake_get)
    monkeypatch.setattr(
        "backend.app.main._get_embedding_service_singleton",
        lambda: type("FakeEmbedding", (), {"model": object()})(),
    )
    monkeypatch.setattr(
        "backend.app.main._get_qdrant_store_singleton",
        lambda: FakeStore(),
    )

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["ready"] is True
    assert response.json()["services"]["llm"] == {
        "provider": "evren",
        "status": "ok",
    }
    assert response.json()["services"]["ollama"]["status"] == "ok"
    assert calls == [
        (
            "https://example.invalid/v1/models",
            {
                "headers": {"Authorization": "Bearer test-key"},
                "timeout": 5,
            },
        )
    ]


def test_ready_preserves_ollama_provider_check(monkeypatch):
    from backend.app.llm.settings import LLMSettings

    calls = []

    class FakeResponse:
        status_code = 200

    class FakeStore:
        client = type(
            "FakeClient",
            (),
            {"get_collections": lambda self: []},
        )()

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse()

    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setattr(
        LLMSettings,
        "OLLAMA_URL",
        "http://ollama.invalid",
    )
    monkeypatch.setattr("requests.get", fake_get)
    monkeypatch.setattr(
        "backend.app.main._get_embedding_service_singleton",
        lambda: type("FakeEmbedding", (), {"model": object()})(),
    )
    monkeypatch.setattr(
        "backend.app.main._get_qdrant_store_singleton",
        lambda: FakeStore(),
    )

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["ready"] is True
    assert response.json()["services"]["llm"] == {
        "provider": "ollama",
        "status": "ok",
    }
    assert calls == [
        (
            "http://ollama.invalid",
            {"timeout": 5},
        )
    ]

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

    def fake_handle(
        message,
        current_draft=None,
        workflow_context=None,
        resolved_mode=None,
    ):
        calls.append((message, current_draft, workflow_context, resolved_mode))
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
    assert calls == [("Evrakı nasıl yüklerim?", None, {}, "kilavuz")]


def test_general_chat_labels_mod_d_small_talk(monkeypatch):
    calls = []

    def fake_handle(
        message,
        current_draft=None,
        workflow_context=None,
        resolved_mode=None,
    ):
        calls.append((message, current_draft, workflow_context, resolved_mode))
        return "Merhaba, size nasıl yardımcı olabilirim?"

    monkeypatch.setattr("backend.app.main.handle_chat_message", fake_handle)

    response = client.post(
        "/api/chat/message",
        json={"message": "Merhaba"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "mode": "kucuk_sohbet",
        "status": "answered",
        "sohbet_yaniti": "Merhaba, size nasıl yardımcı olabilirim?",
        "updated_draft": None,
        "validation_errors": [],
        "validation_warnings": [],
    }
    assert calls == [("Merhaba", None, {}, "kucuk_sohbet")]


def test_general_chat_routes_mod_b_to_handle_chat_message(monkeypatch):
    calls = []

    def fake_handle(
        message,
        current_draft=None,
        workflow_context=None,
        resolved_mode=None,
    ):
        calls.append((message, current_draft, workflow_context, resolved_mode))
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
    assert calls == [
        ("4982 sayılı Kanun Madde 11 nedir?", None, {}, "mevzuat")
    ]


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

    def fake_handle(
        message,
        current_draft=None,
        workflow_context=None,
        resolved_mode=None,
    ):
        calls.append((message, current_draft, workflow_context, resolved_mode))
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


def test_general_chat_uses_router_legal_mode_once(monkeypatch):
    route_calls = []
    handler_calls = []

    def fake_resolve(message):
        route_calls.append(message)
        return "mevzuat"

    def fake_handle(
        message,
        current_draft=None,
        workflow_context=None,
        resolved_mode=None,
    ):
        handler_calls.append(
            (message, current_draft, workflow_context, resolved_mode)
        )
        return "Doğrulanmış kaynaklı cevap."

    monkeypatch.setattr("backend.app.main.resolve_chat_mode", fake_resolve)
    monkeypatch.setattr("backend.app.main.handle_chat_message", fake_handle)
    message = "Dilekçelere kaç günde cevap vermemiz gerekiyor?"

    response = client.post("/api/chat/message", json={"message": message})

    assert response.status_code == 200
    assert response.json()["mode"] == "mevzuat"
    assert response.json()["sohbet_yaniti"] == "Doğrulanmış kaynaklı cevap."
    assert route_calls == [message]
    assert handler_calls == [(message, None, {}, "mevzuat")]


def test_general_chat_rejects_router_d_without_analysis_context(monkeypatch):
    route_calls = []
    monkeypatch.setattr(
        "backend.app.main.resolve_chat_mode",
        lambda message: route_calls.append(message) or "taslak_duzenleme",
    )
    monkeypatch.setattr(
        "backend.app.main.handle_chat_message",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Bağlam yokken chat handler çağrılmamalı")
        ),
    )
    message = "Giriş cümlesini daha nazik yapar mısın?"

    response = client.post("/api/chat/message", json={"message": message})

    assert response.status_code == 200
    assert response.json()["mode"] == "taslak_duzenleme"
    assert response.json()["status"] == "rejected"
    assert response.json()["sohbet_yaniti"] == (
        "Önce bir evrak analiz edin, sonra taslak düzenleme özelliğini "
        "kullanabilirsiniz."
    )
    assert route_calls == [message]


def test_general_chat_applies_router_d_atomically(monkeypatch):
    original_draft = {
        "draft_type": "ust_yazi",
        "draft": {"subject": "Eski Konu", "body": "Eski gövde."},
    }
    updated_draft = {
        "draft_type": "ust_yazi",
        "draft": {"subject": "Eski Konu", "body": "Yeni gövde."},
        "official_rendered_text": "Yeni gövde.",
    }
    analysis_store["router-mod-c"] = {
        "draft": deepcopy(original_draft),
        "extraction": {"fields": {}},
        "routing": {"recommended_unit": "Yazı İşleri"},
        "human_review": {"status": "pending_review"},
        "audit_history": [],
    }
    route_calls = []
    handler_calls = []

    def fake_resolve(message):
        route_calls.append(message)
        return "taslak_duzenleme"

    def fake_handle(
        message,
        current_draft=None,
        workflow_context=None,
        resolved_mode=None,
    ):
        handler_calls.append(
            (message, current_draft, workflow_context, resolved_mode)
        )
        return {
            "status": "applied",
            "sohbet_yaniti": "Gövde değişikliği uygulandı.",
            "updated_draft": deepcopy(updated_draft),
            "validation_errors": [],
            "validation_warnings": [],
        }

    monkeypatch.setattr("backend.app.main.resolve_chat_mode", fake_resolve)
    monkeypatch.setattr("backend.app.main.handle_chat_message", fake_handle)
    message = "Giriş cümlesini daha nazik yapar mısın?"

    response = client.post(
        "/api/chat/message",
        json={"message": message, "analysis_id": "router-mod-c"},
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "taslak_duzenleme"
    assert response.json()["status"] == "applied"
    assert route_calls == [message]
    assert len(handler_calls) == 1
    assert handler_calls[0][3] == "taslak_duzenleme"
    assert analysis_store["router-mod-c"]["draft"] == updated_draft
    assert analysis_store["router-mod-c"]["human_review"][
        "mod_c_original_draft"
    ] == original_draft


def test_chat_forwards_selected_institution_without_analysis(monkeypatch):
    calls = []

    monkeypatch.setattr(
        "backend.app.main.resolve_chat_mode",
        lambda message: "institution",
    )

    def fake_handle(message, current_draft=None, workflow_context=None, resolved_mode=None):
        calls.append((current_draft, workflow_context, resolved_mode))
        return "Fen İşleri Müdürlüğü"

    monkeypatch.setattr("backend.app.main.handle_chat_message", fake_handle)
    response = client.post(
        "/api/chat/message",
        json={
            "message": "Bu kurumda yol işleri hangi birimle ilgilidir?",
            "institution": "belediye",
        },
    )

    assert response.status_code == 200
    assert calls == [(None, {"institution": "belediye"}, "institution")]


def test_chat_drops_analysis_context_when_selected_institution_mismatches(monkeypatch):
    analysis_store["kaymak-context"] = {
        "kurum_profili_id": "kaymakamlik",
        "draft": {"draft": {"subject": "Kaymakamlık evrakı", "body": "Metin"}},
        "extraction": {"fields": {"subject": {"value": "Kaymakamlık evrakı"}}},
        "routing": {"recommended_unit": "İlçe Millî Eğitim Müdürlüğü"},
    }
    calls = []

    monkeypatch.setattr(
        "backend.app.main.resolve_chat_mode",
        lambda message: "active_document",
    )

    def fake_handle(message, current_draft=None, workflow_context=None, resolved_mode=None):
        calls.append((current_draft, workflow_context, resolved_mode))
        return "Bu soruyu yanıtlamak için önce bir evrak analizi açın."

    monkeypatch.setattr("backend.app.main.handle_chat_message", fake_handle)
    response = client.post(
        "/api/chat/message",
        json={
            "message": "Bu evrakı özetle",
            "analysis_id": "kaymak-context",
            "institution": "belediye",
        },
    )

    assert response.status_code == 200
    assert calls == [(None, {"institution": "belediye"}, "active_document")]
    assert "Kaymakamlık evrakı" not in response.json()["sohbet_yaniti"]
