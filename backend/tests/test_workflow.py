import pytest
from unittest.mock import MagicMock
from backend.app.graph.workflow import KamuaiWorkflow
from backend.app.llm.base import LLMClient

@pytest.fixture
def mock_workflow(monkeypatch):
    class FakeRetriever:
        def search_legal(self, *args, **kwargs):
            return []

    monkeypatch.setattr(
        "backend.app.agents.legal_agent.Retriever",
        FakeRetriever,
    )
    monkeypatch.setattr(
        "backend.app.agents.writing_agent.Retriever",
        FakeRetriever,
    )

    fast_llm = MagicMock(spec=LLMClient)
    fast_llm.chat.return_value = "{}"
    fast_llm.get_provider_name.return_value = "evren"
    fast_llm.get_model_name.return_value = "llm-fast"

    legal_llm = MagicMock(spec=LLMClient)
    legal_llm.chat.return_value = '{"items":[]}'
    legal_llm.get_provider_name.return_value = "evren"
    legal_llm.get_model_name.return_value = "llm-large"

    calls = []

    def fake_create_llm_client(agent_name):
        calls.append(agent_name)
        if agent_name == "legal_agent":
            return legal_llm
        return fast_llm

    monkeypatch.setattr(
        "backend.app.graph.workflow.create_llm_client",
        fake_create_llm_client,
    )
    wf = KamuaiWorkflow()
    wf._test_llm_factory_calls = calls
    wf._test_fast_llm = fast_llm
    wf._test_legal_llm = legal_llm
    return wf

def test_workflow_initialization(mock_workflow):
    assert mock_workflow.graph is not None


def test_workflow_assigns_fast_and_large_evren_clients(mock_workflow):
    assert mock_workflow._test_llm_factory_calls == [
        "document_agent",
        "legal_agent",
    ]
    assert mock_workflow.doc_agent.llm is mock_workflow._test_fast_llm
    assert mock_workflow.extract_agent.llm is mock_workflow._test_fast_llm
    assert mock_workflow.summary_agent.llm is mock_workflow._test_fast_llm
    assert mock_workflow.writing_agent.llm is mock_workflow._test_fast_llm
    assert mock_workflow.legal_agent.llm is mock_workflow._test_legal_llm
    assert not hasattr(mock_workflow.quality_agent, "llm")

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
