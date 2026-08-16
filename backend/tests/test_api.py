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
