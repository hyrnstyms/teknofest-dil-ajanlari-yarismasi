import pytest
from fastapi.testclient import TestClient
from backend.app.main import app, analysis_store
from backend.app.integrations.ebys import MockEBYSAdapter

client = TestClient(app)

def test_ebys_status():
    response = client.get("/api/integrations/ebys/status")
    assert response.status_code == 200
    data = response.json()
    assert data["adapter_type"] == "mock"
    assert data["connected"] is False

def test_mock_adapter_methods():
    adapter = MockEBYSAdapter()
    
    # create draft
    res = adapter.create_draft(None)
    assert res.success is True
    assert res.operation == "create_draft"
    
    # route
    from backend.app.integrations.ebys.schemas import EBYSRouteRequest
    route_req = EBYSRouteRequest(document_id="123", target_unit="IT")
    res2 = adapter.route_document(route_req)
    assert res2.success is True
    assert "IT" in res2.message
    
    # approve
    res3 = adapter.send_for_approval(None)
    assert res3.success is True
    assert res3.operation == "send_for_approval"
