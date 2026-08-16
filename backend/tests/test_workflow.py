import pytest
from unittest.mock import MagicMock
from backend.app.graph.workflow import KamuaiWorkflow
from backend.app.llm.base import LLMClient

@pytest.fixture
def mock_workflow(monkeypatch):
    wf = KamuaiWorkflow()
    # Mock LLM calls if necessary or use the LLM abstract
    return wf

def test_workflow_initialization(mock_workflow):
    assert mock_workflow.graph is not None

def test_workflow_end_to_end_empty_text(mock_workflow):
    # This will test the error isolation and degradation
    res = mock_workflow.run("")
    assert "node_timings" in res
    assert "document_agent" in res["node_timings"]
    assert "extraction_agent" in res["node_timings"]
    assert res["quality"]["status"] in ["warning", "fail"]
    assert res["human_review"]["required"] is True

def test_workflow_mehmet_kaya_end_to_end(mock_workflow):
    text = """
    T.C. ÖRNEK KAMU KURUMU Bilgi Edinme Birimine
    Konu: Proje Harcamaları Hakkında Bilgi Talebi
    Başvuru Sahibi: Mehmet Kaya
    T.C. Kimlik No: 10000000146
    Telefon: 0532 111 22 33
    E-posta: mehmet.kaya@example.com
    Kurumunuz tarafından yürütülen Akıllı Şehir Projesi hakkında bilgi edinmek istiyorum.
    """
    res = mock_workflow.run(text)
    
    assert "node_timings" in res
    assert "document" in res
    assert "extraction" in res
    
    # Check timings
    assert "document_agent" in res["node_timings"]
    assert "quality_agent" in res["node_timings"]
    
    # Final state schema
    assert "raw_text" in res
    assert "quality" in res
    assert "human_review" in res
