import pytest
from fastapi.testclient import TestClient
from backend.app.main import app, analysis_store
import uuid

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_store():
    analysis_store.clear()
    yield
    analysis_store.clear()

def test_get_analyses_empty():
    res = client.get("/api/analyses")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0

def test_get_analyses_pagination_and_filter():
    # Insert mocks
    for i in range(5):
        id_ = str(uuid.uuid4())
        analysis_store[id_] = {
            "analysis_id": id_,
            "created_at": f"2026-08-16T10:0{i}:00Z",
            "document": {"document_type": "dilekce" if i % 2 == 0 else "resmi_yazi"},
            "human_review": {"status": "pending_review" if i < 3 else "approved"}
        }
        
    res = client.get("/api/analyses?limit=2&offset=0")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    
    # Check filter
    res2 = client.get("/api/analyses?status=approved")
    data2 = res2.json()
    assert data2["total"] == 2
    assert len(data2["items"]) == 2

def test_get_pending_reviews():
    # Insert 1 pending review required, 1 approved, 1 pending review not required
    id1 = str(uuid.uuid4())
    analysis_store[id1] = {
        "analysis_id": id1,
        "requires_human_approval": True,
        "human_review": {"status": "pending_review"},
        "missing_fields": {"missing_fields": ["address"]},
        "created_at": "2026-08-16T10:00:00Z"
    }
    
    id2 = str(uuid.uuid4())
    analysis_store[id2] = {
        "analysis_id": id2,
        "requires_human_approval": True,
        "human_review": {"status": "approved"},
        "created_at": "2026-08-16T10:01:00Z"
    }
    
    res = client.get("/api/reviews/pending")
    data = res.json()
    
    # Should only return id1
    assert data["total"] == 1
    assert data["items"][0]["analysis_id"] == id1
    assert "Eksik bilgi tespit edildi." in data["items"][0]["review_reasons"]
    
    # Now approve id1
    client.post(f"/api/analysis/{id1}/approve")
    
    # Queue should be empty now
    res2 = client.get("/api/reviews/pending")
    data2 = res2.json()
    assert data2["total"] == 0
